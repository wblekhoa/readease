"""The reading engine, speaking over a pipe instead of into Qt.

This is the seam the Tauri migration stands on: any shell that can spawn a
process and parse JSON lines can drive the whole voice - synthesis, sentence
pauses, time-stretching - without linking Python. The Qt app keeps working
untouched beside it; when the new shell reaches parity, the old one can be
removed without touching this layer.

Protocol (one JSON object per line, requests on stdin, replies on stdout):

    {"id": 1, "method": "ping"}
    {"id": 2, "method": "voices"}
    {"id": 3, "method": "read", "params": {"text": ..., "voice_id": ...,
                                            "rate": 1.0,
                                            "segment_id": "part-2"}}
    {"id": 4, "method": "stop"}

A read streams `{"id": 3, "event": "chunk", "seq": n, "from_voice": bool,
"pcm": <base64 float32 mono>, "sample_rate": 48000}` frames and finishes with
a normal reply. Silence between sentences is a frame like any other, so the
shell needs no prosody knowledge at all.

Flow control is the shell's to ask for. A read carrying `"window": n` gets at
most n frames (chunks and positions alike) before the shell must hand back
room with `{"method": "audio.credit", "params": {"id": 3, "frames": 1}}` -
one credit per frame it has taken off its queue. While the window is spent
the engine waits, still answering the quick requests, so a paused player
never blocks a `model.status`. A read without a window streams as fast as it
can, and closing stdin releases the window too - batch callers do exactly
that. Neither `audio.credit` nor `progress.reached` carries an `id`, and
neither gets a reply.

Listening progress is written on the shell's word, not the engine's: the
engine emits `position` when it SYNTHESISES an utterance, and the shell
sends `{"method": "progress.reached", "params": {"id": 3, "segment_id": s}}`
when the ear gets there. Only then is the book's progress saved.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import json
import sys
import threading
from pathlib import Path
from queue import SimpleQueue
from typing import Any, Iterator, Protocol, TextIO

import numpy as np

from vieneu_reader.domain.models import AudioChunk, Segment, Voice
from vieneu_reader.domain.prosody import (
    SENTENCE_PAUSE_MS,
    pause_after_ms,
    selection_pause_ms,
    speak_with_notes,
    speakable_text,
    split_sentences,
)
from vieneu_reader.domain.segmenter import split_transient_parts
from vieneu_reader.playback.time_stretch import SAMPLE_RATE, TimeStretcher
from vieneu_reader.speech.contracts import SynthesisSettings
from vieneu_reader.importers.errors import BookImportError
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.speech.cache import AudioCache, audio_cache_key
from vieneu_reader.speech.external.estimate import (
    estimate_scope, scope_end, scope_start,
)
from vieneu_reader.speech.external.pricing import PRICES, PRICES_FETCHED, price_for
from vieneu_reader.speech.external.provider import ExternalVoiceError
from vieneu_reader.speech.external.engine import ExternalSpeechEngine
from vieneu_reader.speech.external.pricing import VoicePrice
from vieneu_reader.speech.external.route import (
    KEY_FOR_PROVIDER, model_of, pick_voice_route, provider_of,
)
from vieneu_reader.speech.external.spend import SpendMeter
from vieneu_reader.storage.repository import LibraryRepository, Progress, StoredBook

PROTOCOL_VERSION = 1

_EOF = object()


class ReadingEngine(Protocol):
    @property
    def engine_version(self) -> str: ...

    def voices(self) -> tuple[Voice, ...]: ...

    def stream(
        self, text: str, voice_id: str, settings: SynthesisSettings
    ) -> Iterator[AudioChunk]: ...


#: One model per provider at a time, chosen in settings. The alternative was
#: measured and rejected: the catalogue used to emit MODELS x VOICES, which is
#: 18 rows for OpenAI alone and 2N for an ElevenLabs library - a list nobody
#: can scan, in which the same voice appears twice at two prices. The id stays
#: `provider:model:voice` so the estimate, the cache key and the spend meter
#: still read the price off the id itself; only the catalogue narrows.
MODEL_KEY_FOR_PROVIDER = {
    "openai": "openai_model",
    "elevenlabs": "elevenlabs_model",
}
DEFAULT_MODEL_FOR_PROVIDER = {
    "openai": "tts-1",
    # The model whose published language list names Vietnamese, and half the
    # price of v3 [fetched 2026-09-04]. A default that cannot say the language
    # this app exists for is not a default.
    "elevenlabs": "eleven_flash_v2_5",
}


def chosen_model(provider: str, settings: dict) -> str:
    """The model this Mac is set to use with a provider."""

    stored = settings.get(MODEL_KEY_FOR_PROVIDER.get(provider, ""))
    known = {price.model for price in PRICES if price.provider == provider}
    if isinstance(stored, str) and stored in known:
        return stored
    return DEFAULT_MODEL_FOR_PROVIDER.get(provider, "")


def _external_provider(provider: str, voice_id: str, settings: dict) -> Any:
    """Build the provider a voice names, on the key this Mac holds.

    Kept out of the session so the session never touches a credential except
    to hand it straight to the one module allowed to reach the network.
    """

    key = settings.get(KEY_FOR_PROVIDER.get(provider, ""))
    if not key:
        return None
    model = model_of(voice_id) or chosen_model(provider, settings)
    if provider == "openai":
        from vieneu_reader.speech.external.openai import OpenAIVoiceProvider

        return OpenAIVoiceProvider(str(key), model=model)
    if provider == "elevenlabs":
        from vieneu_reader.speech.external.elevenlabs import ElevenLabsVoiceProvider

        return ElevenLabsVoiceProvider(str(key), model=model)
    return None


def _text_utterances(text: str, settings: SynthesisSettings) -> list[_Utterance]:
    """Pasted or captured text, shaped exactly as the reading will send it.

    ONE builder, two callers - the reading and the estimate that prices it,
    the same rule a book's utterances follow. Counting `text` itself would
    quote a number the bill then disagrees with: `speakable_text` lowers
    shouted runs and rewrites ordinals on the way past.

    Each part is addressable, exactly as a book's segments are. Nothing is
    stored for a plain read (no book_id reaches `_speak`, so no progress
    row) - the id exists so a reading can be RESUMED at the part it had
    reached, which is what changing the voice mid-way does.
    """

    parts = split_transient_parts(text, settings.max_chars)
    if not parts:
        return []
    spoken = tuple(speakable_text(part.text) for part in parts)
    return [
        _Utterance(
            text=spoken[index],
            pause_after_ms=(
                selection_pause_ms(spoken[index], parts[index + 1].joint)
                if index + 1 < len(parts)
                else 0
            ),
            segment_id=f"part-{index}",
        )
        for index in range(len(parts))
    ]


def _start_at(
    utterances: "list[_Utterance]",
    wanted: object,
    order: "list[str] | None" = None,
) -> int:
    """Where a resume lands: the first thing said ABOUT that segment.

    Which may be the cue for a picture placed before it, not the paragraph.

    Some segments say nothing of their own - a footnote whose words were
    already read at the sentence that referenced it. Pointing at one has to
    carry on from the next thing that DOES speak: falling back to 0, as this
    did for anything it could not find, would silently restart the book from
    the beginning under a finger that meant "read from here".
    """

    if not wanted:
        return 0
    for index, utterance in enumerate(utterances):
        if utterance.segment_id == wanted:
            return index
    if not order or str(wanted) not in order:
        return 0
    speaks = {utterance.segment_id for utterance in utterances}
    for later in order[order.index(str(wanted)) + 1:]:
        if later in speaks:
            return next(
                index
                for index, utterance in enumerate(utterances)
                if utterance.segment_id == later
            )
    # Nothing after it has anything to say: the reading is over, which is
    # the truth, and not the top of the book.
    return len(utterances)


def _reading_order(book: Any) -> list[str]:
    """Every segment id, in the order the book reads."""

    return [
        segment.id for chapter in book.chapters for segment in chapter.segments
    ]


def _silence(milliseconds: int) -> bytes:
    samples = SAMPLE_RATE * milliseconds // 1000
    return np.zeros(samples, dtype=np.float32).tobytes()


@dataclass(frozen=True)
class _Utterance:
    """One thing to speak, the rest that follows it, and where it lives."""

    text: str
    pause_after_ms: int
    segment_id: str | None = None
    # Set on the spoken cue for a picture ("Xem hình 3."): rides the position
    # event so the shell can bring the picture into view exactly when the ear
    # hears the cue, not when the model synthesised it.
    figure_id: str | None = None


# What the voice says when the reading reaches a picture, and the rest that
# follows so the listener has a beat to look. Vietnamese on purpose: the voice
# is Vietnamese whatever the shell's UI language is.
FIGURE_CUE = "Xem hình {number}."
FIGURE_CUE_PAUSE_MS = 600

# What the voice says before a footnote, and the beat after it. On paper a
# small number sends the eye down the page and back; an ear has no such move,
# so the note is read where it belongs - after the sentence that carries the
# number - and it has to be ANNOUNCED, or it arrives as a non-sequitur in the
# middle of a paragraph. Two words, because a longer preamble said before
# eighty notes becomes the thing you hear instead of the notes (owner,
# 04/09: "nói thêm").
NOTE_CUE = "Nói thêm, {text}"
NOTE_CUE_PAUSE_MS = 450


def _figure_cues(presentation: Any) -> dict[str, list[tuple[str, str, int]]]:
    """Per anchor segment: (placement, figure_id, number-within-chapter).

    Numbered per CHAPTER, not per book: the domain's running count is right
    for a print index, but "Xem hình 187" is not something a listener can
    hold in their head, and "Xem hình 3" is (owner's call, 2026-09-02).
    """
    cues: dict[str, list[tuple[str, str, int]]] = {}
    for chapter in presentation.chapters:
        for number, figure in enumerate(chapter.figures, start=1):
            cues.setdefault(figure.anchor_segment_id, []).append(
                (figure.placement, figure.id, number)
            )
    return cues


def _note_marks(presentation: Any) -> dict[str, list[tuple[int, int, str]]]:
    """Per anchor segment: (offset, label length, the note's own words).

    Ordered by where the number falls, because that is the order the page
    prints them in and the order a listener has to hear them.
    """

    marks: dict[str, list[tuple[int, int, str]]] = {}
    for chapter in presentation.chapters:
        for note in getattr(chapter, "notes", ()):
            marks.setdefault(note.anchor_segment_id, []).append(
                (note.offset, note.length, note.text)
            )
    for found in marks.values():
        found.sort()
    return marks


class _PreparationCancelled(Exception):
    """A model download the person asked to abandon."""


class _Session:
    """One serve() call: a request pump, a reply channel, and the engine."""

    def __init__(
        self,
        reader: TextIO,
        writer: TextIO,
        engine: ReadingEngine,
        repository: "LibraryRepository | None" = None,
        service: "LibraryService | None" = None,
        settings_path: "Path | None" = None,
        notes_deps: "dict[str, Any] | None" = None,
        audio_cache: "AudioCache | None" = None,
    ):
        self._writer = writer
        self._engine = engine
        self._audio_cache = audio_cache
        # Session-lived, in memory: "what have I run up since I opened the
        # app" is the question, and nothing on disk should accumulate a
        # record of what somebody has been reading.
        self._spend = SpendMeter()
        self._repository = repository
        self._service = service
        self._settings_path = settings_path
        self._backup_root = (
            settings_path.parent / "AppleBooksBackups"
            if settings_path is not None
            else None
        )
        self._notes_deps: dict[str, Any] | None = notes_deps
        self._requests: SimpleQueue = SimpleQueue()
        self._deferred: list[dict] = []
        self._eof = False
        # Frames the shell still has room for during the current reading;
        # None when the shell asked for no window (or stdin has closed).
        self._credits: int | None = None
        self._credit_read: Any = None
        # A stop seen while waiting for room: honoured at the next check.
        self._stop_pending = False
        # What each recent reading was of, so a `progress.reached` for it -
        # which may land after its reply - can be written with the right
        # rate and voice. Bounded: only the last few readings matter.
        self._listening: dict[Any, tuple[str, float, str]] = {}
        pump = threading.Thread(
            target=self._pump, args=(reader,), daemon=True
        )
        pump.start()

    def _pump(self, reader: TextIO) -> None:
        for line in reader:
            line = line.strip()
            if line:
                self._requests.put(line)
        self._requests.put(_EOF)

    def _send(self, payload: dict[str, Any]) -> None:
        self._writer.write(json.dumps(payload) + "\n")
        self._writer.flush()

    def _reply(self, request_id: Any, result: dict[str, Any]) -> None:
        self._send({"id": request_id, "ok": True, "result": result})

    def _fail(self, request_id: Any, error: str) -> None:
        self._send({"id": request_id, "ok": False, "error": error})

    def _next_request(self) -> dict | None:
        """The next request, honouring ones deferred during a reading."""
        if self._deferred:
            return self._deferred.pop(0)
        if self._eof:
            return None
        item = self._requests.get()
        if item is _EOF:
            self._eof = True
            return None
        try:
            return json.loads(item)
        except json.JSONDecodeError:
            self._send({"id": None, "ok": False, "error": "invalid json"})
            return self._next_request()

    # Answered BETWEEN CHUNKS while a reading streams. Each is quick and
    # touches nothing the reading owns, so serving it inline costs one chunk
    # of latency. Everything else still waits for the reading to end.
    #
    # Measured before this existed (2026-09-02): with a reading running,
    # library.list and config.get were answered only when the reading
    # finished - 6.56 s for six sentences, minutes for a chapter, and past the
    # shell's 30 s timeout. To the person that was "the app hangs": switch to
    # the library while listening and the list never arrives; change the
    # speed and it never saves; scroll to a picture and it never loads.
    _INLINE_WHILE_STREAMING = frozenset({
        "ping", "voices", "library.list", "book.open", "book.figure",
        # A cover is a zip read (EPUB) or a 21 ms page render (PDF, measured
        # 02/09) and cached after the first ask - cheap enough between chunks.
        "book.cover",
        "config.get", "config.set", "config.verify_key", "model.status", "notes.books",
        # The read button re-prices itself as the reader changes scope, and
        # they do that while listening.
        "estimate",
        # Removing or rewriting a highlight is one small write, and a
        # person reads (and tidies) while listening - deferring it until the
        # chapter ends would look like the button did nothing.
        "annotations.delete", "annotations.update",
    })

    def _stop_requested(self) -> bool:
        """Poll for a stop while streaming; answer the quick, defer the rest.

        EOF is not a stop: closing stdin means "no more requests", and batch
        callers do exactly that - one read, close, collect the audio. The
        reading finishes; the loop exits afterwards.
        """
        while not self._requests.empty():
            self._absorb(self._requests.get())
        if self._stop_pending:
            self._stop_pending = False
            return True
        return False

    def _absorb(self, item: Any) -> None:
        """One line off stdin while a reading streams."""
        if item is _EOF:
            self._eof = True
            return
        try:
            request = json.loads(item)
        except json.JSONDecodeError:
            self._send({"id": None, "ok": False, "error": "invalid json"})
            return
        method = request.get("method")
        if method == "stop":
            self._reply(request.get("id"), {"stopped": True})
            self._stop_pending = True
        elif method == "audio.credit":
            self._take_credit(request.get("params") or {})
        elif method == "progress.reached":
            self._progress_reached(request.get("params") or {})
        elif method in self._INLINE_WHILE_STREAMING:
            request_id = request.get("id")
            try:
                self._dispatch(method, request_id, request)
            except Exception as error:  # noqa: BLE001 - same net as run()
                self._fail(request_id, f"{method} failed: {error}")
        else:
            self._deferred.append(request)

    def _await_credit(self) -> bool:
        """Wait until the shell has room for one more frame.

        False means a stop arrived while waiting: the frame must not go out.
        Blocking here is the whole point - the shell's queue is bounded, and
        an engine that kept writing would be the one blocking the pipe, with
        every reply stuck behind its audio. Closing stdin releases the wait,
        so a batch caller that never sends credits still gets its audio.
        """
        while (
            self._credits is not None and self._credits <= 0
            and not self._eof and not self._stop_pending
        ):
            self._absorb(self._requests.get())
        if self._stop_pending:
            return False
        if self._credits is not None and not self._eof:
            self._credits -= 1
        return True

    def _take_credit(self, params: dict[str, Any]) -> None:
        # A credit for a reading that is over (the shell drains what a stop
        # left behind) must not top up the one that follows it.
        if self._credits is None or params.get("id") != self._credit_read:
            return
        self._credits += int(params.get("frames") or 1)

    def _progress_reached(self, params: dict[str, Any]) -> None:
        heard = self._listening.get(params.get("id"))
        segment_id = params.get("segment_id")
        if heard is None or not segment_id or self._repository is None:
            return
        book_id, rate, voice_id = heard
        self._repository.save_progress(Progress(
            book_id=book_id,
            segment_id=str(segment_id),
            playback_rate=rate,
            voice_id=voice_id,
        ))

    def run(self) -> None:
        while True:
            request = self._next_request()
            if request is None:
                return
            method = request.get("method")
            request_id = request.get("id")
            try:
                self._dispatch(method, request_id, request)
            except Exception as error:  # noqa: BLE001 - one bad handler
                # must become one error reply, never a dead pipe: the shell
                # on the other end has no way to restart this process.
                self._fail(request_id, f"{method} failed: {error}")

    def _dispatch(self, method, request_id, request) -> None:
            if method == "ping":
                self._reply(request_id, {
                    "protocol": PROTOCOL_VERSION,
                    "engine": self._engine.engine_version,
                    "sample_rate": SAMPLE_RATE,
                })
            elif method == "voices":
                catalogue, unreachable = self._voice_catalogue()
                # A provider that could not be ASKED is not the same as one
                # that offers nothing, and neither is a voice. It travels
                # beside the list so the shell can say which is which.
                #
                # The per-model price list used to ride along here as well.
                # No shell ever read it, and a payload nobody reads is a
                # claim nobody checks. The picker that would need it waits
                # until a voice has actually been listened to; `chosen_model`
                # still decides which model a read uses, and that part is
                # live and tested.
                self._reply(request_id, {
                    "voices": catalogue, "unreachable": unreachable,
                })
            elif method == "read":
                self._read(request_id, request.get("params") or {})
            elif method == "read.book":
                self._read_book(request_id, request.get("params") or {})
            elif method == "applebooks.shelf":
                self._applebooks_shelf(request_id)
            elif method == "applebooks.import":
                self._applebooks_import(request_id, request.get("params") or {})
            elif method == "applebooks.sync_notes":
                self._applebooks_sync_notes(request_id, request.get("params") or {})
            elif method == "annotations.delete":
                self._annotations_delete(request_id, request.get("params") or {})
            elif method == "annotations.update":
                self._annotations_update(request_id, request.get("params") or {})
            elif method == "notes.books":
                self._notes_books(request_id)
            elif method == "notes.plan":
                self._notes_plan(request_id, request.get("params") or {})
            elif method == "notes.transfer":
                self._notes_transfer(request_id, request.get("params") or {})
            elif method == "config.get":
                self._config_get(request_id, request.get("params") or {})
            elif method == "config.set":
                self._config_set(request_id, request.get("params") or {})
            elif method == "config.verify_key":
                self._config_verify_key(request_id, request.get("params") or {})
            elif method == "model.status":
                self._model_status(request_id)
            elif method == "model.prepare":
                self._model_prepare(request_id)
            elif method == "model.set_precision":
                self._model_set_precision(request_id, request.get("params") or {})
            elif method == "model.remove_build":
                self._model_remove_build(request_id, request.get("params") or {})
            elif method == "library.list":
                self._library_list(request_id)
            elif method == "library.import":
                self._library_import(request_id, request.get("params") or {})
            elif method == "library.remove":
                self._library_remove(request_id, request.get("params") or {})
            elif method == "estimate":
                self._estimate(request_id, request.get("params") or {})
            elif method == "book.open":
                self._book_open(request_id, request.get("params") or {})
            elif method == "book.cover":
                self._book_cover(request_id, request.get("params") or {})
            elif method == "book.figure":
                self._book_figure(request_id, request.get("params") or {})
            elif method == "stop":
                # Nothing is playing; saying so beats silence.
                self._reply(request_id, {"stopped": False})
            elif method == "audio.credit":
                # Room handed back after the reading it was for has ended.
                # Nothing to top up, and no reply: it carries no id.
                self._take_credit(request.get("params") or {})
            elif method == "progress.reached":
                # The ear reaches the last utterances after the reply has
                # gone out, so this lands here as often as mid-stream.
                self._progress_reached(request.get("params") or {})
            else:
                self._fail(request_id, f"unknown method: {method}")

    def _read(self, request_id: Any, params: dict[str, Any]) -> None:
        """Pasted or captured text: the same shaping the Qt selection path has.

        `split_transient_parts` bounds each utterance for the engine and keeps
        paragraph joints; `speakable_text` lowers shouted runs; the pause after
        each part comes from the prosody table, never a constant.
        """
        text = str(params.get("text") or "")
        voice_id = str(params.get("voice_id") or "")
        rate = float(params.get("rate") or 1.0)
        settings = SynthesisSettings()
        utterances = _text_utterances(text, settings)
        if not utterances:
            self._fail(request_id, "text is empty")
            return
        wanted = str(params.get("segment_id") or "")
        if wanted:
            for index, utterance in enumerate(utterances):
                if utterance.segment_id == wanted:
                    utterances = utterances[index:]
                    break
            else:
                self._fail(request_id, f"unknown part: {wanted}")
                return
        self._speak(
            request_id, utterances, voice_id, rate, settings,
            window=params.get("window"),
        )

    def _read_book(self, request_id: Any, params: dict[str, Any]) -> None:
        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        stored = self._repository.get_book(book_id)
        if stored is None:
            self._fail(request_id, f"unknown book: {book_id}")
            return
        voice_id = str(params.get("voice_id") or "")
        if not voice_id:
            # Progress is written with this voice once the shell reports the
            # ear reaching a position - so a request the voice would reject
            # must be rejected here, or it leaves a row the library refuses
            # to load (an empty voice made library.list fail for every book,
            # 02/09).
            self._fail(request_id, "voice_id is required")
            return
        rate = float(params.get("rate") or 1.0)
        if not 0.5 <= rate <= 2.0:
            # The other half of the loader's contract: it refuses a stored
            # rate outside this range, so one must never be stored.
            self._fail(request_id, f"rate {rate} is outside 0.5-2.0")
            return
        wanted = params.get("segment_id")
        if not wanted:
            progress = self._repository.load_progress(book_id)
            wanted = progress.segment_id if progress else None
        utterances, chapter_of = self._book_utterances(stored)
        start = _start_at(utterances, wanted, _reading_order(stored.book))
        # How far this press of the button is allowed to reach. `None` is the
        # whole book, which is what every reading did before paid voices
        # existed and is still the default.
        chapters = params.get("chapters")
        end = scope_end(chapter_of, start, None if chapters is None else int(chapters))
        self._speak(
            request_id, utterances[start:end], voice_id, rate, SynthesisSettings(),
            book_id=book_id, window=params.get("window"),
        )

    def _voice_catalogue(self) -> list[dict[str, Any]]:
        """Every voice on offer: the local model first, then paid ones.

        A provider's voices appear ONLY once its key is on this machine.
        Offering a voice that cannot speak would put the refusal after the
        choice instead of before it - the person would pick Alloy, press
        read, and be told no. The local model comes first because it is the
        product; the paid ones are an option somebody went and enabled.
        """

        catalogue: list[dict[str, Any]] = [
            {"id": voice.id, "label": voice.label, "paid": False}
            for voice in self._engine.voices()
        ]
        unreachable: list[dict[str, Any]] = []
        settings = self._settings_document()
        for provider in sorted(KEY_FOR_PROVIDER):
            if not settings.get(KEY_FOR_PROVIDER[provider]):
                continue
            model = chosen_model(provider, settings)
            external = _external_provider(provider, f"{provider}:{model}:x", settings)
            if external is None:
                continue
            try:
                offered = external.voices()
            except ExternalVoiceError as error:
                # ElevenLabs' catalogue is a NETWORK call, unlike OpenAI's
                # constant. Letting it out of here took the whole catalogue
                # with it - including the local voices, which need nothing
                # and were working. The provider drops out and says why; the
                # reader keeps the voices that were never in question.
                unreachable.append({"provider": provider, "code": error.code})
                continue
            catalogue.extend(
                {
                    "id": voice.as_voice(provider).id,
                    "label": voice.as_voice(provider).label,
                    "paid": True,
                    "provider": provider,
                    "model": model,
                    # Which languages the provider vouches for. Empty is
                    # "did not say", never "cannot": OpenAI's list says
                    # nothing about any of its voices, and they all speak
                    # Vietnamese after a fashion.
                    "languages": list(voice.languages),
                    **({"gender": voice.gender} if voice.gender else {}),
                }
                for voice in offered
            )
        return catalogue, unreachable

    def _estimate(self, request_id: Any, params: dict[str, Any]) -> None:
        """What one press of the read button would cost, before it is pressed.

        Exact, not indicative: a paid voice bills by the character and the
        whole book is already on this machine, so this is arithmetic over the
        very strings `_speak` will send. Nothing is requested from anybody to
        answer it, and a local voice costs nothing to say so.
        """

        voice_id = str(params.get("voice_id") or "")
        price = price_for(model_of(voice_id) or "")

        # Pasted text is priced too, and it is the case that most needed it:
        # a paste can be 100,000 characters, which is one press of a button
        # and ten dollars on the dearer voices. There are no chapters in it,
        # so there is no scope to apply - the whole of what was pasted is
        # what gets read.
        if not params.get("book_id"):
            utterances = _text_utterances(
                str(params.get("text") or ""), SynthesisSettings()
            )
            chars = sum(len(utterance.text) for utterance in utterances)
            if price is None:
                self._reply(request_id, {
                    "paid": False, "chars": chars,
                    "utterances": len(utterances), "chapters": 0,
                    "spent_usd": self._spend.snapshot().usd,
                })
                return
            self._reply(request_id, {
                "paid": True,
                "provider": provider_of(voice_id),
                "model": price.model,
                "chars": chars,
                "utterances": len(utterances),
                "chapters": 0,
                "usd": round(price.usd_for(chars), 4),
                "units": price.units_for(chars),
                "unit": price.unit,
                "price_dated": PRICES_FETCHED,
                "spent_usd": self._spend.snapshot().usd,
            })
            return

        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        stored = self._repository.get_book(str(params.get("book_id") or ""))
        if stored is None:
            self._fail(request_id, f"unknown book: {params.get('book_id')}")
            return
        utterances, chapter_of = self._book_utterances(stored)
        wanted = params.get("segment_id")
        if not wanted:
            progress = self._repository.load_progress(stored.book.id)
            wanted = progress.segment_id if progress else None
        resume = _start_at(utterances, wanted, _reading_order(stored.book))
        raw_chapters = params.get("chapters")
        chapters = None if raw_chapters is None else int(raw_chapters)
        # The CEILING of the scope, not the cost of resuming: a click on a
        # paragraph carries the same scope and can start anywhere inside it,
        # so a figure measured from the resume point is a figure that only
        # one of the ways to start a reading actually pays.
        start = scope_start(chapter_of, resume, chapters)

        if price is None:
            # The local model. Saying "free" beats saying nothing: the button
            # is waiting on an answer either way.
            end = scope_end(chapter_of, start, chapters)
            self._reply(request_id, {
                "paid": False,
                "chars": sum(len(u.text) for u in utterances[start:end]),
                "utterances": end - start,
                "chapters": len(set(chapter_of[start:end])),
                "spent_usd": self._spend.snapshot().usd,
            })
            return
        result = estimate_scope(
            [utterance.text for utterance in utterances],
            chapter_of, start, chapters, price,
        )
        self._reply(request_id, {
            "paid": True,
            "provider": provider_of(voice_id),
            "model": price.model,
            "chars": result.chars,
            "utterances": result.utterances,
            "chapters": result.chapters,
            "usd": result.usd,
            "units": result.units,
            "unit": result.unit,
            "price_dated": result.price_dated,
            # What this session has already run up. It rides here rather than
            # on an event of its own because the Rust host forwards only the
            # events it knows about, and the button re-prices whenever
            # anything changes - which is often enough for a figure that
            # lives one press away, behind the settings button.
            "spent_usd": self._spend.snapshot().usd,
        })

    def _book_utterances(
        self, stored: StoredBook
    ) -> tuple[list[_Utterance], list[int]]:
        """Everything this book would say, and the chapter each bit is in.

        ONE builder, two callers: the reading, and the estimate the button
        shows before the reading is paid for. Built separately they would
        drift - the button would be counting characters the engine never
        sends, or missing ones it does - and the difference between those two
        numbers is the difference between a price and a guess.
        """

        segments: list[Segment] = [
            segment
            for chapter in stored.book.chapters
            for segment in chapter.segments
        ]
        chapter_of_segment: dict[str, int] = {
            segment.id: index
            for index, chapter in enumerate(stored.book.chapters)
            for segment in chapter.segments
        }
        cues: dict[str, list[tuple[str, str, int]]] = {}
        notes: dict[str, list[tuple[int, int, str]]] = {}
        already_said: set[str] = set()
        if self._service is not None:
            presentation = self._service.presentation_for(
                stored.book, stored.managed_path
            )
            cues = _figure_cues(presentation)
            notes = _note_marks(presentation)
            already_said = {
                segment_id
                for chapter in presentation.chapters
                for segment_id in getattr(chapter, "spoken_elsewhere", ())
            }
            if already_said:
                # A chapter that WAS the notes has nothing left to say. Its
                # title alone, spoken into the silence at the end of a book,
                # announces a chapter that never arrives.
                for chapter_model in stored.book.chapters:
                    body = [
                        segment
                        for segment in chapter_model.segments
                        if segment.kind != "heading"
                    ]
                    if body and all(
                        segment.id in already_said for segment in body
                    ):
                        already_said.update(
                            segment.id for segment in chapter_model.segments
                        )
        utterances: list[_Utterance] = []
        chapter_of: list[int] = []

        def add(utterance: _Utterance, chapter: int) -> None:
            utterances.append(utterance)
            chapter_of.append(chapter)

        for index, segment in enumerate(segments):
            if segment.id in already_said:
                # The endnote at the back of the book, or the small print at
                # the foot of the chapter: its words were read at the
                # sentence that needed them. Read again here they arrive
                # with no sentence to belong to (owner, 04/09: "đọc lại …
                # mất ngữ cảnh và cũng chả có giá trị gì").
                continue
            here = cues.get(segment.id, [])
            chapter = chapter_of_segment[segment.id]
            for placement, figure_id, number in here:
                if placement == "before":
                    add(_Utterance(
                        text=FIGURE_CUE.format(number=number),
                        pause_after_ms=FIGURE_CUE_PAUSE_MS,
                        segment_id=segment.id,
                        figure_id=figure_id,
                    ), chapter)
            after_segment = pause_after_ms(
                segment,
                segments[index + 1] if index + 1 < len(segments) else None,
            )
            # Notes turn one segment into several utterances - the same thing
            # a figure cue already does - so the follow-along, the estimate
            # and the resume all keep working on `segment_id` alone. Only the
            # LAST piece carries the segment's own pause: put it on an inner
            # one and there is a paragraph-sized hole mid-paragraph.
            # `or` the segment back in: every segment has to produce at
            # least one utterance, or it is a place the reading cannot be
            # resumed from.
            pieces = speak_with_notes(
                segment.text, notes.get(segment.id, [])
            ) or ((segment.text, False),)
            for order, (piece, is_note) in enumerate(pieces):
                last = order == len(pieces) - 1
                spoken = (
                    NOTE_CUE.format(text=speakable_text(piece))
                    if is_note
                    else speakable_text(piece, segment.kind)
                )
                add(_Utterance(
                    text=spoken,
                    pause_after_ms=(
                        after_segment
                        if last
                        else NOTE_CUE_PAUSE_MS if is_note else SENTENCE_PAUSE_MS
                    ),
                    segment_id=segment.id,
                ), chapter)
            for placement, figure_id, number in here:
                if placement == "after":
                    add(_Utterance(
                        text=FIGURE_CUE.format(number=number),
                        pause_after_ms=FIGURE_CUE_PAUSE_MS,
                        segment_id=segment.id,
                        figure_id=figure_id,
                    ), chapter)
        return utterances, chapter_of

    def _library_list(self, request_id: Any) -> None:
        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        books = []
        # Which books still have a live pairing with Apple Books. One read for
        # the whole shelf, and it is the LINK that is reported - not a check
        # against Apple's own database, which would mean copying it every time
        # the library is opened, for a badge (owner, 03/09).
        paired = set(self._repository.apple_book_links().values())
        for stored in self._repository.list_books():
            progress = self._repository.load_progress(stored.book.id)
            try:
                size_bytes = stored.managed_path.stat().st_size
            except OSError:
                size_bytes = None
            # How far the voice got, for the shelf: the spoken segment's place
            # in the whole book, and the chapter it sits in. Null - not 0 -
            # when there is no progress, or its segment no longer exists.
            progress_ratio: float | None = None
            progress_chapter: str | None = None
            if progress is not None:
                seen = 0
                total = sum(len(chapter.segments) for chapter in stored.book.chapters)
                for chapter in stored.book.chapters:
                    for segment in chapter.segments:
                        if segment.id == progress.segment_id:
                            progress_ratio = seen / total if total else None
                            progress_chapter = chapter.title
                            break
                        seen += 1
                    if progress_chapter is not None:
                        break
            books.append({
                "id": stored.book.id,
                "title": stored.book.title,
                "source_format": stored.book.source_format,
                "segment_id": progress.segment_id if progress else None,
                "progress_ratio": progress_ratio,
                "progress_chapter": progress_chapter,
                # What tells two same-titled copies apart: shape, size, and
                # when each one arrived.
                "chapters": len(stored.book.chapters),
                "size_bytes": size_bytes,
                "imported_at": self._repository.imported_at(stored.book.id),
                # True while the pairing holds, which is what makes a note
                # sync land on this book rather than a guess at its title.
                "from_apple_books": stored.book.id in paired,
            })
        self._reply(request_id, {"books": books})

    def _model_prepare(self, request_id: Any) -> None:
        """Download whatever the active build still needs, streaming progress.

        Long and blocking by design: the pipe answers nothing else while a
        download runs, exactly like the Qt setup screen gated the app.
        """
        prepare = getattr(self._engine, "prepare_model", None)
        if prepare is None:
            self._fail(request_id, "engine cannot prepare models")
            return

        def report(progress: float, message: str) -> None:
            # The progress callback is also the cancel point - the same place
            # the Qt setup screen used, for the same reason: it is the only
            # moment a long download hands control back. 453MB with no way out
            # is not a download, it is a hostage situation.
            if self._stop_requested():
                raise _PreparationCancelled()
            self._send({
                "id": request_id,
                "event": "model_progress",
                "progress": float(progress),
                "message": str(message),
            })

        try:
            prepare(report)
        except _PreparationCancelled:
            self._reply(request_id, {"ready": False, "cancelled": True})
            return
        self._reply(request_id, {"ready": True})

    def _model_set_precision(
        self, request_id: Any, params: dict[str, Any]
    ) -> None:
        from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore

        if self._settings_path is None:
            self._fail(request_id, "no settings on this server")
            return
        precision = str(params.get("precision") or "")
        store = VoiceQualityPreferenceStore(self._settings_path)
        store.save(precision)
        # The engine loads its build at construction; the shell restarts this
        # process to make the choice real. Saying so keeps the contract loud.
        self._reply(request_id, {"saved": True, "restart_required": True})

    def _model_remove_build(
        self, request_id: Any, params: dict[str, Any]
    ) -> None:
        remove = getattr(self._engine, "remove_build", None)
        if remove is None:
            self._fail(request_id, "engine cannot remove builds")
            return
        removed = remove(str(params.get("precision") or ""))
        self._reply(request_id, {"removed": bool(removed)})

    # ---- Apple Books notes transfer ------------------------------------
    # The reader, planner, writer and backup machinery are the exact modules
    # the Qt shell shipped; this layer only speaks JSON. The one write this
    # server can make outside its own data lands in Apple Books' database,
    # so the order is sacred: plan again, back up, then copy - and the copy
    # itself is atomic.

    def _notes(self):
        if self._notes_deps is None:
            from vieneu_reader.integrations import apple_books as reading
            from vieneu_reader.integrations import apple_books_writer as writing

            library = reading.AppleBooksLibrary()
            self._notes_deps = {
                "library": library,
                "plan": lambda source, target: reading.build_transfer_plan(
                    library, source, target
                ),
                "copy": writing.copy_annotations,
                "back_up": writing.back_up,
                "prune": writing.prune_backups,
                "books_running": writing.apple_books_is_running,
                "errors": reading,
                "writer_errors": writing,
            }
        return self._notes_deps

    def _notes_error_token(self, error: Exception) -> str:
        from vieneu_reader.integrations import apple_books as reading

        if isinstance(error, reading.AppleBooksNotPermitted):
            return "not_permitted"
        if isinstance(error, reading.AmbiguousAsset):
            return "ambiguous"
        if isinstance(error, reading.UnknownAsset):
            return "book_gone"
        if isinstance(error, reading.SameBook):
            return "same_book"
        # Unavailable/Unreadable carry user-ready sentences of their own.
        return str(error) or "unavailable"

    # ── Apple Books → ReadEase, one way ─────────────────────────────────
    _APPLE_MAX_BYTES = 200 * 1024 * 1024

    def _apple_pairings(self):
        """Apple asset → local book: by the link a sync wrote, else by title
        (shown in the shelf, so a wrong pair is seen rather than suffered)."""
        from vieneu_reader.integrations.apple_books_sync import same_title

        deps = self._notes()
        apple = deps["library"].books()
        stored = self._repository.list_books() if self._repository else ()
        links = self._repository.apple_book_links() if self._repository else {}
        pairs: dict[str, str] = {}
        for book in apple:
            linked = links.get(book.asset_id)
            if linked and any(item.book.id == linked for item in stored):
                pairs[book.asset_id] = linked
                continue
            twin = next((item for item in stored if same_title(item.book.title, book.title)), None)
            if twin is not None:
                pairs[book.asset_id] = twin.book.id
        return apple, stored, pairs

    def _applebooks_shelf(self, request_id: Any) -> None:
        from pathlib import Path
        from vieneu_reader.integrations.apple_books_sync import (
            HIGHLIGHT_KIND, folder_is_encrypted, folder_size,
        )

        if self._repository is None or self._service is None:
            self._fail(request_id, "no library on this server")
            return
        deps = self._notes()
        try:
            apple, stored, pairs = self._apple_pairings()
            notes = deps["library"].annotations_for(*[book.asset_id for book in apple])
        except Exception as error:  # noqa: BLE001 - token or sentence
            self._fail(request_id, self._notes_error_token(error))
            return
        titles = {item.book.id: item.book.title for item in stored}
        rows = []
        for book in apple:
            folder = Path(book.path) if book.path else None
            highlights = sum(
                1 for a in notes.get(book.asset_id, ())
                if a.kind == HIGHLIGHT_KIND and (a.selected_text or "").strip()
            )
            paired = pairs.get(book.asset_id)
            if paired:
                status = "linked"
            elif folder is None or not folder.exists():
                status = "missing"
            elif folder.is_dir() and folder_is_encrypted(folder):
                status = "encrypted"
            elif (folder_size(folder) if folder.is_dir() else folder.stat().st_size) > self._APPLE_MAX_BYTES:
                status = "too_large"
            else:
                status = "importable"
            rows.append({
                "asset_id": book.asset_id,
                "title": book.title,
                "status": status,
                "book_id": paired,
                "paired_title": titles.get(paired) if paired else None,
                "highlights": highlights,
            })
        self._reply(request_id, {"books": rows})

    def _applebooks_import(self, request_id: Any, params: dict[str, Any]) -> None:
        import tempfile
        from pathlib import Path
        from vieneu_reader.integrations.apple_books_sync import (
            folder_is_encrypted, folder_size, pack_epub_folder,
        )

        if self._repository is None or self._service is None:
            self._fail(request_id, "no library on this server")
            return
        asset_id = str(params.get("asset_id") or "")
        deps = self._notes()
        try:
            book = deps["library"].book(asset_id)
        except Exception as error:  # noqa: BLE001
            self._fail(request_id, self._notes_error_token(error))
            return
        source = Path(book.path) if book.path else None
        if source is None or not source.exists():
            self._fail(request_id, "book_missing")
            return
        if source.is_dir() and folder_is_encrypted(source):
            self._fail(request_id, "encrypted")
            return
        size = folder_size(source) if source.is_dir() else source.stat().st_size
        if size > self._APPLE_MAX_BYTES:
            self._fail(request_id, "too_large")
            return
        try:
            with tempfile.TemporaryDirectory() as scratch:
                if source.is_dir():
                    packed = pack_epub_folder(source, Path(scratch) / "apple-books.epub")
                else:
                    packed = source
                result = self._service.import_book(packed)
        except Exception as error:  # noqa: BLE001 - the importer's own sentence
            self._fail(request_id, str(error))
            return
        self._repository.link_apple_book(asset_id, result.book.id)
        self._reply(request_id, {
            "book_id": result.book.id,
            "title": result.book.title,
            "was_existing": bool(getattr(result, "was_existing", False)),
        })

    def _applebooks_sync_notes(self, request_id: Any, params: dict[str, Any]) -> None:
        from vieneu_reader.integrations.apple_books_sync import SegmentRef, match_annotations
        from vieneu_reader.storage.repository import StoredAnnotation

        if self._repository is None or self._service is None:
            self._fail(request_id, "no library on this server")
            return
        asset_id = str(params.get("asset_id") or "")
        deps = self._notes()
        try:
            _apple, _stored, pairs = self._apple_pairings()
            annotations = deps["library"].annotations(asset_id)
        except Exception as error:  # noqa: BLE001
            self._fail(request_id, self._notes_error_token(error))
            return
        book_id = pairs.get(asset_id)
        stored = self._repository.get_book(book_id) if book_id else None
        if stored is None:
            self._fail(request_id, "not_in_library")
            return
        segments = [
            SegmentRef(index, segment.id, segment.text)
            for index, chapter in enumerate(stored.book.chapters)
            for segment in chapter.segments
        ]
        report = match_annotations(segments, annotations)
        # What comes over (owner, 02/09): "highlights" = the passages, their
        # notes left behind; "notes" = only passages that carry a note, with
        # it; "both" (default) = everything matched.
        mode = str(params.get("mode") or "both")
        if mode not in ("both", "highlights", "notes"):
            self._fail(request_id, f"unknown mode: {mode}")
            return
        kept = [
            item for item in report.matched
            if mode != "notes" or item.note
        ]
        self._repository.replace_annotations(stored.book.id, "applebooks", [
            StoredAnnotation(
                id=item.id, segment_id=item.segment_id, selected_text=item.selected_text,
                note=None if mode == "highlights" else item.note,
                style=item.style, source="applebooks",
            )
            for item in kept
        ])
        self._repository.link_apple_book(asset_id, stored.book.id)
        self._reply(request_id, {
            "book_id": stored.book.id,
            "matched": len(kept),
            "unmatched": report.unmatched,
            "skipped": report.skipped + (len(report.matched) - len(kept)),
        })

    def _annotations_delete(self, request_id: Any, params: dict[str, Any]) -> None:
        """Remove one highlight for good.

        For good is the point (owner, 03/09): the repository keeps a
        tombstone, so the next Apple Books sync will not hand it back.
        """

        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        annotation_id = str(params.get("annotation_id") or "")
        if not book_id or not annotation_id:
            self._fail(request_id, "book_id and annotation_id are required")
            return
        removed = self._repository.forget_annotation(book_id, annotation_id)
        self._reply(request_id, {"removed": removed})

    def _annotations_update(self, request_id: Any, params: dict[str, Any]) -> None:
        """Rewrite one highlight's note.

        The repository keeps the edit, so the next Apple Books sync will not
        overwrite the person's own words with the ones the highlight came
        with. `updated` is false when there is no such highlight any more -
        the shell needs to tell that from a note that saved.
        """

        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        annotation_id = str(params.get("annotation_id") or "")
        if not book_id or not annotation_id:
            self._fail(request_id, "book_id and annotation_id are required")
            return
        note = params.get("note")
        updated = self._repository.edit_annotation(
            book_id, annotation_id, None if note is None else str(note)
        )
        self._reply(request_id, {"updated": updated})

    def _notes_books(self, request_id: Any) -> None:
        deps = self._notes()
        try:
            books = deps["library"].books()
        except Exception as error:  # noqa: BLE001 - token or sentence
            self._fail(request_id, self._notes_error_token(error))
            return
        self._reply(request_id, {
            "books": [
                {
                    "asset_id": book.asset_id,
                    "title": book.title,
                    "edition_id": book.edition_id,
                    "progress": book.reading_progress,
                }
                for book in books
            ],
        })

    def _plan_payload(self, plan) -> dict[str, Any]:
        return {
            "source_title": plan.source.title,
            "target_title": plan.target.title,
            "same_edition": plan.same_edition,
            "copyable": len(plan.copyable),
            "items": [
                {
                    "kind": item.annotation.kind,
                    "has_note": item.annotation.has_note,
                    "excerpt": (item.annotation.note
                                or item.annotation.selected_text or "")[:160],
                    "verdict": item.verdict,
                }
                for item in plan.items[:200]
            ],
            "total": len(plan.items),
        }

    def _notes_plan(self, request_id: Any, params: dict[str, Any]) -> None:
        deps = self._notes()
        try:
            plan = deps["plan"](
                str(params.get("source") or ""), str(params.get("target") or "")
            )
        except Exception as error:  # noqa: BLE001
            self._fail(request_id, self._notes_error_token(error))
            return
        self._reply(request_id, self._plan_payload(plan))

    def _notes_transfer(self, request_id: Any, params: dict[str, Any]) -> None:
        deps = self._notes()
        source = str(params.get("source") or "")
        target = str(params.get("target") or "")
        try:
            plan = deps["plan"](source, target)
        except Exception as error:  # noqa: BLE001
            self._fail(request_id, self._notes_error_token(error))
            return

        def outcome(name: str, **extra: Any) -> None:
            self._reply(request_id, {"outcome": name, **extra})

        if not plan.items:
            outcome("no_notes")
            return
        if not plan.copyable:
            outcome("all_already_there", count=len(plan.items))
            return
        database = deps["library"].annotation_database
        if database is None:
            outcome("unsupported")
            return
        if deps["books_running"]():
            outcome("books_open")
            return
        if self._backup_root is None:
            outcome("backup_failed")
            return
        from datetime import datetime

        destination = (
            self._backup_root / datetime.now().strftime("%Y-%m-%d-%H%M%S")
        )
        try:
            backup = deps["back_up"](database, destination)
        except OSError:
            outcome("backup_failed")
            return
        writing = deps["writer_errors"]
        try:
            written = deps["copy"](
                database,
                source,
                target,
                backup=backup,
                only_locations={
                    item.annotation.location for item in plan.copyable
                },
                books_is_running=deps["books_running"],
            )
        except writing.AppleBooksBusy:
            outcome("books_open")
            return
        except writing.NothingToCopy:
            outcome("already_there")
            return
        except Exception:  # noqa: BLE001 - copy is atomic; name the backup
            outcome("copy_failed", backup=str(backup))
            return
        deps["prune"](self._backup_root)
        outcome("copied", written=written, target_title=plan.target.title)

    # "voice" and "rate" are the Qt shell's own keys, in the Qt shell's own
    # settings file: a reader who picked Thu Hà at 1.25x before the rewrite
    # still has that when the new shell opens. Chosen deliberately over new
    # names - the file survived the rebrand, and it survives this too.
    # An outside voice provider's key is WRITE-ONLY over this pipe. The
    # webview may set one and ask whether one is set; it can never read one
    # back. The key belongs to this machine (the owner's condition for the
    # feature), and the webview is the one place in the app that renders
    # arbitrary strings to a screen - so the value simply never goes there,
    # and no future rendering bug can spill it.
    _SECRET_CONFIG_KEYS = frozenset({
        "openai_api_key",
        "elevenlabs_api_key",
    })
    _CONFIG_KEYS = frozenset({
        "tauri_selection_shortcut",
        "ui_language",
        "voice",
        # Which voices the switcher offers. The shell writes this through
        # config.set like every other preference; leaving it out of this set
        # meant the engine answered "unknown config key" to a key the shell
        # asks for on every launch - and the shell read that refusal as a
        # result, crashed its own voice-loading chain, and blamed the
        # catalogue it had already loaded (owner, 05/09).
        "voice_shortlist",
        "rate",
        "external_voice_budget",
        "openai_model",
        "elevenlabs_model",
    }) | _SECRET_CONFIG_KEYS

    def _config_get(self, request_id: Any, params: dict[str, Any]) -> None:
        from vieneu_reader.settings import load_settings

        key = str(params.get("key") or "")
        if key not in self._CONFIG_KEYS or self._settings_path is None:
            self._fail(request_id, f"unknown config key: {key}")
            return
        value = load_settings(self._settings_path).get(key)
        if key in self._SECRET_CONFIG_KEYS:
            # "Is one set" is the only question the shell needs answered, and
            # the only one it gets. A settings screen shows "đã đặt", never
            # the key.
            self._reply(request_id, {"value": None, "set": bool(value)})
            return
        self._reply(request_id, {"value": value})

    def _config_set(self, request_id: Any, params: dict[str, Any]) -> None:
        from vieneu_reader.settings import update_settings

        key = str(params.get("key") or "")
        if key not in self._CONFIG_KEYS or self._settings_path is None:
            self._fail(request_id, f"unknown config key: {key}")
            return
        update_settings(self._settings_path, {key: params.get("value")})
        self._reply(request_id, {"saved": True})

    def _config_verify_key(self, request_id: Any, params: dict[str, Any]) -> None:
        """Save a provider credential, then ask the provider whether it works.

        Saving and checking are one request because they are one act: the
        shell used to save, re-list the catalogue, and treat "some paid voice
        appeared" as proof. That is proof for ElevenLabs, whose catalogue is
        a live authenticated call - and no proof at all for OpenAI, whose
        nine voices are a constant that never leaves this machine. Any
        non-empty string was accepted and reported as checked; the first
        thing that actually knew was a chapter half read.

        An empty value clears the key, which needs no check.
        """

        from vieneu_reader.settings import update_settings

        provider = str(params.get("provider") or "")
        key_name = KEY_FOR_PROVIDER.get(provider)
        if key_name is None or self._settings_path is None:
            self._fail(request_id, f"unknown provider: {provider}")
            return
        value = str(params.get("value") or "")
        if not value:
            update_settings(self._settings_path, {key_name: ""})
            self._reply(request_id, {"saved": True, "ok": False, "code": "no_key"})
            return

        settings = dict(self._settings_document())
        settings[key_name] = value
        model = chosen_model(provider, settings)
        external = _external_provider(provider, f"{provider}:{model}:x", settings)
        if external is None:
            self._fail(request_id, f"unknown provider: {provider}")
            return
        try:
            external.verify()
        except ExternalVoiceError as error:
            # NOT saved. A key the service refuses is not a setting worth
            # keeping - it would sit there looking configured and fail again
            # at the worst moment.
            self._reply(request_id, {"saved": False, "ok": False, "code": error.code})
            return
        update_settings(self._settings_path, {key_name: value})
        self._reply(request_id, {"saved": True, "ok": True})

    def _model_status(self, request_id: Any) -> None:
        engine = self._engine

        def value_of(name, fallback):
            attribute = getattr(engine, name, fallback)
            return attribute() if callable(attribute) else attribute

        # The real engine exposes is_model_ready as a method and precision as
        # a property; fakes may do either. Both shapes are answers.
        ready = value_of("is_model_ready", True)
        precision = value_of("precision", None)
        builds = value_of("installed_builds", dict)
        self._reply(request_id, {
            "ready": bool(ready),
            "precision": precision,
            "installed": {str(key): int(value) for key, value in builds.items()},
        })

    def _library_import(self, request_id: Any, params: dict[str, Any]) -> None:
        if self._service is None:
            self._fail(request_id, "no library on this server")
            return
        source = str(params.get("path") or "")
        try:
            result = self._service.import_book(Path(source))
        except BookImportError as error:
            self._fail(request_id, str(error))
            return
        except OSError as error:
            self._fail(request_id, f"import failed: {error}")
            return
        self._reply(request_id, {
            "book_id": result.book.id,
            "title": result.book.title,
            "source_format": result.book.source_format,
            "was_existing": result.was_existing,
        })

    def _library_remove(self, request_id: Any, params: dict[str, Any]) -> None:
        if self._service is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        removed = self._service.remove_book(book_id)
        if not removed:
            self._fail(request_id, f"unknown book: {book_id}")
            return
        self._reply(request_id, {"removed": True})

    def _book_open(self, request_id: Any, params: dict[str, Any]) -> None:
        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        stored = self._repository.get_book(book_id)
        if stored is None:
            self._fail(request_id, f"unknown book: {book_id}")
            return
        progress = self._repository.load_progress(book_id)
        figures_by_chapter: dict[str, list[dict[str, Any]]] = {}
        if self._service is not None:
            presentation = self._service.presentation_for(
                stored.book, stored.managed_path
            )
            for chapter in presentation.chapters:
                figures_by_chapter[chapter.chapter_id] = [
                    {
                        "id": figure.id,
                        "anchor_segment_id": figure.anchor_segment_id,
                        "placement": figure.placement,
                        "alt": figure.alt_text,
                        # Per chapter, matching the spoken cue exactly.
                        "number": number,
                        # "Image" and friends: an alt that names nothing. The
                        # shell hides it instead of captioning a picture
                        # with the word Image.
                        "alt_is_generic": bool(figure.alt_is_generic),
                    }
                    for number, figure in enumerate(chapter.figures, start=1)
                ]
        self._reply(request_id, {
            "book": {
                "id": stored.book.id,
                "title": stored.book.title,
                "source_format": stored.book.source_format,
                "chapters": [
                    {
                        "id": chapter.id,
                        "title": chapter.title,
                        "figures": figures_by_chapter.get(chapter.id, []),
                        "segments": [
                            {
                                "id": segment.id,
                                "text": segment.text,
                                "kind": segment.kind,
                            }
                            for segment in chapter.segments
                        ],
                    }
                    for chapter in stored.book.chapters
                ],
            },
            "annotations": [
                {
                    "id": item.id,
                    "segment_id": item.segment_id,
                    "selected_text": item.selected_text,
                    "note": item.note,
                    "style": item.style,
                }
                for item in self._repository.annotations_for(book_id)
            ],
            "progress": {
                "segment_id": progress.segment_id if progress else None,
                "rate": progress.playback_rate if progress else 1.0,
                "voice_id": progress.voice_id if progress else None,
            },
        })

    def _book_cover(self, request_id: Any, params: dict[str, Any]) -> None:
        """A book's cover for the shelf - `null` fields when it has none,
        which is an ordinary answer, not an error."""
        if self._repository is None or self._service is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        stored = self._repository.get_book(book_id)
        if stored is None:
            self._fail(request_id, f"unknown book: {book_id}")
            return
        cover = self._service.cover_for(stored.book, stored.managed_path)
        if cover is None:
            self._reply(request_id, {"media_type": None, "data": None})
            return
        data, media_type = cover
        self._reply(request_id, {
            "media_type": media_type,
            "data": base64.b64encode(data).decode("ascii"),
        })

    def _book_figure(self, request_id: Any, params: dict[str, Any]) -> None:
        """One figure's bytes, on demand - never the whole book's."""
        if self._repository is None or self._service is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        figure_id = str(params.get("figure_id") or "")
        stored = self._repository.get_book(book_id)
        if stored is None:
            self._fail(request_id, f"unknown book: {book_id}")
            return
        presentation = self._service.presentation_for(
            stored.book, stored.managed_path
        )
        wanted = next(
            (
                figure
                for chapter in presentation.chapters
                for figure in chapter.figures
                if figure.id == figure_id
            ),
            None,
        )
        if wanted is None:
            self._fail(request_id, f"unknown figure: {figure_id}")
            return
        assets = self._service.assets_for(
            stored.book, stored.managed_path, (wanted,)
        )
        # Keyed by the member name inside the EPUB, never by figure id -
        # `load_epub_assets` returns `{asset_path: bytes}`. Asking for the id
        # missed every time, so no figure ever loaded in this shell; the Qt
        # controller had it right (`assets.get(figure.asset_path)`).
        data = assets.get(wanted.asset_path)
        if not data:
            self._fail(request_id, f"figure unavailable: {figure_id}")
            return
        self._reply(request_id, {
            "media_type": wanted.media_type,
            "data": base64.b64encode(data).decode("ascii"),
        })

    def _settings_document(self) -> dict[str, Any]:
        from vieneu_reader.settings import load_settings

        if self._settings_path is None:
            return {}
        return load_settings(self._settings_path)

    def _budget(self, settings: dict[str, Any]) -> float | None:
        raw = settings.get("external_voice_budget")
        try:
            limit = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        return limit if limit > 0 else None

    def _voice_engine(
        self, voice_id: str, settings: dict[str, Any]
    ) -> tuple[Any, "VoicePrice | None", str | None]:
        """The engine for this voice, its price, and why not if not.

        A paid voice that cannot be paid for is REFUSED by name rather than
        quietly answered by the local model: hearing a different voice than
        the one you picked, with no explanation, is worse than being told the
        key is missing.
        """

        price = price_for(model_of(voice_id) or "")
        self._spend.set_limit(self._budget(settings))
        route = pick_voice_route(
            voice_id,
            keys=settings,
            would_exceed_budget=(
                price is not None and self._spend.snapshot().exhausted
            ),
        )
        if route.kind == "local":
            return self._engine, None, None
        if route.kind == "blocked":
            return None, price, route.reason
        provider = _external_provider(route.provider or "", voice_id, settings)
        if provider is None:
            return None, price, "no_key"
        return ExternalSpeechEngine(provider), price, None

    def _sentence_cache_key(
        self, engine: Any, sentence: str, voice_id: str, settings: SynthesisSettings
    ) -> str | None:
        """Where this sentence's audio lives, or None if nothing is cached.

        Keyed on what the SOUND depends on: the sentence as it will be sent,
        the voice, and who is speaking it. `engine_version`/`model_revision`
        come off the engine, so a paid provider's audio can never be served
        for the local model or the other way round - they are different
        engines with different versions, which is what the key is for.
        """

        if self._audio_cache is None:
            return None
        engine_version = getattr(engine, "engine_version", "")
        model_revision = getattr(engine, "model_revision", "")
        if not engine_version:
            # A fake or a stub engine has no identity to key on; caching audio
            # under an empty name would let two of them collide.
            return None
        return audio_cache_key(
            sentence,
            voice_id,
            str(engine_version),
            str(model_revision),
            settings,
            # Bumped when the way a sentence becomes sound changes in a manner
            # the sentence text does not show.
            reading_revision="headless-sentence-1",
        )

    def _sentence_audio(
        self,
        engine: Any,
        sentence: str,
        voice_id: str,
        settings: SynthesisSettings,
        fresh: list[AudioChunk],
    ) -> Iterator[AudioChunk]:
        """This sentence as audio, from the cache when it is there.

        What is cached is PRE-STRETCH: the rate is applied on the way out, so
        one entry serves 1× and 1.5× alike rather than buying the sentence
        again for every speed.
        """

        key = self._sentence_cache_key(engine, sentence, voice_id, settings)
        if key is not None:
            assert self._audio_cache is not None
            cached = self._audio_cache.get(key)
            if cached is not None:
                yield cached
                return
        for chunk in engine.stream(sentence, voice_id, settings):
            fresh.append(chunk)
            yield chunk

    def _remember_sentence(
        self,
        engine: Any,
        sentence: str,
        voice_id: str,
        settings: SynthesisSettings,
        fresh: list[AudioChunk],
    ) -> None:
        """Keep a sentence that was spoken all the way through."""

        if not fresh or self._audio_cache is None:
            return
        key = self._sentence_cache_key(engine, sentence, voice_id, settings)
        if key is None:
            return
        try:
            self._audio_cache.put_complete(key, fresh)
        except Exception:  # noqa: BLE001
            # A full disk, a quota, a racing sibling process: the reading has
            # already been heard, and failing it now over bookkeeping would
            # turn a saved-nothing into a stopped-reading.
            pass

    def _speak(
        self,
        request_id: Any,
        utterances: list[_Utterance],
        voice_id: str,
        rate: float,
        settings: SynthesisSettings,
        *,
        book_id: str | None = None,
        window: Any = None,
    ) -> None:
        # Which engine speaks this - the local model, or a provider on the
        # reader's own key. Decided once, here, so the sentence loop below is
        # the same road for both.
        document = self._settings_document()
        engine, price, blocked = self._voice_engine(voice_id, document)
        if engine is None:
            # Named, not silently swapped for the local voice: hearing a
            # different voice than the one you chose, with no reason given,
            # is the worse outcome.
            self._fail(request_id, f"voice_unavailable: {blocked}")
            return

        # Rate rides the same stretcher as the Qt app, so a 1.5× reading
        # sounds identical over the pipe. Rests are pure zeros: scaling
        # their length arithmetically is exact, so they skip the stretcher.
        stretcher = TimeStretcher(rate) if rate != 1.0 else None
        seq = 0
        voiced = 0
        stopped = False
        # The shell's window for this reading, if it asked for one. Credits
        # from a previous reading die with it.
        self._credits = None if window is None else int(window)
        self._credit_read = request_id
        self._stop_pending = False
        if book_id is not None:
            self._listening[request_id] = (book_id, rate, voice_id)
            while len(self._listening) > 4:
                del self._listening[next(iter(self._listening))]

        def emit(pcm: bytes, *, from_voice: bool) -> None:
            nonlocal seq, voiced
            if not self._await_credit():
                return
            self._send({
                "id": request_id,
                "event": "chunk",
                "seq": seq,
                "from_voice": from_voice,
                "pcm": base64.b64encode(pcm).decode("ascii"),
                "sample_rate": SAMPLE_RATE,
            })
            seq += 1
            if from_voice:
                voiced += 1

        try:
            for position, utterance in enumerate(utterances):
                if self._stop_requested():
                    stopped = True
                    break
                if utterance.segment_id is not None:
                    # Not `position`: that name is the loop index just above,
                    # and shadowing it broke the is_last arithmetic once.
                    where: dict[str, Any] = {
                        "id": request_id,
                        "event": "position",
                        "segment_id": utterance.segment_id,
                    }
                    if utterance.figure_id is not None:
                        where["figure_id"] = utterance.figure_id
                    # A position rides the shell's queue like a chunk does,
                    # so it spends a credit like one. Progress is NOT saved
                    # here: the engine is minutes ahead of the ear, and what
                    # was written at this point used to resume a restart
                    # past content nobody had heard. The shell says when the
                    # ear arrives (`progress.reached`).
                    if not self._await_credit():
                        stopped = True
                        break
                    self._send(where)
                sentences = split_sentences(utterance.text)
                if not sentences and utterance.text.strip():
                    sentences = (utterance.text,)
                for index, sentence in enumerate(sentences):
                    if index:
                        emit(_silence(int(SENTENCE_PAUSE_MS / rate)),
                             from_voice=False)
                    # Anything the engine actually produced this time, kept so
                    # it can be remembered - but only once the sentence is
                    # WHOLE. Half a sentence in the cache would be handed back
                    # as a finished one for ever after.
                    fresh: list[AudioChunk] = []
                    if price is not None:
                        # The ceiling is asked BEFORE the characters go out.
                        # A limit noticed on the way back is not a limit.
                        cost = price.usd_for(len(sentence))
                        if self._spend.would_exceed(cost):
                            self._fail(request_id, "voice_unavailable: budget")
                            return
                    for chunk in self._sentence_audio(
                        engine, sentence, voice_id, settings, fresh
                    ):
                        if self._stop_requested():
                            stopped = True
                            break
                        samples = np.frombuffer(chunk.pcm, dtype=np.float32)
                        if stretcher is None:
                            emit(chunk.pcm, from_voice=True)
                        else:
                            ready = stretcher.feed(samples)
                            if ready.size:
                                emit(ready.astype(np.float32).tobytes(),
                                     from_voice=True)
                    if stopped:
                        break
                    self._remember_sentence(engine, sentence, voice_id, settings, fresh)
                    if price is not None and fresh:
                        # Only what was actually synthesised is counted: a
                        # sentence answered from the cache cost nothing, and
                        # a meter that charged for it would be lying.
                        running = self._spend.add(
                            len(sentence), price.usd_for(len(sentence))
                        )
                        self._send({
                            "id": request_id,
                            "event": "spend",
                            "chars": running.chars,
                            "usd": running.usd,
                        })
                if stretcher is not None:
                    # Drain per utterance: the tail lands before the rest that
                    # follows it, and a stop never strands buffered audio.
                    tail = stretcher.drain()
                    if tail.size:
                        emit(tail.astype(np.float32).tobytes(),
                             from_voice=True)
                if stopped:
                    break
                is_last = position + 1 == len(utterances)
                if utterance.pause_after_ms and not is_last:
                    emit(_silence(int(utterance.pause_after_ms / rate)),
                         from_voice=False)
        except ExternalVoiceError as error:
            # A word the shell can act on: a refused key, an empty account and
            # a dropped connection are three different next steps.
            self._fail(request_id, f"voice_failed: {error.code}: {error.message}")
            return
        except Exception as error:  # noqa: BLE001 - the pipe must survive
            self._fail(request_id, f"read failed: {error}")
            return
        # A stop that arrived on the last frame was answered; nothing is left
        # for it to cut short, and it must not cut the next reading instead.
        self._stop_pending = False
        self._credits = None
        self._reply(request_id, {
            "frames": seq,
            "voiced_frames": voiced,
            "stopped": stopped,
        })


def serve(
    reader: TextIO,
    writer: TextIO,
    engine: ReadingEngine,
    *,
    repository: "LibraryRepository | None" = None,
    service: "LibraryService | None" = None,
    settings_path: "Path | None" = None,
    notes_deps: "dict[str, Any] | None" = None,
    audio_cache: "AudioCache | None" = None,
) -> None:
    """Answer requests until the reader closes."""
    _Session(
        reader, writer, engine,
        repository=repository, service=service, settings_path=settings_path,
        notes_deps=notes_deps, audio_cache=audio_cache,
    ).run()


def main() -> int:
    from vieneu_reader.config import AppPaths, default_app_root
    from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore
    from vieneu_reader.speech.vieneu import VieNeuSpeechEngine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=None)
    arguments = parser.parse_args()

    paths = AppPaths.create(arguments.data_root or default_app_root())
    quality = VoiceQualityPreferenceStore(paths.root / "settings.json")
    engine = VieNeuSpeechEngine(paths.models, precision=quality.load())
    repository = LibraryRepository(paths.database)
    service = LibraryService(paths, repository)
    # The Qt shell had this and the new one did not, so every re-read paid the
    # model again. It matters more once a voice bills by the character: a
    # sentence already spoken must never be bought twice.
    audio_cache = AudioCache(paths.cache / "Audio")

    # The SDK prints progress to stdout; the protocol channel must stay clean.
    protocol = sys.stdout
    sys.stdout = sys.stderr
    serve(
        sys.stdin, protocol, engine,
        repository=repository, service=service,
        settings_path=paths.root / "settings.json",
        audio_cache=audio_cache,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
