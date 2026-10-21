"""A book's translations kept on this Mac (RE-PLAY-032)."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from vieneu_reader.storage.translations import TranslationStore


class TranslationStoreTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "translations.sqlite3"
        self.store = TranslationStore(self.path)
        self.addCleanup(self.store.close)

    # RE-PLAY-032
    def test_kept_per_book_paragraph_and_language_and_replaced_by_a_later_one(self):
        self.store.put("b1", "en", "readease", {"p1": "One.", "p2": "Two."})
        self.store.put("b1", "vi", "apple", {"p1": "Một."})
        self.store.put("b1", "en", "apple", {"p1": "One again."})
        self.assertEqual(self.store.get("b1", "en"), {"p1": "One again.", "p2": "Two."})
        self.assertEqual(self.store.get("b1", "en", ["p2", "nope"]), {"p2": "Two."})
        self.assertEqual(self.store.get("b2", "en"), {})

    # RE-PLAY-032
    def test_private_file_and_deleting_a_book_or_a_language(self):
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode) & 0o077, 0)
        self.store.put("b1", "en", "x", {"p1": "One.", "p2": "Two."})
        self.store.put("b1", "vi", "x", {"p1": "Một."})
        self.assertEqual(self.store.delete("b1", "en", ["p1"]), 1)
        self.assertEqual(self.store.delete("b1", "vi"), 1)
        self.assertEqual(self.store.delete("b1"), 1)
        self.assertEqual(self.store.get("b1", "en"), {})

    def test_an_unknown_language_and_empty_text_are_not_kept(self):
        with self.assertRaises(ValueError):
            self.store.put("b1", "fr", "x", {"p1": "Un."})
        self.assertEqual(self.store.put("b1", "en", "x", {"p1": "  "}), 0)


if __name__ == "__main__":
    unittest.main()
