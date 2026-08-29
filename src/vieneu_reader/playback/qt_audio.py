"""Thread-safe, generation-aware Qt pull audio output."""

from __future__ import annotations

from collections.abc import Callable
from threading import Condition, RLock
from typing import Any

import numpy as np
from PySide6.QtCore import QIODevice, QObject, Signal, Slot
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QtAudio

from vieneu_reader.domain.models import AudioChunk

from .time_stretch import SAMPLE_RATE, TimeStretcher


def _to_bytes(samples: np.ndarray) -> bytes:
    if samples.size == 0:
        return b""
    return np.clip(samples, -1.0, 1.0).astype("<f4").tobytes()


class _BoundedAudioDevice(QIODevice):
    sourceDrained = Signal(int)

    def __init__(self, generation: int, capacity_bytes: int, rate: float = 1.0):
        super().__init__()
        if capacity_bytes < 4:
            raise ValueError("audio buffer capacity must be at least four bytes")
        self._generation = generation
        self._capacity = capacity_bytes
        self._payload = bytearray()
        # Speed is applied here, on the way out, not on the way in: whatever is
        # still queued has not been committed to a speed yet, so changing it is
        # heard at once rather than after the queue drains.
        self._stretcher = TimeStretcher()
        self._ready = bytearray()
        self._drained_tail = False
        self._finished = False
        self._condition = Condition(RLock())
        self.open(QIODevice.OpenModeFlag.ReadOnly)

    def isSequential(self) -> bool:  # noqa: N802 - Qt virtual method
        return True

    def set_rate(self, rate: float) -> None:
        with self._condition:
            self._stretcher.set_rate(rate)

    def bytesAvailable(self) -> int:  # noqa: N802 - Qt virtual method
        with self._condition:
            return len(self._ready) + len(self._payload) + super().bytesAvailable()

    def atEnd(self) -> bool:  # noqa: N802 - Qt virtual method
        with self._condition:
            return self._finished and not self._payload and not self._ready

    def _fill_ready(self, wanted: int) -> None:
        """Stretch queued audio until enough is ready, or the queue is empty."""

        while len(self._ready) < wanted and self._payload:
            # Whole samples only: half a float32 is not a number.
            take = min(len(self._payload) - len(self._payload) % 4, 64 * 1024)
            if take <= 0:
                break
            block = np.frombuffer(bytes(self._payload[:take]), dtype="<f4")
            del self._payload[:take]
            self._condition.notify_all()
            self._ready.extend(_to_bytes(self._stretcher.feed(block)))
        if (
            len(self._ready) < wanted
            and self._finished
            and not self._payload
            and not self._drained_tail
        ):
            self._drained_tail = True
            self._ready.extend(_to_bytes(self._stretcher.drain()))

    def readData(self, max_length: int) -> bytes:  # noqa: N802 - Qt virtual method
        with self._condition:
            wanted = max(max_length, 0)
            self._fill_ready(wanted)
            count = min(wanted, len(self._ready))
            data = bytes(self._ready[:count])
            if count:
                del self._ready[:count]
                self._condition.notify_all()
            drained = self._finished and not self._payload and not self._ready
            generation = self._generation
        if drained:
            self.sourceDrained.emit(generation)
        return data

    def append(self, generation: int, payload: bytes) -> bool:
        offset = 0
        while offset < len(payload):
            with self._condition:
                while (
                    generation == self._generation
                    and len(self._payload) >= self._capacity
                ):
                    self._condition.wait()
                if generation != self._generation or self._finished:
                    return False
                available = self._capacity - len(self._payload)
                count = min(available, len(payload) - offset)
                self._payload.extend(payload[offset : offset + count])
                offset += count
            self.readyRead.emit()
        return True

    def finish(self, generation: int) -> None:
        with self._condition:
            if generation != self._generation:
                return
            self._finished = True
            drained = not self._payload and not self._ready
            self._condition.notify_all()
        if drained:
            self.sourceDrained.emit(generation)

    def cancel(self, next_generation: int) -> None:
        with self._condition:
            self._generation = next_generation
            self._finished = True
            self._payload.clear()
            self._ready.clear()
            self._drained_tail = False
            self._stretcher.reset(self._stretcher.rate)
            self._condition.notify_all()

    def finished_and_empty(self, generation: int) -> bool:
        with self._condition:
            return (
                generation == self._generation
                and self._finished
                and not self._payload
                and not self._ready
            )


class QtAudioOutput(QObject):
    """AudioOutput implementation safe for coordinator worker calls."""

    _beginRequested = Signal(int, float, object)
    _stopRequested = Signal(int)
    _pauseRequested = Signal(int)
    _resumeRequested = Signal(int)

    def __init__(
        self,
        *,
        sink_factory: Callable[[QAudioFormat], Any] | None = None,
        capacity_bytes: int = 4 * 1024 * 1024,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._capacity_bytes = capacity_bytes
        self._sink_factory = sink_factory or (
            lambda audio_format: QAudioSink(audio_format, self)
        )
        self._lock = RLock()
        self._generation = 0
        self._rate = 1.0
        self._paused = False
        self._buffer: _BoundedAudioDevice | None = None
        self._sink: Any | None = None
        self._on_drained: Callable[[], None] | None = None

        self._beginRequested.connect(self._begin_on_qt)
        self._stopRequested.connect(self._stop_on_qt)
        self._pauseRequested.connect(self._pause_on_qt)
        self._resumeRequested.connect(self._resume_on_qt)

    @staticmethod
    def _format() -> QAudioFormat:
        # Fixed: speed is a change to the samples now, not to how fast the
        # device consumes them. That is what keeps the pitch where it was, and
        # it means a speed change no longer restarts the audio device.
        audio_format = QAudioFormat()
        audio_format.setSampleRate(SAMPLE_RATE)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Float)
        return audio_format

    def begin(
        self,
        generation: int,
        rate: float,
        on_drained: Callable[[], None],
    ) -> None:
        if not 0.5 <= rate <= 2.0:
            raise ValueError("playback rate must be between 0.5 and 2.0")
        buffer = _BoundedAudioDevice(generation, self._capacity_bytes, rate)
        buffer.set_rate(rate)
        buffer.moveToThread(self.thread())
        buffer.sourceDrained.connect(self._source_drained)
        with self._lock:
            if generation != self._generation:
                buffer.cancel(self._generation)
                buffer.deleteLater()
                return
            previous = self._buffer
            self._buffer = buffer
            self._rate = rate
            self._paused = False
            self._on_drained = on_drained
        if previous is not None:
            previous.cancel(generation)
        self._beginRequested.emit(generation, rate, buffer)

    def append(self, generation: int, chunk: AudioChunk) -> None:
        with self._lock:
            if generation != self._generation:
                return
            buffer = self._buffer
        if buffer is None:
            return
        if chunk.sample_rate != 48_000 or chunk.channels != 1:
            raise ValueError("Qt audio requires mono 48 kHz input")
        if chunk.sample_format != "float32" or len(chunk.pcm) % 4:
            raise ValueError("Qt audio requires complete float32 samples")
        buffer.append(generation, chunk.pcm)

    def end(self, generation: int) -> None:
        with self._lock:
            buffer = self._buffer if generation == self._generation else None
        if buffer is not None:
            buffer.finish(generation)

    def pause(self, generation: int) -> None:
        with self._lock:
            current = generation == self._generation
            if current:
                self._paused = True
        if current:
            self._pauseRequested.emit(generation)

    def resume(self, generation: int) -> None:
        with self._lock:
            current = generation == self._generation
            if current:
                self._paused = False
        if current:
            self._resumeRequested.emit(generation)

    def stop(self, generation: int) -> None:
        with self._lock:
            if generation < self._generation:
                return
            self._generation = generation
            buffer = self._buffer
            self._buffer = None
            self._paused = False
            self._on_drained = None
        if buffer is not None:
            buffer.cancel(generation)
        self._stopRequested.emit(generation)

    def set_rate(self, generation: int, rate: float) -> None:
        if not 0.5 <= rate <= 2.0:
            raise ValueError("playback rate must be between 0.5 and 2.0")
        with self._lock:
            if generation != self._generation:
                return
            self._rate = rate
            buffer = self._buffer
        if buffer is not None:
            buffer.set_rate(rate)

    def _replace_sink(
        self,
        generation: int,
        buffer: _BoundedAudioDevice,
    ) -> None:
        with self._lock:
            if generation != self._generation or buffer is not self._buffer:
                return
            previous_sink = self._sink
            self._sink = None
        if previous_sink is not None:
            previous_sink.stop()
            previous_sink.deleteLater()
        sink = self._sink_factory(self._format())
        def state_changed() -> None:
            self._sink_state_changed(
                generation,
                buffer,
                sink,
            )

        sink.stateChanged.connect(state_changed)
        with self._lock:
            if generation != self._generation or buffer is not self._buffer:
                sink.stop()
                sink.deleteLater()
                return
            self._sink = sink
            paused = self._paused
        sink.start(buffer)
        if paused:
            sink.suspend()

    @Slot(int, float, object)
    def _begin_on_qt(
        self,
        generation: int,
        rate: float,
        buffer: _BoundedAudioDevice,
    ) -> None:
        self._replace_sink(generation, buffer)

    @Slot(int)
    def _stop_on_qt(self, generation: int) -> None:
        with self._lock:
            if generation != self._generation:
                return
            sink = self._sink
            self._sink = None
        if sink is not None:
            sink.stop()
            sink.deleteLater()

    @Slot(int)
    def _pause_on_qt(self, generation: int) -> None:
        with self._lock:
            sink = self._sink if generation == self._generation else None
        if sink is not None:
            sink.suspend()

    @Slot(int)
    def _resume_on_qt(self, generation: int) -> None:
        with self._lock:
            sink = self._sink if generation == self._generation else None
        if sink is not None:
            sink.resume()

    @Slot(int)
    def _source_drained(self, generation: int) -> None:
        self._maybe_publish_drained(generation)

    def _sink_state_changed(
        self,
        generation: int,
        buffer: _BoundedAudioDevice,
        sink: Any,
    ) -> None:
        with self._lock:
            if (
                generation != self._generation
                or buffer is not self._buffer
                or sink is not self._sink
            ):
                return
        if sink.state() is QtAudio.State.IdleState:
            self._maybe_publish_drained(generation)

    def _maybe_publish_drained(self, generation: int) -> None:
        with self._lock:
            buffer = self._buffer if generation == self._generation else None
            sink = self._sink
            callback = self._on_drained
            ready = (
                buffer is not None
                and sink is not None
                and callback is not None
                and buffer.finished_and_empty(generation)
                and sink.state() is QtAudio.State.IdleState
            )
            if ready:
                self._on_drained = None
        if ready:
            callback()
