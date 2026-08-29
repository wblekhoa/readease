"""Choosing a model build must reach every place that build is remembered."""

import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from vieneu_reader.speech.cache import audio_cache_key
from vieneu_reader.speech.contracts import SynthesisSettings
from vieneu_reader.speech.preferences import (
    ENVIRONMENT_KEY,
    SETTINGS_KEY,
    VoiceQualityPreferenceStore,
)
from vieneu_reader.speech.vieneu import (
    CODEC_DIRECTORY,
    CODEC_REVISION,
    MODEL_DIRECTORY,
    DEFAULT_PRECISION,
    MODEL_REVISION,
    PRECISIONS,
    VieNeuSpeechEngine,
)
from vieneu_reader.ui.i18n import Language, LanguagePreferenceStore


class PrecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.models = Path(self.temp_dir.name) / "Models"

    def tearDown(self):
        self.temp_dir.cleanup()

    def engine(self, precision):
        return VieNeuSpeechEngine(
            self.models,
            sdk_factory=lambda **kwargs: None,
            precision=precision,
        )

    def test_an_unknown_build_is_refused_rather_than_guessed(self):
        with self.assertRaises(ValueError):
            self.engine("fp16")

    def test_the_shipped_default_is_the_small_fast_one(self):
        self.assertEqual(DEFAULT_PRECISION, "int8")
        self.assertEqual(self.engine(DEFAULT_PRECISION).precision, "int8")

    def test_each_build_reads_from_its_own_folder(self):
        for precision, subfolder in PRECISIONS.items():
            with self.subTest(precision=precision):
                engine = self.engine(precision)
                self.assertEqual(engine._onnx_directory.name, subfolder)

    def test_the_two_builds_never_share_an_audio_cache_entry(self):
        """Both live in one repo revision, so the revision alone cannot separate
        them. Without this, switching would keep serving the other build."""
        settings = SynthesisSettings()
        keys = {
            precision: audio_cache_key(
                "Xin chào",
                "Adam",
                self.engine(precision).engine_version,
                self.engine(precision).model_revision,
                settings,
            )
            for precision in PRECISIONS
        }
        self.assertEqual(len(set(keys.values())), len(PRECISIONS), keys)

    def test_the_revision_still_names_the_pinned_commit(self):
        for precision in PRECISIONS:
            with self.subTest(precision=precision):
                self.assertIn(MODEL_REVISION, self.engine(precision).model_revision)

    def test_each_build_has_its_own_readiness_record(self):
        markers = {p: self.engine(p)._ready_marker for p in PRECISIONS}
        self.assertEqual(len(set(markers.values())), len(PRECISIONS), markers)

    def test_preparing_downloads_only_the_chosen_build(self):
        for precision, subfolder in PRECISIONS.items():
            with self.subTest(precision=precision):
                seen = []

                def downloader(**kwargs):
                    seen.append(kwargs.get("allow_patterns"))
                    return ""

                engine = VieNeuSpeechEngine(
                    self.models,
                    sdk_factory=lambda **kwargs: None,
                    model_downloader=downloader,
                    precision=precision,
                )
                with self.assertRaises(Exception):
                    engine.prepare_model(lambda *_: None)
                self.assertIn([f"{subfolder}/*"], seen)

    def test_the_chosen_build_is_what_the_sdk_is_asked_for(self):
        for precision in PRECISIONS:
            with self.subTest(precision=precision):
                engine = self.engine(precision)
                self.assertEqual(
                    engine._sdk_arguments(prepared=False)["precision"], precision
                )


class ExistingInstallTests(unittest.TestCase):
    """Nobody who already has the model should be asked to download it again."""

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.models = Path(self.temp_dir.name) / "Models"
        self.models.mkdir(parents=True)
        # Exactly what a pre-existing install has on disk.
        (self.models / ".vieneu-ready.json").write_text(
            json.dumps(
                {
                    "codec_revision": CODEC_REVISION,
                    "engine_version": "3.3.0",
                    "model_revision": MODEL_REVISION,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (self.models / ".vieneu-ready.json").chmod(0o600)

    def tearDown(self):
        self.temp_dir.cleanup()

    def engine(self, precision):
        return VieNeuSpeechEngine(
            self.models, sdk_factory=lambda **kwargs: None, precision=precision
        )

    def test_the_readiness_record_from_before_this_choice_still_counts(self):
        self.assertTrue(self.engine("int8")._marker_matches())

    def test_but_it_does_not_vouch_for_a_build_it_never_saw(self):
        self.assertFalse(self.engine("fp32")._marker_matches())


class RemovingAnUnusedBuildTests(unittest.TestCase):
    """One build is downloaded at a time; the other must not be stuck there."""

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.models = Path(self.temp_dir.name) / "Models"
        self.root = self.models / MODEL_DIRECTORY
        for subfolder, size in (("onnx_int8", 1200), ("onnx_update", 3400)):
            (self.root / subfolder).mkdir(parents=True)
            (self.root / subfolder / "vieneu_backbone_shared.data").write_bytes(
                b"x" * size
            )
        self.codec = self.models / CODEC_DIRECTORY
        self.codec.mkdir(parents=True)
        (self.codec / "keep-me").write_bytes(b"codec")

    def tearDown(self):
        self.temp_dir.cleanup()

    def engine(self, precision):
        return VieNeuSpeechEngine(
            self.models, sdk_factory=lambda **kwargs: None, precision=precision
        )

    def test_it_reports_what_each_build_is_taking_up(self):
        sizes = self.engine("int8").installed_builds()

        self.assertEqual(sizes["int8"], 1200)
        self.assertEqual(sizes["fp32"], 3400)

    def test_a_build_that_was_never_downloaded_reads_as_nothing(self):
        shutil.rmtree(self.root / "onnx_update")

        self.assertEqual(self.engine("int8").installed_builds()["fp32"], 0)

    def test_the_build_not_in_use_can_be_removed(self):
        removed = self.engine("fp32").remove_build("int8")

        self.assertTrue(removed)
        self.assertFalse((self.root / "onnx_int8").exists())
        # And nothing else went with it.
        self.assertTrue((self.root / "onnx_update").exists())
        self.assertTrue((self.codec / "keep-me").exists())

    def test_the_build_in_use_is_refused(self):
        """Removing what the app is reading with would break a working install."""
        with self.assertRaises(ValueError):
            self.engine("fp32").remove_build("fp32")

        self.assertTrue((self.root / "onnx_update").exists())

    def test_a_build_this_version_does_not_know_is_refused(self):
        with self.assertRaises(ValueError):
            self.engine("int8").remove_build("fp16")

    def test_removing_it_also_drops_its_readiness_record(self):
        engine = self.engine("int8")
        engine._write_ready_marker()
        marker = engine._ready_marker
        self.assertTrue(marker.exists())

        self.engine("fp32").remove_build("int8")

        self.assertFalse(marker.exists())

    def test_removing_one_that_is_already_gone_says_so_without_raising(self):
        engine = self.engine("fp32")
        engine.remove_build("int8")

        self.assertFalse(engine.remove_build("int8"))


class VoiceQualityPreferenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "settings.json"
        self.store = VoiceQualityPreferenceStore(self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_nothing_saved_yet_means_the_shipped_default(self):
        self.assertEqual(self.store.load(), DEFAULT_PRECISION)

    def test_a_saved_choice_comes_back(self):
        self.store.save("fp32")
        self.assertEqual(VoiceQualityPreferenceStore(self.path).load(), "fp32")

    def test_a_build_this_version_does_not_know_falls_back(self):
        self.path.write_text(json.dumps({SETTINGS_KEY: "fp16"}), encoding="utf-8")
        self.assertEqual(self.store.load(), DEFAULT_PRECISION)

    def test_saving_it_keeps_the_other_preferences(self):
        LanguagePreferenceStore(self.path).save(Language.ENGLISH)
        self.store.save("fp32")
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["language"], "en")
        self.assertEqual(stored[SETTINGS_KEY], "fp32")

    def test_the_environment_can_try_a_build_without_saving_it(self):
        self.store.save("int8")
        with patch.dict(os.environ, {ENVIRONMENT_KEY: "fp32"}):
            self.assertEqual(self.store.load(), "fp32")
        self.assertEqual(self.store.load(), "int8")

    def test_refusing_to_save_a_build_that_does_not_exist(self):
        with self.assertRaises(ValueError):
            self.store.save("fp16")


if __name__ == "__main__":
    unittest.main()
