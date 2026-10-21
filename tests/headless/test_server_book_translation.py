"""A library book read in translation (RE-PLAY-032): the engine keeps what
the host translated, paragraph by paragraph, and speaks it."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from vieneu_reader.domain.models import BookDocument
from vieneu_reader.headless.server import serve
from vieneu_reader.storage.repository import LibraryRepository, Progress
from vieneu_reader.storage.translations import TranslationStore
from dataclasses import replace

from tests.headless.test_server import BOOK_ID, FakeEngine, build_book


def book() -> BookDocument:
    """Two chapters; the first opens with ONE paragraph split in two pieces."""
    built = build_book([
        ("Một", [("Câu một của đoạn dài,", "paragraph"), ("phần sau của nó.", "paragraph"), ("Đoạn hai.", "paragraph")]),
        ("Hai", [("Đoạn ba.", "paragraph")]),
    ])
    first = built.chapters[0]
    segments = list(first.segments)
    segments[1] = replace(segments[1], joint="split")
    return replace(built, chapters=(replace(first, segments=tuple(segments)),) + built.chapters[1:])


class BookTranslationTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.repository = LibraryRepository(root / "reader.sqlite3")
        self.addCleanup(self.repository.close)
        self.book = book()
        source = root / "book.epub"
        source.write_bytes(b"fixture")
        self.repository.add_book(self.book, source)
        self.store = TranslationStore(root / "translations.sqlite3")
        self.addCleanup(self.store.close)
        self.ids = [s.id for c in self.book.chapters for s in c.segments]

    def run_(self, requests, engine=None):
        reader = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
        writer = io.StringIO()
        serve(reader, writer, engine or FakeEngine(chunks_per_sentence=1),
              repository=self.repository, translations=self.store)
        return [json.loads(line) for line in writer.getvalue().splitlines()]

    # RE-PLAY-032
    def test_paragraphs_join_their_pieces_and_say_what_is_already_translated(self):
        self.store.put(BOOK_ID, "en", "x", {self.ids[2]: "Paragraph two."})
        reply = self.run_([{"id": 1, "method": "translation.paragraphs",
                            "params": {"book_id": BOOK_ID, "target": "en", "chapters": 1}}])[0]["result"]
        self.assertEqual(reply["chapters"], [{"chapter": 0, "paragraphs": [
            {"segment_id": self.ids[0], "text": "Câu một của đoạn dài, phần sau của nó.", "translated": False},
            {"segment_id": self.ids[2], "text": "Đoạn hai.", "translated": True},
        ]}])

    # RE-PLAY-032
    def test_a_translated_reading_speaks_the_translations_and_keeps_the_books_voice(self):
        self.repository.save_progress(Progress(book_id=BOOK_ID, segment_id=self.ids[0], playback_rate=1.0, voice_id="adam"))
        engine = FakeEngine(chunks_per_sentence=1)
        replies = self.run_([
            {"id": 1, "method": "translation.put", "params": {"book_id": BOOK_ID, "target": "en", "provider": "readease",
             "items": {self.ids[0]: "The first long paragraph.", self.ids[2]: "Paragraph two.", "not-a-paragraph": "x"}}},
            {"id": 2, "method": "read.book", "params": {"book_id": BOOK_ID, "voice_id": "af_heart", "chapters": 1,
             "translation": {"target": "en"}}},
        ], engine)
        self.assertEqual(replies[0]["result"], {"kept": 2})
        self.assertEqual([t for t, _ in engine.requests], ["The first long paragraph.", "Paragraph two."])
        self.assertEqual({v for _, v in engine.requests}, {"af_heart"})
        positions = [r["segment_id"] for r in replies if r.get("event") == "position"]
        self.assertEqual(positions, [self.ids[0], self.ids[2]])
        for segment_id in positions:
            self.run_([{"id": 3, "method": "progress.reached", "params": {"id": 2, "segment_id": segment_id}}])
        saved = self.repository.load_progress(BOOK_ID)
        self.assertEqual(saved.voice_id, "adam")

    # RE-PLAY-032
    def test_the_reading_stops_at_the_first_paragraph_not_yet_translated(self):
        self.store.put(BOOK_ID, "en", "x", {self.ids[0]: "The first."})
        engine = FakeEngine(chunks_per_sentence=1)
        replies = self.run_([{"id": 2, "method": "read.book", "params": {
            "book_id": BOOK_ID, "voice_id": "af_heart", "chapters": 1, "translation": {"target": "en"}}}], engine)
        self.assertTrue(replies[-1]["ok"])
        self.assertEqual([t for t, _ in engine.requests], ["The first."])

    # RE-PLAY-032
    def test_nothing_translated_where_it_starts_is_refused_by_name(self):
        replies = self.run_([{"id": 2, "method": "read.book", "params": {
            "book_id": BOOK_ID, "voice_id": "af_heart", "chapters": 1, "translation": {"target": "en"}}}])
        self.assertFalse(replies[-1]["ok"])
        self.assertIn("translation:missing", replies[-1]["error"])

    # RE-PLAY-032
    def test_list_and_clear(self):
        self.store.put(BOOK_ID, "vi", "x", {self.ids[3]: "Ba."})
        replies = self.run_([
            {"id": 1, "method": "translation.list", "params": {"book_id": BOOK_ID, "target": "vi"}},
            {"id": 2, "method": "translation.clear", "params": {"book_id": BOOK_ID}},
            {"id": 3, "method": "translation.list", "params": {"book_id": BOOK_ID, "target": "vi"}},
        ])
        self.assertEqual(replies[0]["result"]["items"], {self.ids[3]: "Ba."})
        self.assertEqual(replies[1]["result"], {"deleted": 1})
        self.assertEqual(replies[2]["result"]["items"], {})


if __name__ == "__main__":
    unittest.main()


class RemovingABookTakesItsTranslationsTests(unittest.TestCase):
    # RE-PLAY-032
    def test_library_remove_deletes_the_books_translations(self):
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = AppPaths.create(root / "app")
            repository = LibraryRepository(paths.database)
            self.addCleanup(repository.close)
            store = TranslationStore(root / "translations.sqlite3")
            self.addCleanup(store.close)
            source = root / "a.md"
            source.write_text("# A\n\nMột đoạn.", encoding="utf-8")
            imported = LibraryService(paths, repository).import_book(source).book
            segment = imported.chapters[0].segments[0].id
            store.put(imported.id, "en", "x", {segment: "A paragraph."})
            store.put("another-book", "en", "x", {"p": "Kept."})
            reader = io.StringIO(json.dumps({"id": 1, "method": "library.remove", "params": {"book_id": imported.id}}) + "\n")
            writer = io.StringIO()
            serve(reader, writer, FakeEngine(chunks_per_sentence=1), repository=repository,
                  service=LibraryService(paths, repository), translations=store)
            self.assertEqual(json.loads(writer.getvalue().splitlines()[-1])["result"], {"removed": True})
            self.assertEqual(store.get(imported.id, "en"), {})
            self.assertEqual(store.get("another-book", "en"), {"p": "Kept."})
