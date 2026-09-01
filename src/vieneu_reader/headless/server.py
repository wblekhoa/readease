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
                                            "rate": 1.0}}
    {"id": 4, "method": "stop"}

A read streams `{"id": 3, "event": "chunk", "seq": n, "from_voice": bool,
"pcm": <base64 float32 mono>, "sample_rate": 48000}` frames and finishes with
a normal reply. Silence between sentences is a frame like any other, so the
shell needs no prosody knowledge at all.
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
    speakable_text,
    split_sentences,
)
from vieneu_reader.domain.segmenter import split_transient_parts
from vieneu_reader.playback.time_stretch import SAMPLE_RATE, TimeStretcher
from vieneu_reader.speech.contracts import SynthesisSettings
from vieneu_reader.importers.errors import BookImportError
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.storage.repository import LibraryRepository, Progress

PROTOCOL_VERSION = 1

_EOF = object()


class ReadingEngine(Protocol):
    @property
    def engine_version(self) -> str: ...

    def voices(self) -> tuple[Voice, ...]: ...

    def stream(
        self, text: str, voice_id: str, settings: SynthesisSettings
    ) -> Iterator[AudioChunk]: ...


def _silence(milliseconds: int) -> bytes:
    samples = SAMPLE_RATE * milliseconds // 1000
    return np.zeros(samples, dtype=np.float32).tobytes()


@dataclass(frozen=True)
class _Utterance:
    """One thing to speak, the rest that follows it, and where it lives."""

    text: str
    pause_after_ms: int
    segment_id: str | None = None


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
    ):
        self._writer = writer
        self._engine = engine
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

    def _stop_requested(self) -> bool:
        """Poll for a stop while streaming; defer everything else.

        EOF is not a stop: closing stdin means "no more requests", and batch
        callers do exactly that - one read, close, collect the audio. The
        reading finishes; the loop exits afterwards.
        """
        while not self._requests.empty():
            item = self._requests.get()
            if item is _EOF:
                self._eof = True
                continue
            try:
                request = json.loads(item)
            except json.JSONDecodeError:
                self._send({"id": None, "ok": False, "error": "invalid json"})
                continue
            if request.get("method") == "stop":
                self._reply(request.get("id"), {"stopped": True})
                return True
            self._deferred.append(request)
        return False

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
                self._reply(request_id, {
                    "voices": [
                        {"id": voice.id, "label": voice.label}
                        for voice in self._engine.voices()
                    ],
                })
            elif method == "read":
                self._read(request_id, request.get("params") or {})
            elif method == "read.book":
                self._read_book(request_id, request.get("params") or {})
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
            elif method == "book.open":
                self._book_open(request_id, request.get("params") or {})
            elif method == "book.figure":
                self._book_figure(request_id, request.get("params") or {})
            elif method == "stop":
                # Nothing is playing; saying so beats silence.
                self._reply(request_id, {"stopped": False})
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
        parts = split_transient_parts(text, settings.max_chars)
        if not parts:
            self._fail(request_id, "text is empty")
            return
        spoken = tuple(speakable_text(part.text) for part in parts)
        utterances = [
            _Utterance(
                text=spoken[index],
                pause_after_ms=(
                    selection_pause_ms(spoken[index], parts[index + 1].joint)
                    if index + 1 < len(parts)
                    else 0
                ),
            )
            for index in range(len(parts))
        ]
        self._speak(request_id, utterances, voice_id, rate, settings)

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
        rate = float(params.get("rate") or 1.0)
        segments: list[Segment] = [
            segment
            for chapter in stored.book.chapters
            for segment in chapter.segments
        ]
        start = 0
        wanted = params.get("segment_id")
        if not wanted:
            progress = self._repository.load_progress(book_id)
            wanted = progress.segment_id if progress else None
        if wanted:
            for index, segment in enumerate(segments):
                if segment.id == wanted:
                    start = index
                    break
        utterances = [
            _Utterance(
                text=speakable_text(segment.text, segment.kind),
                pause_after_ms=pause_after_ms(
                    segment,
                    segments[index + 1] if index + 1 < len(segments) else None,
                ),
                segment_id=segment.id,
            )
            for index, segment in enumerate(segments)
        ][start:]
        self._speak(
            request_id, utterances, voice_id, rate, SynthesisSettings(),
            book_id=book_id,
        )

    def _library_list(self, request_id: Any) -> None:
        if self._repository is None:
            self._fail(request_id, "no library on this server")
            return
        books = []
        for stored in self._repository.list_books():
            progress = self._repository.load_progress(stored.book.id)
            try:
                size_bytes = stored.managed_path.stat().st_size
            except OSError:
                size_bytes = None
            books.append({
                "id": stored.book.id,
                "title": stored.book.title,
                "source_format": stored.book.source_format,
                "segment_id": progress.segment_id if progress else None,
                # What tells two same-titled copies apart: shape, size, and
                # when each one arrived.
                "chapters": len(stored.book.chapters),
                "size_bytes": size_bytes,
                "imported_at": self._repository.imported_at(stored.book.id),
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
            self._send({
                "id": request_id,
                "event": "model_progress",
                "progress": float(progress),
                "message": str(message),
            })

        prepare(report)
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

    _CONFIG_KEYS = frozenset({"tauri_selection_shortcut", "ui_language"})

    def _config_get(self, request_id: Any, params: dict[str, Any]) -> None:
        from vieneu_reader.settings import load_settings

        key = str(params.get("key") or "")
        if key not in self._CONFIG_KEYS or self._settings_path is None:
            self._fail(request_id, f"unknown config key: {key}")
            return
        value = load_settings(self._settings_path).get(key)
        self._reply(request_id, {"value": value})

    def _config_set(self, request_id: Any, params: dict[str, Any]) -> None:
        from vieneu_reader.settings import update_settings

        key = str(params.get("key") or "")
        if key not in self._CONFIG_KEYS or self._settings_path is None:
            self._fail(request_id, f"unknown config key: {key}")
            return
        update_settings(self._settings_path, {key: params.get("value")})
        self._reply(request_id, {"saved": True})

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
                    }
                    for figure in chapter.figures
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
            "progress": {
                "segment_id": progress.segment_id if progress else None,
                "rate": progress.playback_rate if progress else 1.0,
                "voice_id": progress.voice_id if progress else None,
            },
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
        data = assets.get(figure_id)
        if not data:
            self._fail(request_id, f"figure unavailable: {figure_id}")
            return
        self._reply(request_id, {
            "media_type": wanted.media_type,
            "data": base64.b64encode(data).decode("ascii"),
        })

    def _speak(
        self,
        request_id: Any,
        utterances: list[_Utterance],
        voice_id: str,
        rate: float,
        settings: SynthesisSettings,
        *,
        book_id: str | None = None,
    ) -> None:
        # Rate rides the same stretcher as the Qt app, so a 1.5× reading
        # sounds identical over the pipe. Rests are pure zeros: scaling
        # their length arithmetically is exact, so they skip the stretcher.
        stretcher = TimeStretcher(rate) if rate != 1.0 else None
        seq = 0
        voiced = 0
        stopped = False

        def emit(pcm: bytes, *, from_voice: bool) -> None:
            nonlocal seq, voiced
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
                    self._send({
                        "id": request_id,
                        "event": "position",
                        "segment_id": utterance.segment_id,
                    })
                    if book_id is not None and self._repository is not None:
                        # Progress follows the voice, exactly like the Qt
                        # coordinator: reopening lands where reading stopped.
                        self._repository.save_progress(Progress(
                            book_id=book_id,
                            segment_id=utterance.segment_id,
                            playback_rate=rate,
                            voice_id=voice_id,
                        ))
                sentences = split_sentences(utterance.text)
                if not sentences and utterance.text.strip():
                    sentences = (utterance.text,)
                for index, sentence in enumerate(sentences):
                    if index:
                        emit(_silence(int(SENTENCE_PAUSE_MS / rate)),
                             from_voice=False)
                    for chunk in self._engine.stream(
                        sentence, voice_id, settings
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
        except Exception as error:  # noqa: BLE001 - the pipe must survive
            self._fail(request_id, f"read failed: {error}")
            return
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
) -> None:
    """Answer requests until the reader closes."""
    _Session(
        reader, writer, engine,
        repository=repository, service=service, settings_path=settings_path,
        notes_deps=notes_deps,
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

    # The SDK prints progress to stdout; the protocol channel must stay clean.
    protocol = sys.stdout
    sys.stdout = sys.stderr
    serve(
        sys.stdin, protocol, engine,
        repository=repository, service=service,
        settings_path=paths.root / "settings.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
