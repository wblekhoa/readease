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

from vieneu_reader.settings import update_settings
from vieneu_reader.integrations.selection_shortcut import (
    CMD_KEY,
    CONTROL_KEY,
    DEFAULT_SHORTCUT,
    OPTION_KEY,
    SHIFT_KEY,
    InvalidShortcutError,
    ReadOnCopyPreferenceStore,
    Shortcut,
    ShortcutPreferenceStore,
)
from vieneu_reader.ui.shortcut_recorder import (
    ShortcutRecorderButton,
    carbon_modifiers_from_qt,
    key_code_from_qt,
)


class ShortcutValueTests(unittest.TestCase):
    def test_modifier_values_match_the_native_helper_contract(self) -> None:
        # The helper is handed these numbers and passes them to Carbon, so the
        # two layers have to agree on what each modifier is worth. This is
        # about the constants, not about which of them the default happens to
        # use.
        self.assertEqual(CONTROL_KEY, 0x1000)
        self.assertEqual(OPTION_KEY, 0x0800)
        self.assertEqual(CMD_KEY, 0x0100)
        self.assertEqual(CONTROL_KEY | OPTION_KEY | CMD_KEY, 6400)

    def test_the_default_asks_for_two_modifiers_not_three(self) -> None:
        """Three modifiers is a lot of hand for something pressed mid-read."""
        self.assertEqual(DEFAULT_SHORTCUT.key_code, 15)
        self.assertEqual(DEFAULT_SHORTCUT.modifiers, OPTION_KEY | CMD_KEY)
        self.assertEqual(DEFAULT_SHORTCUT.label, "Option + Command + R")

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

    def test_the_old_three_modifier_default_is_moved_to_the_short_one(self) -> None:
        """The app saved the first default into settings the moment it
        registered it, so nobody on it ever chose it. Leaving it there would
        mean the shorter default only ever reached fresh installs."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = ShortcutPreferenceStore(path)
            path.write_text(
                '{"selection_shortcut": {"key_code": 15, "modifiers": 6400}}',
                encoding="utf-8",
            )

            self.assertEqual(store.load(), DEFAULT_SHORTCUT)
            self.assertEqual(store.load().label, "Option + Command + R")

    def test_a_combination_someone_chose_is_never_moved(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = ShortcutPreferenceStore(path)
            for chosen in (
                Shortcut(key_code=38, modifiers=CONTROL_KEY | CMD_KEY),
                # Same three modifiers as the old default, but a different key:
                # a real choice, and it has to survive.
                Shortcut(
                    key_code=38,
                    modifiers=CONTROL_KEY | OPTION_KEY | CMD_KEY,
                ),
            ):
                with self.subTest(chosen=chosen.label):
                    self.assertTrue(store.save(chosen))

                    self.assertEqual(store.load(), chosen)

    def test_unusable_stored_shortcut_falls_back_to_the_default(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = ShortcutPreferenceStore(path)

            path.write_text(
                '{"selection_shortcut": {"key_code": 15, "modifiers": 0}}',
                encoding="utf-8",
            )

            self.assertEqual(store.load(), DEFAULT_SHORTCUT)


class ReadOnCopyPreferenceStoreTests(unittest.TestCase):
    def test_read_on_copy_is_off_unless_it_was_deliberately_turned_on(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = ReadOnCopyPreferenceStore(path)

            self.assertFalse(store.load())

            for payload in (
                '{"read_on_copy": "true"}',
                '{"read_on_copy": 1}',
                '{"read_on_copy": null}',
                "not json at all",
            ):
                path.write_text(payload, encoding="utf-8")
                self.assertFalse(store.load(), payload)

            path.write_text('{"language": "en"}', encoding="utf-8")
            self.assertTrue(store.save(True))

            self.assertTrue(store.load())
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"language": "en", "read_on_copy": True},
            )

            self.assertTrue(store.save(False))
            self.assertFalse(store.load())


class SettingsDocumentTests(unittest.TestCase):
    def test_a_damaged_file_is_kept_instead_of_being_written_over(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"language": "en", oops', encoding="utf-8")

            self.assertTrue(update_settings(path, {"language": "vi"}))

            # The unreadable file may hold settings this build cannot parse;
            # saving one preference must not be what destroys them.
            salvaged = path.with_name(path.name + ".damaged")
            self.assertTrue(salvaged.is_file())
            self.assertEqual(
                salvaged.read_text(encoding="utf-8"),
                '{"language": "en", oops',
            )
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"language": "vi"},
            )

    def test_an_ordinary_save_leaves_no_salvage_copy(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"language": "en"}', encoding="utf-8")

            self.assertTrue(update_settings(path, {"read_on_copy": True}))

            self.assertFalse(path.with_name(path.name + ".damaged").exists())
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"language": "en", "read_on_copy": True},
            )


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
