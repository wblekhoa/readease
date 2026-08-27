"""A button that listens for one key combination and hands it back."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent
from PySide6.QtWidgets import QPushButton, QWidget

from vieneu_reader.integrations.selection_shortcut import (
    CMD_KEY,
    CONTROL_KEY,
    KEY_CODES,
    OPTION_KEY,
    SHIFT_KEY,
    InvalidShortcutError,
    Shortcut,
)


# Qt reports the Command key as ControlModifier and the Control key as
# MetaModifier on macOS, so the Carbon mask has to swap the two back.
_MODIFIERS: tuple[tuple[Qt.KeyboardModifier, int], ...] = (
    (Qt.KeyboardModifier.ControlModifier, CMD_KEY),
    (Qt.KeyboardModifier.MetaModifier, CONTROL_KEY),
    (Qt.KeyboardModifier.AltModifier, OPTION_KEY),
    (Qt.KeyboardModifier.ShiftModifier, SHIFT_KEY),
)

_QT_KEY_CODES: dict[int, int] = {
    int(qt_key): key_code
    for name, key_code in KEY_CODES.items()
    if (qt_key := getattr(Qt.Key, f"Key_{name}", None)) is not None
}

_MODIFIER_KEYS = frozenset(
    {
        int(Qt.Key.Key_Control),
        int(Qt.Key.Key_Meta),
        int(Qt.Key.Key_Alt),
        int(Qt.Key.Key_Shift),
        int(Qt.Key.Key_CapsLock),
        int(Qt.Key.Key_AltGr),
    }
)


def carbon_modifiers_from_qt(modifiers: Qt.KeyboardModifier) -> int:
    mask = 0
    for qt_modifier, carbon_modifier in _MODIFIERS:
        if modifiers & qt_modifier:
            mask |= carbon_modifier
    return mask


def key_code_from_qt(key: int) -> int | None:
    return _QT_KEY_CODES.get(int(key))


class ShortcutRecorderButton(QPushButton):
    """Wait for one combination, ignoring anything macOS could not register."""

    shortcutRecorded = Signal(object)
    recordingChanged = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._recording = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(self.start_recording)

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        if self._recording:
            return
        self._recording = True
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.recordingChanged.emit(True)

    def stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self.recordingChanged.emit(False)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if not self._recording:
            super().keyPressEvent(event)
            return
        event.accept()
        key = int(event.key())
        if key == int(Qt.Key.Key_Escape):
            self.stop_recording()
            return
        if key in _MODIFIER_KEYS:
            return
        key_code = key_code_from_qt(key)
        if key_code is None:
            return
        try:
            shortcut = Shortcut(
                key_code=key_code,
                modifiers=carbon_modifiers_from_qt(event.modifiers()),
            )
        except InvalidShortcutError:
            return
        self.stop_recording()
        self.shortcutRecorded.emit(shortcut)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802
        self.stop_recording()
        super().focusOutEvent(event)
