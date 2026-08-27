"""Application composition root; views depend only on stable local ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from vieneu_reader.config import AppPaths, default_app_root
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.integrations.macos_selection import SelectionShortcutBridge
from vieneu_reader.playback.coordinator import PlaybackCoordinator
from vieneu_reader.playback.qt_audio import QtAudioOutput
from vieneu_reader.speech.cache import AudioCache
from vieneu_reader.speech.vieneu import VieNeuSpeechEngine
from vieneu_reader.storage.repository import LibraryRepository

from .controller import ReaderController
from .model_setup import ModelSetupCoordinator
from .window import ReaderWindow


class QtDispatcher(QObject):
    _dispatchRequested = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._dispatchRequested.connect(self._run)

    def __call__(self, action: Callable[[], None]) -> None:
        if QThread.currentThread() is self.thread():
            action()
        else:
            self._dispatchRequested.emit(action)

    @Slot(object)
    def _run(self, action: Callable[[], None]) -> None:
        action()


@dataclass(slots=True)
class AppRuntime:
    paths: AppPaths
    repository: LibraryRepository
    playback: PlaybackCoordinator
    model_setup: ModelSetupCoordinator
    selection_shortcut: SelectionShortcutBridge
    dispatcher: QtDispatcher
    window: ReaderWindow
    _closed: bool = field(default=False, init=False)
    _close_lock: RLock = field(default_factory=RLock, init=False)

    def close(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
        self.selection_shortcut.close()
        self.model_setup.close()
        self.playback.close()
        self.repository.close()


def build_runtime(app_data_root: Path | None = None) -> AppRuntime:
    paths = AppPaths.create(app_data_root or default_app_root())
    repository = LibraryRepository(paths.database)
    library_service = LibraryService(paths, repository)
    engine = VieNeuSpeechEngine(paths.models)
    cache = AudioCache(paths.cache / "Audio")
    audio_output = QtAudioOutput()
    playback = PlaybackCoordinator(
        engine=engine,
        cache=cache,
        progress_repository=repository,
        output=audio_output,
    )
    dispatcher = QtDispatcher()
    controller = ReaderController(
        repository,
        library_service,
        playback,
        dispatch=dispatcher,
    )
    model_setup = ModelSetupCoordinator(engine)
    selection_shortcut = SelectionShortcutBridge()
    selection_shortcut.selectionReceived.connect(
        controller.read_external_selection
    )
    selection_shortcut.statusReceived.connect(
        controller.external_selection_failed
    )
    model_setup.ready.connect(lambda _voices: selection_shortcut.start())
    window = ReaderWindow(controller, model_setup)
    return AppRuntime(
        paths=paths,
        repository=repository,
        playback=playback,
        model_setup=model_setup,
        selection_shortcut=selection_shortcut,
        dispatcher=dispatcher,
        window=window,
    )
