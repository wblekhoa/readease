"""Playback state machine independent from GUI and audio hardware."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Mapping, Protocol

from vieneu_reader.domain.models import AudioChunk, BookDocument, Segment
from vieneu_reader.domain.segmenter import normalize_paragraph, split_transient_text
from vieneu_reader.speech.cache import AudioCache, audio_cache_key
from vieneu_reader.speech.contracts import SpeechEngine, SynthesisSettings
from vieneu_reader.storage.repository import Progress


class PlaybackState(str, Enum):
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class PlaybackSnapshot:
    state: PlaybackState = PlaybackState.IDLE
    book_id: str | None = None
    segment_id: str | None = None
    is_selection: bool = False
    selection_part_index: int | None = None
    selection_part_count: int = 0
    rate: float = 1.0
    error: str | None = None
    generation: int = 0
    sequence: int = 0


class AudioOutput(Protocol):
    """Generation-aware sink; stop must unblock a backpressured older append."""

    def begin(
        self,
        generation: int,
        rate: float,
        on_drained: Callable[[], None],
    ) -> None: ...
    def append(self, generation: int, chunk: AudioChunk) -> None: ...
    def end(self, generation: int) -> None: ...
    def pause(self, generation: int) -> None: ...
    def resume(self, generation: int) -> None: ...
    def stop(self, generation: int) -> None: ...
    def set_rate(self, generation: int, rate: float) -> None: ...


class ProgressRepository(Protocol):
    def save_progress(self, progress: Progress) -> None: ...
    def save_preferences(self, preferences: Progress) -> None: ...


class TaskScheduler(Protocol):
    def submit(self, task: Callable[[], None]) -> None: ...


class ThreadScheduler:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vieneu-reader")

    def submit(self, task: Callable[[], None]) -> None:
        self._executor.submit(task)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class _CancelledPlayback(Exception):
    pass


class PlaybackCoordinator:
    def __init__(
        self,
        *,
        engine: SpeechEngine,
        cache: AudioCache,
        progress_repository: ProgressRepository,
        output: AudioOutput,
        scheduler: TaskScheduler | None = None,
    ):
        self._engine = engine
        self._cache = cache
        self._progress = progress_repository
        self._output = output
        self._scheduler = scheduler or ThreadScheduler()
        self._command_lock = RLock()
        self._lock = RLock()
        self._progress_lock = RLock()
        self._generation = 0
        self._sequence = 0
        self._book: BookDocument | None = None
        self._segments: tuple[Segment, ...] = ()
        self._index: int | None = None
        self._selection_parts: tuple[str, ...] = ()
        self._selection_index: int | None = None
        self._speech_text_by_segment: dict[str, str] = {}
        self._voice_id = "Adam"
        self._rate = 1.0
        self._settings = SynthesisSettings()
        self._snapshot = PlaybackSnapshot()
        self._listeners: list[Callable[[PlaybackSnapshot], None]] = []

    @property
    def snapshot(self) -> PlaybackSnapshot:
        with self._lock:
            return self._snapshot

    def add_listener(self, listener: Callable[[PlaybackSnapshot], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def _publish(
        self,
        state: PlaybackState,
        *,
        is_selection: bool = False,
        error: str | None = None,
        generation: int | None = None,
    ) -> None:
        with self._lock:
            if generation is not None and generation != self._generation:
                return
            self._sequence += 1
            segment_id = (
                self._segments[self._index].id
                if self._index is not None and self._index < len(self._segments)
                else None
            )
            self._snapshot = PlaybackSnapshot(
                state=state,
                book_id=self._book.id if self._book else None,
                segment_id=segment_id,
                is_selection=is_selection,
                selection_part_index=(
                    self._selection_index + 1
                    if is_selection and self._selection_index is not None
                    else None
                ),
                selection_part_count=(
                    len(self._selection_parts) if is_selection else 0
                ),
                rate=self._rate,
                error=error,
                generation=self._generation,
                sequence=self._sequence,
            )
            snapshot = self._snapshot
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(snapshot)

    def _invalidate_output(self) -> int:
        with self._lock:
            self._generation += 1
            token = self._generation
            self._selection_parts = ()
            self._selection_index = None
        self._engine.cancel()
        self._output.stop(token)
        with self._progress_lock:
            pass
        return token

    def _guard(self, token: int) -> None:
        with self._lock:
            if token != self._generation:
                raise _CancelledPlayback()

    def _call_output(self, token: int, operation: Callable[[], None]) -> None:
        """Guard both sides; the sink rejects a stale token during the call race."""

        self._guard(token)
        operation()
        self._guard(token)

    @contextmanager
    def _cache_commit_guard(self, token: int):
        with self._lock:
            if token != self._generation:
                raise _CancelledPlayback()
            yield

    def _write_progress(self, token: int, index: int) -> None:
        with self._progress_lock:
            self._guard(token)
            with self._lock:
                book = self._book
                segment = self._segments[index]
                rate = self._rate
                voice_id = self._voice_id
            if book is None:
                raise _CancelledPlayback()
            progress = Progress(
                book_id=book.id,
                segment_id=segment.id,
                playback_rate=rate,
                voice_id=voice_id,
            )
            self._progress.save_progress(progress)
            self._guard(token)

    @staticmethod
    def _location(book: BookDocument, segment_id: str) -> tuple[tuple[Segment, ...], int]:
        segments = tuple(
            segment for chapter in book.chapters for segment in chapter.segments
        )
        try:
            index = next(
                index for index, segment in enumerate(segments) if segment.id == segment_id
            )
        except StopIteration as error:
            raise ValueError("segment does not belong to book") from error
        return segments, index

    def activate_book(
        self,
        book: BookDocument,
        segment_id: str,
        voice_id: str,
        *,
        rate: float,
        speech_text_by_segment: Mapping[str, str] | None = None,
    ) -> None:
        """Replace navigation context without autoplaying or writing progress."""

        with self._command_lock:
            self._validate_rate(rate)
            segments, index = self._location(book, segment_id)
            token = self._invalidate_output()
            with self._lock:
                self._book = book
                self._segments = segments
                self._index = index
                self._voice_id = voice_id
                self._rate = rate
                self._speech_text_by_segment = self._validated_speech_projection(
                    segments,
                    speech_text_by_segment,
                )
            self._publish(PlaybackState.IDLE, generation=token)

    def save_position(
        self,
        book: BookDocument,
        segment_id: str,
        voice_id: str,
        *,
        rate: float,
    ) -> None:
        with self._command_lock:
            self._validate_rate(rate)
            segments, index = self._location(book, segment_id)
            with self._progress_lock:
                with self._lock:
                    self._book = book
                    self._segments = segments
                    self._index = index
                    self._voice_id = voice_id
                    self._rate = rate
                self._progress.save_progress(
                    Progress(book.id, segment_id, rate, voice_id)
                )

    def save_preferences(
        self,
        book: BookDocument,
        segment_id: str,
        voice_id: str,
        *,
        rate: float,
    ) -> None:
        with self._command_lock:
            self._validate_rate(rate)
            self._location(book, segment_id)
            with self._progress_lock:
                with self._lock:
                    if self._book is None or self._book.id == book.id:
                        self._voice_id = voice_id
                        self._rate = rate
                self._progress.save_preferences(
                    Progress(book.id, segment_id, rate, voice_id)
                )

    def play(
        self,
        book: BookDocument,
        segment_id: str,
        voice_id: str,
        *,
        rate: float = 1.0,
        settings: SynthesisSettings = SynthesisSettings(),
        speech_text_by_segment: Mapping[str, str] | None = None,
    ) -> None:
        with self._command_lock:
            segments, index = self._location(book, segment_id)
            self._validate_rate(rate)
            token = self._invalidate_output()
            with self._lock:
                self._book = book
                self._segments = segments
                self._index = index
                self._voice_id = voice_id
                self._rate = rate
                self._settings = settings
                self._speech_text_by_segment = self._validated_speech_projection(
                    segments,
                    speech_text_by_segment,
                )
            self._publish(PlaybackState.LOADING, generation=token)
            self._schedule_segment(token, index)

    def play_selection(
        self,
        text: str,
        voice_id: str,
        *,
        rate: float = 1.0,
        settings: SynthesisSettings = SynthesisSettings(),
    ) -> None:
        with self._command_lock:
            parts = split_transient_text(text, settings.max_chars)
            if not parts:
                raise ValueError("selection text cannot be empty")
            self._validate_rate(rate)
            token = self._invalidate_output()
            with self._lock:
                self._voice_id = voice_id
                self._rate = rate
                self._settings = settings
                self._selection_parts = parts
                self._selection_index = 0
            self._publish(
                PlaybackState.LOADING,
                is_selection=True,
                generation=token,
            )
            self._scheduler.submit(
                lambda: self._render_text(token, parts[0], 0, is_selection=True)
            )

    def _schedule_segment(self, token: int, index: int) -> None:
        with self._lock:
            if token != self._generation or not 0 <= index < len(self._segments):
                return
            segment = self._segments[index]
            text = self._speech_text_by_segment.get(segment.id, segment.text)
        self._scheduler.submit(
            lambda: self._render_text(token, text, index, is_selection=False)
        )

    def _render_text(
        self,
        token: int,
        text: str,
        index: int | None,
        *,
        is_selection: bool,
    ) -> None:
        try:
            self._guard(token)
            with self._lock:
                voice_id = self._voice_id
                rate = self._rate
                settings = self._settings
            key = None
            cached = None
            if not is_selection:
                key = audio_cache_key(
                    text,
                    voice_id,
                    self._engine.engine_version,
                    self._engine.model_revision,
                    settings,
                )
                cached = self._cache.get(key)
            self._guard(token)
            self._call_output(
                token,
                lambda: self._output.begin(
                    token,
                    rate,
                    lambda: self._on_drained(
                        token,
                        index,
                        is_selection=is_selection,
                    ),
                ),
            )
            if cached is not None:
                self._call_output(token, lambda: self._output.append(token, cached))
                self._publish(
                    PlaybackState.PLAYING,
                    is_selection=is_selection,
                    generation=token,
                )
            else:
                produced_chunks = 0
                synthesis_failed = False

                def generating_chunks():
                    nonlocal produced_chunks, synthesis_failed
                    try:
                        for chunk in self._engine.stream(text, voice_id, settings):
                            self._call_output(
                                token,
                                lambda: self._output.append(token, chunk),
                            )
                            # Count what the person can actually hear, so the
                            # guard below does not depend on the engine never
                            # handing back an empty chunk.
                            if chunk.pcm:
                                produced_chunks += 1
                                if produced_chunks == 1:
                                    self._publish(
                                        PlaybackState.PLAYING,
                                        is_selection=is_selection,
                                        generation=token,
                                    )
                            yield chunk
                    except _CancelledPlayback:
                        raise
                    except Exception:
                        synthesis_failed = True
                        raise

                if is_selection:
                    for _chunk in generating_chunks():
                        pass
                else:
                    if key is None:
                        raise RuntimeError("cache key is unavailable")
                    chunks = generating_chunks()
                    try:
                        self._cache.put_complete(
                            key,
                            chunks,
                            commit_guard=lambda: self._cache_commit_guard(token),
                        )
                    except _CancelledPlayback:
                        raise
                    except Exception:
                        if synthesis_failed:
                            raise
                        # The voice itself worked, so this paragraph is already
                        # reaching the person; only storing it for next time
                        # failed. Finish sending the audio and stay quiet about
                        # the cache, exactly as _prefetch does.
                        for _chunk in chunks:
                            pass
                if not produced_chunks:
                    # The engine finished without a single sample, so the person
                    # is sitting in silence. On either path that is the voice
                    # failing, and staying quiet would leave them with no way to
                    # tell whether the app is working, stuck or done.
                    raise RuntimeError("synthesis produced no audio")
            self._guard(token)
            self._call_output(token, lambda: self._output.end(token))
            if not is_selection and index is not None and index + 1 < len(self._segments):
                self._scheduler.submit(lambda: self._prefetch(token, index + 1))
        except _CancelledPlayback:
            return
        except Exception:
            try:
                self._call_output(token, lambda: self._output.stop(token))
            except _CancelledPlayback:
                return
            else:
                self._publish(
                    PlaybackState.ERROR,
                    is_selection=is_selection,
                    error="Không thể tạo giọng đọc cho đoạn này.",
                    generation=token,
                )

    def _prefetch(self, token: int, index: int) -> None:
        try:
            with self._lock:
                if token != self._generation or not 0 <= index < len(self._segments):
                    return
                voice_id = self._voice_id
                settings = self._settings
                segment = self._segments[index]
                text = self._speech_text_by_segment.get(segment.id, segment.text)
            key = audio_cache_key(
                text,
                voice_id,
                self._engine.engine_version,
                self._engine.model_revision,
                settings,
            )
            if self._cache.get(key) is not None:
                return

            def guarded_chunks():
                for chunk in self._engine.stream(text, voice_id, settings):
                    self._guard(token)
                    yield chunk

            self._cache.put_complete(
                key,
                guarded_chunks(),
                commit_guard=lambda: self._cache_commit_guard(token),
            )
        except Exception:
            return

    def _on_drained(
        self,
        token: int,
        index: int | None,
        *,
        is_selection: bool,
    ) -> None:
        with self._lock:
            if token != self._generation:
                return
            book = self._book
            segment_count = len(self._segments)
        if is_selection:
            with self._lock:
                if (
                    token != self._generation
                    or index is None
                    or index != self._selection_index
                ):
                    return
                next_index = index + 1
                if next_index >= len(self._selection_parts):
                    self._selection_parts = ()
                    self._selection_index = None
                    next_text = None
                else:
                    self._selection_index = next_index
                    next_text = self._selection_parts[next_index]
            if next_text is None:
                self._publish(PlaybackState.IDLE, generation=token)
                return
            self._publish(
                PlaybackState.LOADING,
                is_selection=True,
                generation=token,
            )
            self._scheduler.submit(
                lambda: self._render_text(
                    token,
                    next_text,
                    next_index,
                    is_selection=True,
                )
            )
            return
        if book is None or index is None:
            self._publish(PlaybackState.IDLE, generation=token)
            return
        next_index = index + 1
        saved_index = next_index if next_index < segment_count else index
        try:
            self._write_progress(token, saved_index)
        except _CancelledPlayback:
            return
        except Exception:
            self._publish(
                PlaybackState.ERROR,
                error="Không thể lưu vị trí đọc. Sách vẫn có thể mở lại.",
                generation=token,
            )
            return
        with self._lock:
            if (
                token != self._generation
                or self._book is None
                or self._book.id != book.id
            ):
                return
            at_end = next_index >= len(self._segments)
            if not at_end:
                self._index = next_index
        if at_end:
            self._publish(PlaybackState.IDLE, generation=token)
            return
        self._publish(PlaybackState.LOADING, generation=token)
        self._schedule_segment(token, next_index)

    def next(self) -> None:
        with self._command_lock:
            if self.snapshot.is_selection:
                return
            with self._lock:
                if self._index is None or self._index + 1 >= len(self._segments):
                    return
                target = self._index + 1
            token = self._invalidate_output()
            with self._lock:
                self._index = target
            if not self._save_navigation(target, token):
                return
            self._publish(PlaybackState.LOADING, generation=token)
            self._schedule_segment(token, target)

    def previous(self) -> None:
        with self._command_lock:
            if self.snapshot.is_selection:
                return
            with self._lock:
                if self._index is None or self._index == 0:
                    return
                target = self._index - 1
            token = self._invalidate_output()
            with self._lock:
                self._index = target
            if not self._save_navigation(target, token):
                return
            self._publish(PlaybackState.LOADING, generation=token)
            self._schedule_segment(token, target)

    def _save_navigation(self, index: int, token: int) -> bool:
        try:
            self._write_progress(token, index)
            return True
        except _CancelledPlayback:
            return False
        except Exception:
            self._publish(
                PlaybackState.ERROR,
                error="Không thể lưu vị trí đọc. Sách vẫn có thể mở lại.",
                generation=token,
            )
            return False

    def pause(self) -> None:
        with self._command_lock:
            snapshot = self.snapshot
            if snapshot.state is PlaybackState.PLAYING:
                token = snapshot.generation
                try:
                    self._call_output(token, lambda: self._output.pause(token))
                except _CancelledPlayback:
                    return
                self._publish(
                    PlaybackState.PAUSED,
                    is_selection=snapshot.is_selection,
                    generation=token,
                )

    def resume(self) -> None:
        with self._command_lock:
            snapshot = self.snapshot
            if snapshot.state is PlaybackState.PAUSED:
                token = snapshot.generation
                try:
                    self._call_output(token, lambda: self._output.resume(token))
                except _CancelledPlayback:
                    return
                self._publish(
                    PlaybackState.PLAYING,
                    is_selection=snapshot.is_selection,
                    generation=token,
                )

    def set_rate(self, rate: float) -> None:
        with self._command_lock:
            self._validate_rate(rate)
            with self._lock:
                self._rate = rate
                token = self._generation
                snapshot = self._snapshot
            try:
                self._call_output(token, lambda: self._output.set_rate(token, rate))
            except _CancelledPlayback:
                return
            self._publish(
                snapshot.state,
                is_selection=snapshot.is_selection,
                error=snapshot.error,
                generation=token,
            )

    @staticmethod
    def _validate_rate(rate: float) -> None:
        if not 0.5 <= rate <= 2.0:
            raise ValueError("playback rate must be between 0.5 and 2.0")

    @staticmethod
    def _validated_speech_projection(
        segments: tuple[Segment, ...],
        projection: Mapping[str, str] | None,
    ) -> dict[str, str]:
        if not projection:
            return {}
        segment_ids = {segment.id for segment in segments}
        validated: dict[str, str] = {}
        for segment_id, text in projection.items():
            normalized = normalize_paragraph(text)
            if segment_id not in segment_ids or not normalized:
                raise ValueError("speech projection does not belong to book")
            validated[segment_id] = normalized
        return validated

    def stop(self) -> None:
        with self._command_lock:
            token = self._invalidate_output()
            self._publish(PlaybackState.IDLE, generation=token)

    def close(self) -> None:
        self.stop()
        shutdown = getattr(self._scheduler, "shutdown", None)
        if shutdown is not None:
            shutdown()
