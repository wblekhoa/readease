"""Application composition root; views depend only on stable local ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from vieneu_reader.config import AppPaths, default_app_root
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.integrations.macos_selection import (
    SelectionShortcutBridge,
)
from vieneu_reader.integrations.selection_shortcut import (
    ShortcutPreferenceStore,
)
from vieneu_reader.playback.coordinator import PlaybackCoordinator
from vieneu_reader.playback.preferences import VoicePreferenceStore
from vieneu_reader.playback.qt_audio import QtAudioOutput
from vieneu_reader.speech.cache import AudioCache
from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore
from vieneu_reader.speech.vieneu import VieNeuSpeechEngine
from vieneu_reader.storage.repository import LibraryRepository

from vieneu_reader.integrations.apple_books import AppleBooksLibrary
from .controller import ReaderController
from .i18n import LanguagePreferenceStore
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
        # The window and its widget tree sit in reference cycles - Qt parent
        # links, signal connections, this dataclass - so refcounting alone never
        # frees them. Only the cyclic collector does, and it runs at whatever
        # allocation happens to cross its threshold. When a second runtime
        # provides that pressure, the collector has torn this widget tree down
        # in the middle of an unrelated Qt call and taken the process with it.
        # Handing the objects to Qt moves destruction to a point Qt controls.
        self.window.close()
        self.window.deleteLater()
        self.dispatcher.deleteLater()


def build_runtime(app_data_root: Path | None = None) -> AppRuntime:
    paths = AppPaths.create(app_data_root or default_app_root())
    repository = LibraryRepository(paths.database)
    library_service = LibraryService(paths, repository)
    settings_path = paths.root / "settings.json"
    voice_quality_store = VoiceQualityPreferenceStore(settings_path)
    engine = VieNeuSpeechEngine(
        paths.models,
        precision=voice_quality_store.load(),
    )
    cache = AudioCache(paths.cache / "Audio")
    audio_output = QtAudioOutput()
    playback = PlaybackCoordinator(
        engine=engine,
        cache=cache,
        progress_repository=repository,
        output=audio_output,
    )
    dispatcher = QtDispatcher()
    voice_store = VoicePreferenceStore(settings_path)
    controller = ReaderController(
        repository,
        library_service,
        playback,
        dispatch=dispatcher,
        voice_store=voice_store,
    )
    model_setup = ModelSetupCoordinator(engine)
    language_store = LanguagePreferenceStore(settings_path)
    shortcut_store = ShortcutPreferenceStore(settings_path)
    selection_shortcut = SelectionShortcutBridge(
        shortcut=shortcut_store.load(),
        # Pressed again while a reading is under way, the shortcut stops it,
        # so there is a way out without leaving the app being read.
        is_reading=lambda: controller.is_reading,
    )
    selection_shortcut.stopRequested.connect(controller.stop)
    selection_shortcut.selectionReceived.connect(
        controller.read_external_selection
    )
    selection_shortcut.statusReceived.connect(
        controller.external_selection_failed
    )
    model_setup.ready.connect(lambda _voices: selection_shortcut.start())
    window = ReaderWindow(
        controller,
        model_setup,
        language_store=language_store,
        selection_shortcut=selection_shortcut.shortcut,
        shortcut_store=shortcut_store,
        voice_quality_store=voice_quality_store,
        # Holds no path and touches no disk until the tab that needs it is
        # opened; a person who never opens it never has their Books folder read.
        apple_books=AppleBooksLibrary(),
    )
    window.selectionShortcutChanged.connect(selection_shortcut.apply_shortcut)
    # The window remembers only a combination macOS actually registered, so a
    # shortcut another app owns can never come back on the next launch.
    selection_shortcut.shortcutAccepted.connect(window.set_selection_shortcut)
    return AppRuntime(
        paths=paths,
        repository=repository,
        playback=playback,
        model_setup=model_setup,
        selection_shortcut=selection_shortcut,
        dispatcher=dispatcher,
        window=window,
    )
