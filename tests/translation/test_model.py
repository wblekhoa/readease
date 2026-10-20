"""ReadEase's own translator download (RE-PLAY-031)."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vieneu_reader.speech.kokoro import EnglishModelError
from vieneu_reader.translation import model as translator


class TranslatorModelTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.models = Path(folder.name)
        self.payload = b"gguf" * 64
        # The real file is 1.1 GB; the checks are the same on a small one.
        patches = [
            mock.patch.object(translator, "MODEL_SHA256", hashlib.sha256(self.payload).hexdigest()),
            mock.patch.object(translator, "DOWNLOAD_BYTES", len(self.payload)),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def fetcher(self, payload: bytes):
        """Behaves as the shared `_fetch` does: checks the hash before the
        file lands, and raises its own error when it does not match."""
        calls = []

        def fetch(url, target, expected, progress):
            calls.append(url)
            if expected is not None and hashlib.sha256(payload).hexdigest() != expected:
                raise EnglishModelError("mismatch")
            target.write_bytes(payload)
            progress(len(payload))
        return fetch, calls

    # RE-PLAY-031
    def test_a_download_that_matches_is_ready_and_says_where_it_is(self):
        fetch, calls = self.fetcher(self.payload)
        model = translator.TranslatorModel(self.models, file_fetcher=fetch)
        self.assertFalse(model.is_model_ready)
        seen = []
        model.prepare_model(lambda fraction, message: seen.append(fraction))
        self.assertTrue(model.is_model_ready)
        self.assertEqual(model.path.read_bytes(), self.payload)
        self.assertEqual(calls, [translator.MODEL_URL])
        self.assertIn(translator.MODEL_REVISION, translator.MODEL_URL)
        self.assertEqual(seen[-1], 1.0)
        # Already there: nothing fetched again.
        model.prepare_model(lambda *_: None)
        self.assertEqual(len(calls), 1)

    # RE-PLAY-031
    def test_a_file_that_does_not_match_is_never_ready(self):
        fetch, _ = self.fetcher(b"something else")
        model = translator.TranslatorModel(self.models, file_fetcher=fetch)
        with self.assertRaises(translator.TranslatorModelError) as raised:
            model.prepare_model(lambda *_: None)
        # Said as a mismatch, not as a network problem.
        self.assertIn("không khớp", str(raised.exception))
        self.assertFalse(model.is_model_ready)

    # RE-PLAY-031
    def test_remove_deletes_the_model_folder_only(self):
        fetch, _ = self.fetcher(self.payload)
        model = translator.TranslatorModel(self.models, file_fetcher=fetch)
        model.prepare_model(lambda *_: None)
        (self.models / "other").mkdir()
        self.assertTrue(model.remove())
        self.assertFalse(model.is_model_ready)
        self.assertEqual(model.installed_size(), 0)
        self.assertTrue((self.models / "other").is_dir())
        self.assertFalse(model.remove())


if __name__ == "__main__":
    unittest.main()
