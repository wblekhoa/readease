import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.integrations.selection_shortcut import ShortcutPreferenceStore
from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore
from vieneu_reader.playback.preferences import (
    DEFAULT_RATE,
    DEFAULT_VOICE_ID,
    VoicePreferenceStore,
)
from vieneu_reader.ui.i18n import Language, LanguagePreferenceStore


class VoicePreferenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "settings.json"
        self.store = VoicePreferenceStore(self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_nothing_stored_yet_reads_as_the_shipped_default(self):
        self.assertEqual(self.store.load_voice(), DEFAULT_VOICE_ID)
        self.assertEqual(self.store.load_rate(), DEFAULT_RATE)

    def test_a_saved_choice_survives_a_new_store_over_the_same_file(self):
        self.store.save("Trúc Ly", 1.25)

        reopened = VoicePreferenceStore(self.path)

        self.assertEqual(reopened.load_voice(), "Trúc Ly")
        self.assertEqual(reopened.load_rate(), 1.25)

    def test_saving_the_voice_leaves_the_other_preferences_alone(self):
        LanguagePreferenceStore(self.path).save(Language.ENGLISH)
        shortcut = ShortcutPreferenceStore(self.path)
        shortcut.save(shortcut.load())
        VoiceQualityPreferenceStore(self.path).save("fp32")

        self.store.save("Ngọc Linh", 1.5)

        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["language"], "en")
        self.assertIn("selection_shortcut", stored)
        self.assertEqual(stored["voice_quality"], "fp32")
        self.assertEqual(stored["voice"], "Ngọc Linh")

    def test_a_speed_outside_the_supported_range_is_not_handed_on(self):
        # QtAudioOutput raises for anything outside 0.5-2.0, from inside a Qt
        # slot where nothing would catch it.
        self.path.write_text(json.dumps({"rate": 5.0}), encoding="utf-8")

        self.assertEqual(self.store.load_rate(), DEFAULT_RATE)

    def test_a_blank_or_wrongly_typed_voice_falls_back(self):
        for payload in ({"voice": ""}, {"voice": 7}, {"voice": None}):
            with self.subTest(payload=payload):
                self.path.write_text(json.dumps(payload), encoding="utf-8")
                self.assertEqual(self.store.load_voice(), DEFAULT_VOICE_ID)

    def test_an_unreadable_settings_file_reads_as_the_default(self):
        self.path.write_text("{ not json", encoding="utf-8")

        self.assertEqual(self.store.load_voice(), DEFAULT_VOICE_ID)
        self.assertEqual(self.store.load_rate(), DEFAULT_RATE)


if __name__ == "__main__":
    unittest.main()
