from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from vieneu_reader.integrations.selection_shortcut import (
    CMD_KEY,
    CONTROL_KEY,
    DEFAULT_SHORTCUT,
    OPTION_KEY,
    SHIFT_KEY,
    InvalidShortcutError,
    Shortcut,
    ShortcutPreferenceStore,
)
from vieneu_reader.ui.shortcut_recorder import (
    ShortcutRecorderButton,
    carbon_modifiers_from_qt,
    key_code_from_qt,
)


class ShortcutValueTests(unittest.TestCase):
    def test_default_matches_the_native_helper_contract(self) -> None:
        # The native helper compiles kVK_ANSI_R and controlKey|optionKey|cmdKey
        # into these exact numbers; both layers pin them independently.
        self.assertEqual(DEFAULT_SHORTCUT.key_code, 15)
        self.assertEqual(DEFAULT_SHORTCUT.modifiers, 6400)
        self.assertEqual(CONTROL_KEY | OPTION_KEY | CMD_KEY, 6400)
        self.assertEqual(DEFAULT_SHORTCUT.label, "Control + Option + Command + R")

    def test_labels_read_in_the_macos_order(self) -> None:
        shortcut = Shortcut(
            key_code=96,
            modifiers=CONTROL_KEY | OPTION_KEY | SHIFT_KEY | CMD_KEY,
        )

        self.assertEqual(
            shortcut.label,
            "Control + Option + Shift + Command + F5",
        )

    def test_rejects_combinations_that_would_hijack_typing(self) -> None:
        with self.assertRaises(InvalidShortcutError):
            Shortcut(key_code=15, modifiers=0)
        with self.assertRaises(InvalidShortcutError):
            Shortcut(key_code=15, modifiers=SHIFT_KEY)
        with self.assertRaises(InvalidShortcutError):
            Shortcut(key_code=15, modifiers=CMD_KEY | 0x4000)
        with self.assertRaises(InvalidShortcutError):
            Shortcut(key_code=200, modifiers=CMD_KEY)

    def test_round_trips_through_a_settings_payload(self) -> None:
        shortcut = Shortcut(key_code=38, modifiers=CONTROL_KEY | CMD_KEY)

        payload = shortcut.to_payload()

        self.assertEqual(payload, {"key_code": 38, "modifiers": 4352})
        self.assertEqual(Shortcut.from_payload(payload), shortcut)
        self.assertEqual(Shortcut.from_payload({"key_code": 38}), None)
        self.assertEqual(Shortcut.from_payload({"key_code": 15, "modifiers": 0}), None)
        self.assertEqual(Shortcut.from_payload("not a mapping"), None)


class ShortcutPreferenceStoreTests(unittest.TestCase):
    def test_defaults_safely_and_keeps_other_settings_intact(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = ShortcutPreferenceStore(path)

            self.assertEqual(store.load(), DEFAULT_SHORTCUT)

            path.write_text('{"language": "en"}', encoding="utf-8")
            chosen = Shortcut(key_code=38, modifiers=CONTROL_KEY | CMD_KEY)
            self.assertTrue(store.save(chosen))

            self.assertEqual(store.load(), chosen)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {
                    "language": "en",
                    "selection_shortcut": {"key_code": 38, "modifiers": 4352},
                },
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_unusable_stored_shortcut_falls_back_to_the_default(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = ShortcutPreferenceStore(path)

            path.write_text(
                '{"selection_shortcut": {"key_code": 15, "modifiers": 0}}',
                encoding="utf-8",
            )

            self.assertEqual(store.load(), DEFAULT_SHORTCUT)


class ShortcutRecorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_qt_modifiers_map_to_carbon_with_the_macos_command_swap(self) -> None:
        # Qt reports the Command key as ControlModifier and the Control key as
        # MetaModifier on the cocoa platform, so the map has to swap them back.
        self.assertEqual(
            carbon_modifiers_from_qt(Qt.KeyboardModifier.ControlModifier),
            CMD_KEY,
        )
        self.assertEqual(
            carbon_modifiers_from_qt(Qt.KeyboardModifier.MetaModifier),
            CONTROL_KEY,
        )
        self.assertEqual(
            carbon_modifiers_from_qt(Qt.KeyboardModifier.AltModifier),
            OPTION_KEY,
        )
        self.assertEqual(
            carbon_modifiers_from_qt(Qt.KeyboardModifier.ShiftModifier),
            SHIFT_KEY,
        )

    def test_qt_keys_map_onto_macos_virtual_key_codes(self) -> None:
        self.assertEqual(key_code_from_qt(Qt.Key.Key_R), 15)
        self.assertEqual(key_code_from_qt(Qt.Key.Key_A), 0)
        self.assertEqual(key_code_from_qt(Qt.Key.Key_F5), 96)
        self.assertIsNone(key_code_from_qt(Qt.Key.Key_Home))

    def _press(self, recorder: ShortcutRecorderButton, key, modifiers) -> None:
        event = QKeyEvent(QEvent.Type.KeyPress, key, modifiers)
        QApplication.sendEvent(recorder, event)

    def test_records_only_registrable_combinations_and_cancels_on_escape(self) -> None:
        recorder = ShortcutRecorderButton()
        recorded: list[Shortcut] = []
        states: list[bool] = []
        recorder.shortcutRecorded.connect(recorded.append)
        recorder.recordingChanged.connect(states.append)

        recorder.start_recording()
        self.assertTrue(recorder.is_recording)
        self.assertEqual(states, [True])

        # A bare key would swallow that key for every app: keep waiting.
        self._press(recorder, Qt.Key.Key_J, Qt.KeyboardModifier.NoModifier)
        # Shift alone is not enough either.
        self._press(recorder, Qt.Key.Key_J, Qt.KeyboardModifier.ShiftModifier)
        # A held modifier on its own must not end the recording.
        self._press(
            recorder,
            Qt.Key.Key_Control,
            Qt.KeyboardModifier.ControlModifier,
        )
        # A key macOS has no virtual code for in our table is refused too.
        self._press(
            recorder,
            Qt.Key.Key_Home,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.assertEqual(recorded, [])
        self.assertTrue(recorder.is_recording)

        self._press(
            recorder,
            Qt.Key.Key_J,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
        )

        self.assertEqual(
            recorded,
            [Shortcut(key_code=38, modifiers=CMD_KEY | OPTION_KEY)],
        )
        self.assertFalse(recorder.is_recording)
        self.assertEqual(states, [True, False])

        recorder.start_recording()
        self._press(recorder, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)

        self.assertEqual(len(recorded), 1)
        self.assertFalse(recorder.is_recording)
        recorder.deleteLater()


if __name__ == "__main__":
    unittest.main()
