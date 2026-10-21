"""A book's words are made ready when it opens (RE-PLAY-034)."""

from __future__ import annotations

import io
import json
import tempfile
import time
import unittest
from pathlib import Path

from vieneu_reader.headless.server import _Session
from vieneu_reader.storage.repository import LibraryRepository
from tests.headless.test_server import BOOK_ID, FakeEngine, build_book


class PreparedBookTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.repository = LibraryRepository(root / "reader.sqlite3")
        self.addCleanup(self.repository.close)
        book = build_book([("Một", [(f"Đoạn số {i}.", "paragraph") for i in range(5)])])
        source = root / "book.epub"
        source.write_bytes(b"fixture")
        self.repository.add_book(book, source)
        self.settings = root / "settings.json"
        self.session = _Session(io.StringIO(""), io.StringIO(), FakeEngine(chunks_per_sentence=1),
                                repository=self.repository, settings_path=self.settings)
        self.stored = self.repository.get_book(BOOK_ID)

    # RE-PLAY-034
    def test_a_second_build_is_the_cached_one_until_a_shaping_setting_changes(self):
        first = self.session._book_utterances(self.stored, "vi")
        self.assertIs(self.session._book_utterances(self.stored, "vi"), first)
        # Who reads and how fast do not change the words: still cached.
        self.settings.write_text(json.dumps({"voice": "adam", "rate": 1.4}), encoding="utf-8")
        self.assertIs(self.session._book_utterances(self.stored, "vi"), first)
        # A pronunciation does: rebuilt.
        self.settings.write_text(json.dumps({"voice": "adam", "pronunciations": {"Đoạn": "đoạn văn"}}), encoding="utf-8")
        self.assertIsNot(self.session._book_utterances(self.stored, "vi"), first)

    # RE-PLAY-034
    def test_opening_the_book_prepares_its_words_in_the_background(self):
        self.session._prepare_book(self.stored)
        deadline = time.time() + 5
        while not self.session._utterance_cache and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(len(self.session._utterance_cache), 1)

    def test_a_translated_reading_is_never_cached(self):
        self.session._book_utterances(self.stored, "en", translated={})
        self.assertEqual(self.session._utterance_cache, {})


if __name__ == "__main__":
    unittest.main()
