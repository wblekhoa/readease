"""Continuous, cancellation-safe reading playback."""

from .coordinator import PlaybackCoordinator, PlaybackSnapshot, PlaybackState

__all__ = ["PlaybackCoordinator", "PlaybackSnapshot", "PlaybackState", "QtAudioOutput"]


def __getattr__(name):
    # QtAudioOutput drags PySide6 in; the headless sidecar ships without Qt
    # and only ever touches the pure modules. Loading it on demand keeps the
    # Qt shell's import surface identical and the sidecar Qt-free.
    if name == "QtAudioOutput":
        from .qt_audio import QtAudioOutput

        return QtAudioOutput
    raise AttributeError(name)
