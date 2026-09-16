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

A `stop` covers every reading asked for before it: the one streaming, and
any `read`/`read.book` still queued behind a reading or a model download
(each of those answers `{"frames": 0, "voiced_frames": 0, "stopped": true}`
without a frame). It does not touch a download; that has its own
`{"id": 5, "method": "model.cancel"}`, answered from inside the download the
way a stop is answered from inside a reading.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import json
import sys
import threading
import time
from hashlib import sha256
from pathlib import Path
from queue import SimpleQueue
from typing import Any, Iterator, Protocol, TextIO

import numpy as np

from vieneu_reader.domain.models import AudioChunk, Segment, Voice
from vieneu_reader.domain.language import (
    language_in_use,
    language_of_text,
    language_of_texts,
)
from vieneu_reader.domain.presentation import figure_label
from vieneu_reader.domain.prosody import (
    SENTENCE_PAUSE_MS,
    pause_after_ms,
    selection_pause_ms,
    speak_with_notes,
    DEFAULT_SPEECH_LANGUAGE,
    SPEECH_LANGUAGES,
    speech_language,
    speakable_text,
    split_sentences,
)
from vieneu_reader.domain.segmenter import split_transient_parts

#: The language the second local model reads.
ENGLISH = "en"
from vieneu_reader.playback.time_stretch import SAMPLE_RATE, TimeStretcher
from vieneu_reader.speech.contracts import SynthesisSettings
from vieneu_reader.importers.errors import BookImportError
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.speech.cache import AudioCache, audio_cache_key
from vieneu_reader.speech.external.estimate import (
    estimate_scope, scope_end, scope_start,
)
from vieneu_reader.speech.external.pricing import PRICES, price_for
from vieneu_reader.speech.external.provider import ExternalVoiceError
from vieneu_reader.speech.external.engine import ExternalSpeechEngine
from vieneu_reader.speech.external.pricing import VoicePrice
from vieneu_reader.speech.external.route import (
    KEY_FOR_PROVIDER, model_of, pick_voice_route, provider_of,
)
from vieneu_reader.speech.external.spend import SpendMeter
from vieneu_reader.speech.kokoro import (
    DOWNLOAD_BYTES as ENGLISH_DOWNLOAD_BYTES,
    VOICE_IDS as ENGLISH_VOICE_IDS,
)
from vieneu_reader.storage.errors import RepositoryCorruptionError
from vieneu_reader.storage.repository import (
    DamagedBook,
    LibraryRepository,
    Progress,
    StoredBook,
)

PROTOCOL_VERSION = 1

_EOF = object()


class ReadingEngine(Protocol):
    @property
    def engine_version(self) -> str: ...

    def voices(self) -> tuple[Voice, ...]: ...

    def stream(
        self, text: str, voice_id: str, settings: SynthesisSettings
    ) -> Iterator[AudioChunk]: ...


class EnglishEngine(ReadingEngine, Protocol):
    """The English model: a `ReadingEngine` that is downloaded on request."""

    @property
    def is_model_ready(self) -> bool: ...

    def prepare_model(self, progress_callback: Any) -> None: ...

    def installed_size(self) -> int: ...

    def remove(self) -> bool: ...

    def warm(self) -> bool: ...

    def gender_of(self, voice_id: str) -> str | None: ...


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
    # OpenAI's own words for it: "our newest and most reliable text-to-speech
    # model" [fetched 2026-09-10]. It replaced tts-1/tts-1-hd outright rather
    # than joining them - see `pricing.py` for what that cost in exactness.
    "openai": "gpt-4o-mini-tts",
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


#: How long a provider's refusal is taken at its word before it is asked
#: again - long enough that a dead network costs one wait, short enough that
#: a fixed one is noticed on the next visit to the voices panel.
_FAILURE_MEMORY = 60.0
#: Stands in for an error code while the background thread is still asking.
_PENDING = "pending"


def _catalogue_key(provider: str, model: str, key: str) -> tuple[str, str, str]:
    """The credential never sits in memory as a dictionary key: its digest
    does. A different key is a different question; the same key asked
    twice is the same answer."""
    return provider, model, sha256(key.encode("utf-8")).hexdigest()


def _is_ready(engine: Any) -> bool:
    """Whether a local model is on this Mac, whatever shape the engine gives
    the fact: the real one exposes `is_model_ready` as a property, fakes as
    a method or not at all - and an engine that never says is taken as
    ready, so a test double without the attribute keeps speaking."""

    attribute = getattr(engine, "is_model_ready", True)
    return bool(attribute() if callable(attribute) else attribute)


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


def _text_utterances(
    text: str,
    settings: SynthesisSettings,
    language: str = DEFAULT_SPEECH_LANGUAGE,
) -> list[_Utterance]:
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
    spoken = tuple(speakable_text(part.text, language=language) for part in parts)
    return [
        _Utterance(
            text=spoken[index],
            pause_after_ms=(
                selection_pause_ms(spoken[index], parts[index + 1].joint)
                if index + 1 < len(parts)
                else 0
            ),
            segment_id=f"part-{index}",
            source=parts[index].text,
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
    # The same words as WRITTEN. `text` is what the voice says, and
    # `speakable_text` has already been past it - shouted runs lowered,
    # ordinals rewritten - so it is the wrong thing to show a reader who
    # wants to see what was captured. A book hands its own text to the
    # shell through `book.open`; a plain read had no such door until
    # `text.parts` (09/09), and this field is what that door returns.
    source: str = ""
    # Set on the spoken cue for a picture ("Xem hình 3."): rides the position
    # event so the shell can bring the picture into view exactly when the ear
    # hears the cue, not when the model synthesised it.
    figure_id: str | None = None


# What the voice says when the reading reaches a picture, and the rest that
# follows so the listener has a beat to look. In the language being READ: this
# sentence is spoken aloud between two sentences of the book, so a Vietnamese
# one in the middle of an English chapter is a stumble, not a label.
FIGURE_CUE = {
    "vi": "Xem hình {number}.",
    "en": "See figure {number}.",
}
FIGURE_CUE_PAUSE_MS = 600

# What the voice says before a footnote, and the beat after it. On paper a
# small number sends the eye down the page and back; an ear has no such move,
# so the note is read where it belongs - after the sentence that carries the
# number - and it has to be ANNOUNCED, or it arrives as a non-sequitur in the
# middle of a paragraph. Two words, because a longer preamble said before
# eighty notes becomes the thing you hear instead of the notes (owner,
# 04/09: "nói thêm").
NOTE_CUE = {
    "vi": "Nói thêm, {text}",
    "en": "Also, {text}",
}
NOTE_CUE_PAUSE_MS = 450


@dataclass(frozen=True)
class _FigureCue:
    placement: str
    figure_id: str
    #: What the voice says: the book's own number ("1.3") when the caption
    #: or alt carries one, else the figure's count within its chapter.
    number: str
    #: The segment that captions this figure, if the book gave it one. The
    #: caption is then the announcement - no "Xem hình" on top of it.
    caption_segment_id: str | None


def _figure_cues(presentation: Any) -> dict[str, list[_FigureCue]]:
    """Per anchor segment, the figures announced there.

    Numbered per CHAPTER, not per book: the domain's running count is right
    for a print index, but "Xem hình 187" is not something a listener can
    hold in their head, and "Xem hình 3" is (owner's call, 2026-09-02). A
    book that numbers its own figures wins over both: "Xem hình 1.3" is
    what the text beside it says (owner, 05/09).
    """
    cues: dict[str, list[_FigureCue]] = {}
    for chapter in presentation.chapters:
        for figure, number in _figure_numbers(chapter.figures):
            if figure.duplicate_of is not None:
                # A translated copy of the picture just announced. The page
                # shows it; the voice has nothing new to say about it.
                continue
            labelled = figure_label(figure.label)
            cues.setdefault(figure.anchor_segment_id, []).append(_FigureCue(
                placement=figure.placement,
                figure_id=figure.id,
                number=labelled[1] if labelled else str(number),
                caption_segment_id=figure.caption_segment_id,
            ))
    return cues


def _figure_numbers(figures: Any) -> list[tuple[Any, int]]:
    """Each figure with its number within the chapter; a copy shares the
    number of the picture it repeats, so the page and the voice agree."""
    numbered: list[tuple[Any, int]] = []
    by_id: dict[str, int] = {}
    count = 0
    for figure in figures:
        if figure.duplicate_of is not None and figure.duplicate_of in by_id:
            number = by_id[figure.duplicate_of]
        else:
            count += 1
            number = count
        by_id[figure.id] = number
        numbered.append((figure, number))
    return numbered


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


class _PreparationCancelled(BaseException):
    """A model download the person asked to abandon.

    Not an `Exception`: it is raised from inside an engine's `prepare_model`,
    which wraps whatever goes wrong in there into its own "check the network"
    error - and a cancel wrapped that way came back as a failure, with the
    reader told to check a network that was fine. Outside that family, it
    passes through the way an interrupt does.
    """


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
        english_engine: "EnglishEngine | None" = None,
    ):
        self._writer = writer
        self._engine = engine
        # The second local model, for books in English - or None in a test
        # that has no use for it. Its voices are listed only once it is
        # downloaded, so choosing one can never be followed by a refusal
        # to speak (the same rule paid voices follow).
        self._english_engine = english_engine
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
        # A `model.cancel` seen while a download runs: honoured at its next
        # progress report, the only moment it hands control back.
        self._cancel_pending = False
        self._downloading = False
        # Whether the reading in progress is allowed to leave audio on disk.
        # Set per reading by `_speak`; false until one starts.
        self._cache_reading = False
        # What each book's own text reads as, remembered for this process.
        # A book's words do not change while it is on the shelf, and reading
        # them is 2.34 ms each - nothing once, half a second every time a
        # two-hundred-book shelf is listed.
        self._detected_languages: dict[tuple[str, str], str] = {}
        # What each recent reading was of, so a `progress.reached` for it -
        # which may land after its reply - can be written with the right
        # rate and voice. Bounded: only the last few readings matter.
        self._listening: dict[Any, tuple[str, float, str]] = {}
        # What each paid provider offered, remembered for this process and
        # keyed by the credential it was asked with - a new key is a new
        # question. ElevenLabs' catalogue is a network round trip (1-1.8 s
        # measured 14/09) that used to be paid on every listing, at start-up
        # ahead of the request that decides which screen to show. A failed
        # ask is remembered too, briefly, so a dead network costs one wait
        # rather than one per listing.
        self._catalogues: dict[
            tuple[str, str, str], tuple[tuple[Any, ...] | None, str | None, float]
        ] = {}
        self._catalogue_fetching: set[tuple[str, str, str]] = set()
        self._catalogue_lock = threading.Lock()
        # Two threads may have something to say - the request loop and a
        # background fetch - and a line is only a line if it is written whole.
        self._send_lock = threading.Lock()
        # Which local models have been asked to load, so choosing a voice
        # twice does not load its model twice. The threads are kept so a
        # test can wait for them; the app never needs to.
        self._warm_lock = threading.Lock()
        self._warmed: set[Any] = set()
        self._warm_threads: list[threading.Thread] = []
        pump = threading.Thread(
            target=self._pump, args=(reader,), daemon=True
        )
        pump.start()

    def start_background_work(self) -> None:
        """What can be done before anybody asks: load the model the reader
        uses so the first reading does not have to, and ask the paid
        providers for their catalogues so the first listing does not have
        to wait on the network. Both off the request thread; neither is
        required for any answer, so a failure here is a slower answer
        later, not an error.

        One model, not both. Each local model is a few hundred MB resident
        once loaded (measured 15/09 in the frozen engine: the English one
        adds ~525 MB), and a reader who stays in one language would pay for
        the other on every launch. So the model of the saved voice is
        warmed here; the other one warms the moment a voice of it is
        chosen (`config.set voice`, which every path in the shell goes
        through), and loads on demand if a reading gets there first. A
        saved voice that names no local model - none yet, or a paid one -
        warms the Vietnamese model when it is on this Mac, else the English
        one: the model the reader uses, or the one there is.
        """
        threading.Thread(
            target=self._warm_for_start, name="model-warm", daemon=True
        ).start()
        threading.Thread(
            target=self._prefetch_catalogues, name="voices-prefetch", daemon=True
        ).start()

    def _warm_for_start(self) -> None:
        voice = str(self._settings_document().get("voice") or "")
        engine = self._local_engine_of(voice)
        if engine is None:
            # No local voice saved: the Vietnamese model if it is here, else
            # the English one - never both, never a model that is not.
            engine = self._engine if _is_ready(self._engine) else self._english_engine
        self._warm(engine)

    def _local_engine_of(self, voice_id: str) -> Any:
        """The local model a voice belongs to, or None for a paid voice, no
        voice, or a model that is not on this Mac. The same split as
        `_voice_engine`: a bare name is local, and local is the English
        model for its six names and the Vietnamese one for any other -
        without asking the Vietnamese model for its list, which on a fresh
        install would load it, on whatever thread asked."""
        if not voice_id or provider_of(voice_id) is not None:
            return None
        english = self._english_engine
        if english is not None and voice_id in ENGLISH_VOICE_IDS:
            return english if english.is_model_ready else None
        return self._engine if _is_ready(self._engine) else None

    def _warm(self, engine: Any) -> None:
        """Load a model now, on this thread, unless it is not here or is
        already loading or loaded. Nothing to say either way: a failure is
        a slower first sentence later, and the reading path reports its own."""
        warm = getattr(engine, "warm", None)
        if engine is None or not callable(warm):
            return
        with self._warm_lock:
            if engine in self._warmed:
                return
            self._warmed.add(engine)
        if not warm():
            with self._warm_lock:
                self._warmed.discard(engine)

    def _warm_later(self, engine: Any) -> None:
        """`_warm`, off the request thread - the reply that prompted it must
        not wait on a model load."""
        if engine is None:
            return
        thread = threading.Thread(target=self._warm, args=(engine,), name="model-warm", daemon=True)
        self._warm_threads.append(thread)
        thread.start()

    def _pump(self, reader: TextIO) -> None:
        for line in reader:
            line = line.strip()
            if line:
                self._requests.put(line)
        self._requests.put(_EOF)

    def _send(self, payload: dict[str, Any]) -> None:
        with self._send_lock:
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
        # Asked at the moment a scanned passage STARTS being read, so the
        # reader can follow it. Held until the reading ended, the answer
        # would arrive after the only minute it was for.
        "text.parts",
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
            self._drop_queued("read", "read.book")
        elif method == "model.cancel":
            # True when there is a download to cancel - running, or still
            # queued behind the reading this poll belongs to.
            queued = self._drop_queued("model.prepare")
            self._reply(request.get("id"), {"cancelled": self._downloading or queued})
            self._cancel_pending = True
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

    def _drop_queued(self, *methods: str) -> bool:
        """Answer, as stopped, the deferred requests of these methods; True
        if there were any.

        A stop covers everything asked for BEFORE it, not only what happens
        to be running. A reading queued behind a download (Đọc pressed
        while a model downloads, then Dừng) or behind another reading (two
        quick presses: stop+read, stop+read, of which one stop was spent on
        the reading in flight) used to start AFTER the stop, for a shell
        that had already dropped its id - so nobody credited its frames,
        and once past the window it waited for room forever, with every
        later reading queued behind it. To the person: no voice until the
        app was relaunched (owner, 16/09; reproduced on the 0.1.3 engine).
        The shell's `stop` sets the reading's id to nothing before it is
        sent, so a reading it never hears of is one it never wanted.
        """
        kept: list[dict] = []
        for request in self._deferred:
            if request.get("method") not in methods:
                kept.append(request)
            elif request.get("method") == "model.prepare":
                self._reply(request.get("id"), {"ready": False, "cancelled": True})
            else:
                self._reply(request.get("id"), {
                    "frames": 0, "voiced_frames": 0, "stopped": True,
                })
        dropped = len(kept) < len(self._deferred)
        self._deferred = kept
        return dropped

    def _cancel_requested(self) -> bool:
        """Poll for a cancel while a download runs; answer the quick, defer
        the rest - `_stop_requested` for the download's own signal. A stop
        seen here has done its work in `_absorb` (the readings queued behind
        the download are answered) and does not end the download: Dừng is
        for the voice, Huỷ tải for the download, and they used to be one
        word."""
        while not self._requests.empty():
            self._absorb(self._requests.get())
        self._stop_pending = False
        if self._cancel_pending:
            self._cancel_pending = False
            return True
        return False

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
                catalogue, unreachable, pending = self._voice_catalogue()
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
                    # Providers still being asked in the background. The
                    # `voices` event says when the answer is in.
                    "pending": pending,
                })
            elif method == "read":
                self._read(request_id, request.get("params") or {})
            elif method == "text.parts":
                self._text_parts(request_id, request.get("params") or {})
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
                self._model_prepare(request_id, request.get("params") or {})
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
            elif method == "book.set_language":
                self._book_set_language(request_id, request.get("params") or {})
            elif method == "book.open":
                self._book_open(request_id, request.get("params") or {})
            elif method == "book.cover":
                self._book_cover(request_id, request.get("params") or {})
            elif method == "book.figure":
                self._book_figure(request_id, request.get("params") or {})
            elif method == "stop":
                # Nothing is playing; saying so beats silence.
                self._reply(request_id, {"stopped": False})
            elif method == "model.cancel":
                # Nothing is downloading; same answer for the same reason.
                self._reply(request_id, {"cancelled": False})
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
        # The passage itself is the evidence, exactly as a book's text is:
        # the language decides how the text is cut into utterances and
        # what the shell's hint says, and reading it off the interface
        # setting got the commonest case wrong - a Vietnamese interface and
        # an English paragraph pasted out of a browser.
        language = language_of_text(text, self._reading_language())
        utterances = _text_utterances(text, settings, language)
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
            window=params.get("window"), language=language,
            # The shell's word that this is the APP's own fixed sentence -
            # the voice-preview sample - and not something the reader wrote
            # or captured. It is what makes the clip cacheable; see `_speak`.
            app_text=bool(params.get("app_text")),
        )

    def _text_parts(self, request_id: Any, params: dict[str, Any]) -> None:
        """The same parts a `read` of this text would speak, as WRITTEN.

        The shell already receives a `position` event per part - it just had
        nothing to point those ids at, so a scanned passage could be heard
        but never followed. This is that missing half, and it comes from the
        SAME builder the reading uses: re-splitting in the shell would make
        two rules for one id, and the day they disagreed the marker would
        land on the wrong paragraph with nothing to say so.
        """

        text = str(params.get("text") or "")
        utterances = _text_utterances(text, SynthesisSettings())
        self._reply(request_id, {
            "parts": [
                {"segment_id": utterance.segment_id, "text": utterance.source}
                for utterance in utterances
            ],
        })

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
        language = self._book_language(stored)
        utterances, chapter_of = self._book_utterances(stored, language)
        start = _start_at(utterances, wanted, _reading_order(stored.book))
        # How far this press of the button is allowed to reach. `None` is the
        # whole book, which is what every reading did before paid voices
        # existed and is still the default.
        chapters = params.get("chapters")
        end = scope_end(chapter_of, start, None if chapters is None else int(chapters))
        self._speak(
            request_id, utterances[start:end], voice_id, rate, SynthesisSettings(),
            book_id=book_id, window=params.get("window"), language=language,
        )

    def _voice_catalogue(self) -> list[dict[str, Any]]:
        """Every voice on offer: the local model first, then paid ones.

        A provider's voices appear ONLY once its key is on this machine.
        Offering a voice that cannot speak would put the refusal after the
        choice instead of before it - the person would pick Alloy, press
        read, and be told no. The local model comes first because it is the
        product; the paid ones are an option somebody went and enabled.
        """

        # The local voices are Vietnamese and only Vietnamese - not "did not
        # say" like a provider that never published a list. Naming it here is
        # what lets the shell say which voices were made for the language in
        # front of the reader. Listed only while the model is on this Mac:
        # with no model and no remembered list, `voices()` loads the SDK,
        # which is the one call that cannot succeed - and it took the whole
        # listing down with it, the English voices included, for a reader
        # who chose to download only those.
        catalogue: list[dict[str, Any]] = [
            {
                "id": voice.id,
                "label": voice.label,
                "paid": False,
                "languages": [DEFAULT_SPEECH_LANGUAGE],
            }
            for voice in (self._engine.voices() if _is_ready(self._engine) else ())
        ]
        english = self._english_engine
        if english is not None and english.is_model_ready:
            # Listed only once it is on this Mac - before that, the settings
            # panel offers the download, and the voices panel says so.
            catalogue.extend(
                {
                    "id": voice.id,
                    "label": voice.label,
                    "paid": False,
                    "languages": [ENGLISH],
                    **({"gender": gender} if (gender := english.gender_of(voice.id)) else {}),
                }
                for voice in english.voices()
            )
        unreachable: list[dict[str, Any]] = []
        pending: list[str] = []
        settings = self._settings_document()
        for provider in sorted(KEY_FOR_PROVIDER):
            key = settings.get(KEY_FOR_PROVIDER[provider])
            if not key:
                continue
            model = chosen_model(provider, settings)
            offered, code = self._catalogue_of(provider, model, str(key), settings)
            if code == _PENDING:
                # Being asked right now, in the background. Not waiting is
                # the point: the listing answers with what it has, and the
                # `voices` event brings the rest.
                pending.append(provider)
                continue
            if offered is None:
                # ElevenLabs' catalogue is a NETWORK call, unlike OpenAI's
                # constant. Letting it out of here took the whole catalogue
                # with it - including the local voices, which need nothing
                # and were working. The provider drops out and says why; the
                # reader keeps the voices that were never in question.
                unreachable.append({"provider": provider, "code": code})
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
        return catalogue, unreachable, pending

    def _catalogue_of(
        self, provider: str, model: str, key: str, settings: dict
    ) -> tuple[tuple[Any, ...] | None, str | None]:
        """One provider's offer: remembered, being fetched, or fetched now.

        Fetched NOW only when nobody else is fetching it - the request loop
        never waits on the background thread, it either has the answer or
        says the answer is pending.
        """
        cache_key = _catalogue_key(provider, model, key)
        with self._catalogue_lock:
            remembered = self._catalogues.get(cache_key)
            if cache_key in self._catalogue_fetching:
                return None, _PENDING
            if remembered is not None:
                offered, code, asked_at = remembered
                if offered is not None or time.monotonic() - asked_at < _FAILURE_MEMORY:
                    return offered, code
                # A refusal whose memory has lapsed is asked again - in the
                # background. On a network that swallows packets the ask is
                # a 60 s timeout, and the request loop must never carry
                # that: everything behind it (the shelf, a book opening)
                # would wait too. The listing says what it last knew.
                self._catalogue_fetching.add(cache_key)
                threading.Thread(
                    target=self._refetch_catalogue,
                    args=(cache_key, provider, model, settings),
                    name="voices-refetch", daemon=True,
                ).start()
                return None, _PENDING
            self._catalogue_fetching.add(cache_key)
        try:
            return self._fetch_catalogue(cache_key, provider, model, settings)
        finally:
            with self._catalogue_lock:
                self._catalogue_fetching.discard(cache_key)

    def _refetch_catalogue(
        self, cache_key: tuple[str, str, str], provider: str, model: str, settings: dict
    ) -> None:
        try:
            self._fetch_catalogue(cache_key, provider, model, settings)
        except Exception:
            pass
        finally:
            with self._catalogue_lock:
                self._catalogue_fetching.discard(cache_key)
        self._send({"event": "voices", "providers": [provider]})

    def _fetch_catalogue(
        self, cache_key: tuple[str, str, str], provider: str, model: str, settings: dict
    ) -> tuple[tuple[Any, ...] | None, str | None]:
        external = _external_provider(provider, f"{provider}:{model}:x", settings)
        if external is None:
            return None, "no_key"
        try:
            offered: tuple[Any, ...] | None = tuple(external.voices())
            code: str | None = None
        except ExternalVoiceError as error:
            offered, code = None, error.code
        with self._catalogue_lock:
            self._catalogues[cache_key] = (offered, code, time.monotonic())
        return offered, code

    def _remember_catalogue(
        self, provider: str, model: str, key: str, offered: tuple[Any, ...]
    ) -> None:
        with self._catalogue_lock:
            self._catalogues[_catalogue_key(provider, model, key)] = (
                tuple(offered), None, time.monotonic()
            )

    def _prefetch_catalogues(self) -> None:
        """Ask every keyed provider once, off the request thread, and say
        so when done - the shell lists again on the `voices` event."""
        settings = self._settings_document()
        asked: list[str] = []
        for provider in sorted(KEY_FOR_PROVIDER):
            key = settings.get(KEY_FOR_PROVIDER[provider])
            if not key:
                continue
            model = chosen_model(provider, settings)
            cache_key = _catalogue_key(provider, model, str(key))
            with self._catalogue_lock:
                if cache_key in self._catalogues or cache_key in self._catalogue_fetching:
                    continue
                self._catalogue_fetching.add(cache_key)
            try:
                self._fetch_catalogue(cache_key, provider, model, settings)
            except Exception:
                # A provider module that throws something other than its own
                # error must not kill the thread silently: the entry stays
                # absent, and the next listing asks in the open.
                pass
            finally:
                with self._catalogue_lock:
                    self._catalogue_fetching.discard(cache_key)
            asked.append(provider)
        if asked:
            self._send({"event": "voices", "providers": asked})

    def _estimate(self, request_id: Any, params: dict[str, Any]) -> None:
        """What one press of the read button would cost, before it is pressed.

        Exact, not indicative: a paid voice bills by the character and the
        whole book is already on this machine, so this is arithmetic over the
        very strings `_speak` will send. Nothing is requested from anybody to
        answer it, and a local voice costs nothing to say so.
        """

        voice_id = str(params.get("voice_id") or "")
        price = price_for(model_of(voice_id) or "")
        if price is None and provider_of(voice_id) is not None:
            # A paid voice whose model this build cannot price. Answering
            # "paid: False" here would put a FREE-looking button in front of
            # a reading that bills - the exact thing the figure in the button
            # exists to prevent. `_speak` refuses the same id by name; this
            # is the half that keeps the button from inviting it.
            self._fail(request_id, "voice_unavailable: unknown_model")
            return

        # Pasted text is priced too, and it is the case that most needed it:
        # a paste can be 100,000 characters, which is one press of a button
        # and ten dollars on the dearer voices. There are no chapters in it,
        # so there is no scope to apply - the whole of what was pasted is
        # what gets read.
        if not params.get("book_id"):
            pasted = str(params.get("text") or "")
            # Named in the reply: the passage is judged by its own words
            # at every read, and this is the one answer the paste screen
            # gets before the read - what the shell's language hint stands
            # on.
            language = language_of_text(pasted, self._reading_language())
            utterances = _text_utterances(pasted, SynthesisSettings(), language)
            chars = sum(len(utterance.text) for utterance in utterances)
            if price is None:
                self._reply(request_id, {
                    "paid": False, "chars": chars,
                    "utterances": len(utterances), "chapters": 0,
                    "language": language,
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
                "language": language,
                "usd": round(price.usd_for(chars), 4),
                "units": price.units_for(chars),
                "unit": price.unit,
                "billing": price.billing,
                "price_dated": price.fetched,
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
        language = self._book_language(stored)
        utterances, chapter_of = self._book_utterances(stored, language)
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
                "language": language,
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
            "language": language,
            "usd": result.usd,
            "units": result.units,
            "unit": result.unit,
            "billing": result.billing,
            "price_dated": result.price_dated,
            # What this session has already run up. It rides here rather than
            # on an event of its own because the Rust host forwards only the
            # events it knows about, and the button re-prices whenever
            # anything changes - which is often enough for a figure that
            # lives one press away, behind the settings button.
            "spent_usd": self._spend.snapshot().usd,
        })

    def _book_utterances(
        self, stored: StoredBook, language: str = DEFAULT_SPEECH_LANGUAGE
    ) -> tuple[list[_Utterance], list[int]]:
        """Everything this book would say, and the chapter each bit is in.

        ONE builder, two callers: the reading, and the estimate the button
        shows before the reading is paid for. Built separately they would
        drift - the button would be counting characters the engine never
        sends, or missing ones it does - and the difference between those two
        numbers is the difference between a price and a guess.
        """

        language = speech_language(language)
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
        cues: dict[str, list[_FigureCue]] = {}
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
        # Figures whose caption does the announcing: the caption's first
        # utterance carries the figure, so the picture still comes into view
        # as the ear reaches it, and the voice does not say "Xem hình 1"
        # right before reading "Hình 1.1. …" (owner, 05/09: three
        # announcements for one picture).
        captioned: dict[str, str] = {
            cue.caption_segment_id: cue.figure_id
            for here in cues.values()
            for cue in here
            if cue.caption_segment_id is not None
        }

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
            for cue in here:
                if cue.placement == "before" and cue.caption_segment_id is None:
                    add(_Utterance(
                        text=FIGURE_CUE[language].format(number=cue.number),
                        pause_after_ms=FIGURE_CUE_PAUSE_MS,
                        segment_id=segment.id,
                        figure_id=cue.figure_id,
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
                    NOTE_CUE[language].format(
                        text=speakable_text(piece, language=language)
                    )
                    if is_note
                    else speakable_text(piece, segment.kind, language)
                )
                add(_Utterance(
                    text=spoken,
                    pause_after_ms=(
                        after_segment
                        if last
                        else NOTE_CUE_PAUSE_MS if is_note else SENTENCE_PAUSE_MS
                    ),
                    segment_id=segment.id,
                    figure_id=captioned.get(segment.id) if order == 0 else None,
                ), chapter)
            for cue in here:
                if cue.placement == "after" and cue.caption_segment_id is None:
                    add(_Utterance(
                        text=FIGURE_CUE[language].format(number=cue.number),
                        pause_after_ms=FIGURE_CUE_PAUSE_MS,
                        segment_id=segment.id,
                        figure_id=cue.figure_id,
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
        for stored in self._repository.list_shelf():
            if isinstance(stored, DamagedBook):
                # A row this build cannot decode keeps its place on the
                # shelf, marked, with the two ways out (remove, re-import)
                # still open. Skipped, it would be a ghost: gone from the
                # shelf, yet refusing the same file at import.
                try:
                    size_bytes = (
                        stored.managed_path.stat().st_size
                        if stored.managed_path is not None else None
                    )
                except OSError:
                    size_bytes = None
                books.append({
                    "id": stored.id,
                    "title": stored.title,
                    "source_format": stored.source_format,
                    "segment_id": None,
                    "progress_ratio": None,
                    "progress_chapter": None,
                    "chapters": 0,
                    "size_bytes": size_bytes,
                    "imported_at": self._repository.imported_at(stored.id),
                    "from_apple_books": stored.id in paired,
                    "damaged": True,
                })
                continue
            try:
                progress = self._repository.load_progress(stored.book.id)
            except RepositoryCorruptionError:
                # One book's unreadable position must not take the shelf down
                # with it. The Qt shell kept listing the book and simply did
                # not restore its place; this path answered "thư viện hỏng"
                # for the WHOLE library instead, and the only way back was
                # editing SQLite by hand. A book with no readable position is
                # a state the shelf already renders - it is a book nobody has
                # started.
                progress = None
            chosen_language = self._repository.book_language(stored.book.id)
            detected_language = self._detected_language(stored)
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
                "damaged": False,
                # Which language this book gets read in, and whether that was
                # a reader's decision or the detector's. Both, because "đã
                # đặt" is what the shell needs to offer an undo - and because
                # a shelf that only showed the answer would leave somebody
                # wondering whether it can be changed at all.
                # One question to the database per book, not two. Asking for
                # the language and then asking AGAIN whether it was set read
                # the same row twice on every shelf open; the detector only
                # ever ran once, so this is the query, not the reading.
                "language": language_in_use(chosen_language, detected_language),
                "language_set": chosen_language is not None,
                # What the TEXT says, whatever the reader decided. The shell
                # needs both to offer a suggestion rather than an argument:
                # a book set to Vietnamese whose words read as English is
                # somebody who may have chosen by mistake, and a book where
                # the two agree has nothing to suggest.
                "language_detected": detected_language,
            })
        self._reply(request_id, {"books": books})

    def _model_prepare(self, request_id: Any, params: dict[str, Any]) -> None:
        """Download whatever the active build still needs, streaming progress.

        Long and blocking by design: the pipe answers nothing else while a
        download runs, exactly like the Qt setup screen gated the app.
        `engine: "english"` asks for the English model instead.
        """
        if params.get("engine") == "english":
            if self._english_engine is None:
                self._fail(request_id, "no English model on this server")
                return
            prepare = self._english_engine.prepare_model
        else:
            prepare = getattr(self._engine, "prepare_model", None)
        if prepare is None:
            self._fail(request_id, "engine cannot prepare models")
            return

        def report(progress: float, message: str) -> None:
            # The progress callback is also the cancel point - the same place
            # the Qt setup screen used, for the same reason: it is the only
            # moment a long download hands control back. 453MB with no way out
            # is not a download, it is a hostage situation.
            if self._cancel_requested():
                raise _PreparationCancelled()
            self._send({
                "id": request_id,
                "event": "model_progress",
                "progress": float(progress),
                "message": str(message),
            })

        # A cancel from before this download began was answered by dropping
        # the queued request; one that reaches here is for this download.
        self._cancel_pending = False
        self._downloading = True
        try:
            prepare(report)
        except _PreparationCancelled:
            self._reply(request_id, {"ready": False, "cancelled": True})
            return
        finally:
            self._downloading = False
        self._reply(request_id, {"ready": True})
        # A model's voices just became listable - six English ones, or the
        # Vietnamese twenty on a Mac that chose the English model first. The
        # shell lists at start-up and on this event, so without it they
        # would wait for the next launch - the same signal a paid catalogue
        # arriving sends.
        self._send({"event": "voices", "providers": ["local"]})

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
        if params.get("engine") == "english":
            if self._english_engine is None:
                self._fail(request_id, "no English model on this server")
                return
            removed = bool(self._english_engine.remove())
            self._reply(request_id, {"removed": removed})
            if removed:
                self._send({"event": "voices", "providers": ["local"]})
            return
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
        # The readable books only: a damaged row has no title worth
        # pairing on, and must not cost every other book its note sync.
        stored = tuple(
            item for item in self._repository.list_shelf()
            if isinstance(item, StoredBook)
        ) if self._repository else ()
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
        # The language the reader chose to read in, and the voice last
        # picked under each language (15/09, with the English voice): the
        # settings panel opens on that language and switching it brings
        # that language's voice back. `voice` stays the one in use.
        "reading_language",
        "voice_vi",
        "voice_en",
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
        # A voice chosen is a model about to be needed: start loading it
        # now, behind the reply, so the first sentence in it waits less -
        # or not at all, if the play button comes a few seconds later.
        if key == "voice":
            self._warm_later(self._local_engine_of(str(params.get("value") or "")))

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
            listed = external.verify()
        except ExternalVoiceError as error:
            # NOT saved. A key the service refuses is not a setting worth
            # keeping - it would sit there looking configured and fail again
            # at the worst moment.
            self._reply(request_id, {"saved": False, "ok": False, "code": error.code})
            return
        if listed is not None:
            # ElevenLabs' check IS a listing; the shell lists again right
            # after this reply and must not pay the network a second time.
            self._remember_catalogue(provider, model, value, tuple(listed))
        update_settings(self._settings_path, {key_name: value})
        self._reply(request_id, {"saved": True, "ok": True})

    def _model_status(self, request_id: Any) -> None:
        engine = self._engine

        def value_of(name, fallback):
            attribute = getattr(engine, name, fallback)
            return attribute() if callable(attribute) else attribute

        # The real engine exposes is_model_ready as a method and precision as
        # a property; fakes may do either. Both shapes are answers.
        ready = _is_ready(engine)
        precision = value_of("precision", None)
        builds = value_of("installed_builds", dict)
        status: dict[str, Any] = {
            "ready": bool(ready),
            "precision": precision,
            "installed": {str(key): int(value) for key, value in builds.items()},
        }
        english = self._english_engine
        if english is not None:
            status["english"] = {
                "ready": bool(english.is_model_ready),
                "installed": int(english.installed_size()),
                "download_bytes": ENGLISH_DOWNLOAD_BYTES,
            }
        self._reply(request_id, status)

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
        try:
            progress = self._repository.load_progress(book_id)
        except RepositoryCorruptionError:
            # Same reasoning as library.list: an unreadable position costs
            # this book its place, not the book. Refusing to open it would
            # leave a book visible on the shelf that nothing can open, and
            # the text itself is fine - it is the bookmark that is torn.
            progress = None
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
                        # The book's own label ("Hình 1.1") and the segment
                        # that captions the picture, when the book gave it
                        # one: the shell shows the book's label and does
                        # not repeat a caption that is already on the page.
                        "label": figure.label,
                        "caption_segment_id": figure.caption_segment_id,
                        # A translated copy of the picture before it: shown
                        # (a reader may want to compare), numbered with the
                        # original, never announced twice.
                        "duplicate_of": figure.duplicate_of,
                    }
                    for figure, number in _figure_numbers(chapter.figures)
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
                                # How this block attaches to the one before:
                                # a "split" is the tail of a paragraph the
                                # importer cut for the voice, and the page
                                # must not open a new paragraph there.
                                "joint": segment.joint,
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
        try:
            stored = self._repository.get_book(book_id)
        except RepositoryCorruptionError:
            # A damaged book is on the shelf with no cover to show; that is
            # the ordinary "none" answer, not an error the shelf must wear.
            self._reply(request_id, {"media_type": None, "data": None})
            return
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

    def _reading_language(self, settings: dict[str, Any] | None = None) -> str:
        """The language the VOICE reads in, when there is no book to ask.

        Pasted text and a selection captured from another app have no book
        behind them, so the interface language is the only thing this app has
        been told. A BOOK is asked directly - see `_book_language`.
        """

        document = self._settings_document() if settings is None else settings
        return speech_language(document.get("ui_language"))

    def _detected_language(self, stored: StoredBook) -> str:
        """What this book's own text says, ignoring anyone's opinion of it.

        Remembered per book for as long as this process lives. Measured on
        the owner's shelf (07/09): 2.34 ms a book, which is nothing once and
        half a second on a two-hundred-book shelf that is listed on every
        visit to the library. Keyed on the source hash as well as the id, so
        a book re-imported from a different file is read again rather than
        answered from what the old one said.
        """

        key = (stored.book.id, stored.book.source_hash)
        remembered = self._detected_languages.get(key)
        if remembered is not None:
            return remembered
        found = language_of_texts(
            (
                segment.text
                for chapter in stored.book.chapters
                for segment in chapter.segments
            ),
            self._reading_language(),
        )
        self._detected_languages[key] = found
        return found

    def _book_language(self, stored: StoredBook) -> str:
        """The language THIS book is written in.

        The book outranks the interface: a library holds books in more than
        one language, and the setting says which language the reader wants
        buttons in, not which language the chapter in front of them is in.
        Getting this from the book is what lets the shell suggest the right
        voice for the chapter to somebody whose interface is Vietnamese,
        and what cuts the text into utterances the way that language reads.

        A reader's word and the text's are weighed by `language_in_use`: the
        word fills the gap the text leaves - a Vietnamese book that lost its
        diacritics reads as English, so the reader says so and it is cut
        and suggested as Vietnamese - and does not overrule what the text
        proves. Until 12/09 the word won outright, and a book 29% Vietnamese
        by orthography, set to English by a tap, could be read by no voice at
        all: in those days the local one refused it as English, and there
        was no other.

        One door on purpose: `read.book`, the book half of `estimate` and the
        shelf all come to this rule, so the price, the reading and the
        listing can never disagree about which language a book is in.
        """

        chosen = None
        if self._repository is not None:
            chosen = self._repository.book_language(stored.book.id)
        return language_in_use(chosen, self._detected_language(stored))

    def _book_set_language(self, request_id: Any, params: dict[str, Any]) -> None:
        """A reader's word about one book's language; `null` withdraws it.

        Fail-closed on the language, like the config keys: an open string
        column reached over a pipe would put whatever arrived in front of the
        transforms that turn writing into words.
        """

        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        book_id = str(params.get("book_id") or "")
        stored = self._repository.get_book(book_id)
        if stored is None:
            self._fail(request_id, f"unknown book: {book_id}")
            return
        raw = params.get("language")
        if raw is not None and str(raw) not in SPEECH_LANGUAGES:
            self._fail(request_id, f"unknown language: {raw}")
            return
        chosen = None if raw is None else str(raw)
        if chosen is not None and chosen != DEFAULT_SPEECH_LANGUAGE:
            if self._detected_language(stored) == DEFAULT_SPEECH_LANGUAGE:
                # A word may fill the gap the text leaves; it may not deny
                # what the text proves. This is the tap that once left a
                # Vietnamese book unreadable by every voice (12/09). The
                # shell no longer offers it on such a book, and a pipe is
                # refused by name because it cannot be trusted to.
                self._fail(
                    request_id,
                    f"language_proven: the book's own words are "
                    f"{DEFAULT_SPEECH_LANGUAGE}, not {chosen}",
                )
                return
        self._repository.set_book_language(book_id, chosen)
        # What the book is in NOW, so the shell shows the answer rather than
        # asking for it again.
        self._reply(request_id, {
            "language": self._book_language(stored),
            "language_set": chosen is not None,
            "language_detected": self._detected_language(stored),
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
        self,
        voice_id: str,
        settings: dict[str, Any],
        language_hint: str | None = None,
    ) -> tuple[Any, "VoicePrice | None", str | None]:
        """The engine for this voice, its price, and why not if not.

        A paid voice that cannot be paid for is REFUSED by name rather than
        quietly answered by the local model: hearing a different voice than
        the one you picked, with no explanation, is worse than being told the
        key is missing.
        """

        price = price_for(model_of(voice_id) or "")
        self._spend.set_limit(self._budget(settings))
        language = language_hint or self._reading_language(settings)
        route = pick_voice_route(
            voice_id,
            keys=settings,
            would_exceed_budget=(
                price is not None and self._spend.snapshot().exhausted
            ),
        )
        if route.kind == "local":
            # Either local model reads whatever it is handed. Each was
            # trained for one language and sounds like it in the other -
            # and until 15/09 the engine refused the mismatch by name. The
            # owner's decision that day: no blocking, the voice is the
            # reader's to choose, and the shell SUGGESTS the language's
            # voice instead ("không cần có cơ chế chặn ... cho user tự do
            # chọn voice"). So the one refusal left here is a model that is
            # not on this Mac: a voice can be remembered by a book or by
            # settings from before its download was removed, and that is
            # refused by name, with the sentence saying where to get it.
            english = self._english_engine
            if english is not None and voice_id in ENGLISH_VOICE_IDS:
                if not english.is_model_ready:
                    return None, None, "model_missing"
                return english, None, None
            if not _is_ready(self._engine):
                return None, None, "model_missing"
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
        """Where this sentence's audio lives, or None if it must not be kept.

        The one door to the audio cache - both the lookup and the write go
        through it - so the rule about WHICH readings may use disk is stated
        once, here, and a later call site cannot forget it.

        Keyed on what the SOUND depends on: the sentence as it will be sent,
        the voice, and who is speaking it. `engine_version`/`model_revision`
        come off the engine, so a paid provider's audio can never be served
        for the local model or the other way round - they are different
        engines with different versions, which is what the key is for.
        """

        if self._audio_cache is None or not self._cache_reading:
            # Both directions, not just the write: a lookup touches the
            # entry's mtime for the LRU, which is a persistent mark left by
            # a reading that promised to leave none.
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
        language: str | None = None,
        app_text: bool = False,
    ) -> None:
        # Which engine speaks this - the local model, or a provider on the
        # reader's own key. Decided once, here, so the sentence loop below is
        # the same road for both.
        document = self._settings_document()
        engine, price, blocked = self._voice_engine(voice_id, document, language)
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
        # Only a reading OF A BOOK may leave audio on disk. Pasted text and
        # text read from a selection are transient - PRIVACY.md promises they
        # are "not added to the library or persistent audio cache", and a
        # person reading a selection out of their mail or their notes has not
        # asked this app to keep it. `book_id` is exactly the difference: the
        # library path passes one, `read` never does.
        #
        # `app_text` is the one other thing that may be kept, and it does not
        # touch that promise: the promise is about the READER'S text, and this
        # is the app's own fixed sample sentence, the same words for everyone.
        # Keeping it is what stops a paid voice being bought twice for the
        # same audition - comparing five AI voices cost five charges, and
        # listening to one of them again cost another. Deliberately a claim
        # about PROVENANCE rather than a "cache this" bit: a caller cannot ask
        # for the reader's words to be kept by setting a flag.
        self._cache_reading = book_id is not None or app_text
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
    background: bool = False,
    english_engine: "EnglishEngine | None" = None,
) -> None:
    """Answer requests until the reader closes.

    `background` starts the work that needs nobody to ask for it - warming
    the model, prefetching paid catalogues - which the app wants and a test
    does not."""
    session = _Session(
        reader, writer, engine,
        repository=repository, service=service, settings_path=settings_path,
        notes_deps=notes_deps, audio_cache=audio_cache,
        english_engine=english_engine,
    )
    if background:
        session.start_background_work()
    session.run()


def _self_test() -> int:
    """The parts of the English voice that only fail in the frozen binary.

    The venv suite imports everything happily; a module the bundle left out
    fails here and nowhere else. No model is needed: the tagger and the
    out-of-lexicon reader ship in the bundle, and the two together are the
    imports a packaged English reading depends on. One JSON line on stdout,
    exit 0 or 1, so the build script can gate on it.
    """
    from vieneu_reader.speech.english.fallback import Fallback
    from vieneu_reader.speech.english.tagger import tag

    try:
        tagged = tag("The quick brown fox reads.")
        phonemes = Fallback().phonemes("Kowalczyk")
    except Exception as error:  # noqa: BLE001 - the whole point is to report
        print(json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"}))
        return 1
    ok = bool(tagged) and all(tag_ for _, tag_, _ in tagged) and bool(phonemes)
    print(json.dumps({"ok": ok, "tags": [tag_ for _, tag_, _ in tagged], "fallback": phonemes}))
    return 0 if ok else 1


def main() -> int:
    from vieneu_reader.config import AppPaths, default_app_root
    from vieneu_reader.speech.kokoro import KokoroSpeechEngine
    from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore
    from vieneu_reader.speech.vieneu import VieNeuSpeechEngine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="exercise the frozen imports the English voice needs and exit",
    )
    arguments = parser.parse_args()
    if arguments.self_test:
        return _self_test()

    paths = AppPaths.create(arguments.data_root or default_app_root())
    quality = VoiceQualityPreferenceStore(paths.root / "settings.json")
    engine = VieNeuSpeechEngine(paths.models, precision=quality.load())
    english_engine = KokoroSpeechEngine(paths.models)
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
        background=True,
        english_engine=english_engine,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
