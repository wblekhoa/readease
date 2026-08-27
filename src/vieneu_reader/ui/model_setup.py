"""Non-blocking bridge for explicit local model preparation."""

from __future__ import annotations

from threading import Event, RLock, Thread
from typing import Any

from PySide6.QtCore import QObject, Signal


class _PreparationCancelled(Exception):
    pass


class ModelSetupCoordinator(QObject):
    progressChanged = Signal(float, str)
    ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, engine: Any, parent: QObject | None = None):
        super().__init__(parent)
        self._engine = engine
        self._lock = RLock()
        self._cancel = Event()
        self._worker: Thread | None = None
        self._closed = False

    @property
    def is_ready(self) -> bool:
        return bool(self._engine.is_model_ready)

    def start(self) -> None:
        with self._lock:
            if self._closed or (self._worker is not None and self._worker.is_alive()):
                return
            self._cancel.clear()
            worker = Thread(
                target=self._run,
                name="vieneu-model-setup",
                daemon=True,
            )
            self._worker = worker
            worker.start()

    def cancel(self) -> None:
        with self._lock:
            worker = self._worker
            if worker is None or not worker.is_alive():
                return
            self._cancel.set()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._cancel.set()

    def _progress(self, value: float, message: str) -> None:
        if self._cancel.is_set():
            raise _PreparationCancelled()
        self.progressChanged.emit(value, message)

    def _emit_if_open(self, signal: Any, *args: Any) -> None:
        with self._lock:
            if not self._closed:
                signal.emit(*args)

    def _run(self) -> None:
        try:
            self._engine.prepare_model(self._progress)
            if self._cancel.is_set():
                raise _PreparationCancelled()
            voices = self._engine.voices()
            if self._cancel.is_set():
                raise _PreparationCancelled()
            self._emit_if_open(self.ready, voices)
        except _PreparationCancelled:
            self._emit_if_open(self.cancelled)
        except Exception:
            self._emit_if_open(
                self.failed,
                "Không thể chuẩn bị giọng đọc. Hãy kiểm tra kết nối mạng và Thử lại."
            )
