"""Highlights and notes made in the Reader (RE-NOTE-005 ... RE-NOTE-007).

Until 21/10/2026 every highlight came from Apple Books; this app could only
edit or remove them. These hold what making one here has to mean: it is
kept on this Mac under its own source, so the Books sync - a mirror that
replaces only Books' rows - never takes it away; it lands only on words the
paragraph really holds; and only a highlight made here can change colour.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.config import AppPaths
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.storage.repository import LibraryRepository, StoredAnnotation

from tests.domain.book_fixture import sample_book
from tests.headless.test_server import FakeEngine, run_server


class ReaderHighlightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        paths = AppPaths.create(Path(self.temp.name) / "data")
        self.repository = LibraryRepository(paths.database)
        self.addCleanup(self.repository.close)
        self.service = LibraryService(paths, self.repository)
        self.book = sample_book("tô màu")
        managed = paths.books / f"{self.book.id}.epub"
        managed.write_bytes(b"managed copy")
        self.repository.add_book(self.book, managed)
        self.first, self.second = (segment.id for segment in self.book.chapters[0].segments)

    def call(self, method: str, params: dict) -> dict:
        return run_server([{"id": 1, "method": method, "params": params}], FakeEngine(),
                          repository=self.repository, service=self.service)[0]

    # RE-NOTE-005, RE-NOTE-006
    def test_a_selection_over_two_paragraphs_is_kept_with_its_note_on_the_first(self) -> None:
        reply = self.call("annotations.add", {
            "book_id": self.book.id, "style": 1, "note": "  nhớ câu này ",
            "pieces": [{"segment_id": self.first, "selected_text": "chào."},
                       {"segment_id": self.second, "selected_text": "Tiếng Việt"}],
        })
        self.assertTrue(reply["ok"], reply)
        made = reply["result"]["annotations"]
        self.assertEqual([item["segment_id"] for item in made], [self.first, self.second])
        self.assertEqual([item["note"] for item in made], ["nhớ câu này", None])
        self.assertEqual({item["style"] for item in made}, {1})
        self.assertEqual({item["source"] for item in made}, {"readease"})
        self.assertEqual(len({item["id"] for item in made}), 2)

        opened = self.call("book.open", {"book_id": self.book.id})["result"]["annotations"]
        self.assertEqual([item["id"] for item in opened], [item["id"] for item in made])

    # RE-NOTE-005
    def test_the_books_sync_never_takes_a_highlight_made_here(self) -> None:
        mine = self.call("annotations.add", {
            "book_id": self.book.id,
            "pieces": [{"segment_id": self.first, "selected_text": "Xin chào."}],
        })["result"]["annotations"][0]
        self.assertEqual(mine["style"], 3)  # yellow, the colour every highlight wore
        self.repository.replace_annotations(self.book.id, "applebooks", [
            StoredAnnotation(id="AB-1", segment_id=self.second, selected_text="Tiếng Việt.",
                             source="applebooks"),
        ])
        self.repository.replace_annotations(self.book.id, "applebooks", [])
        kept = self.repository.annotations_for(self.book.id)
        self.assertEqual([item.id for item in kept], [mine["id"]])

    # RE-NOTE-005
    def test_words_the_paragraph_does_not_hold_are_refused_and_nothing_is_kept(self) -> None:
        for pieces in (
            [{"segment_id": self.first, "selected_text": "không có ở đây"}],
            [{"segment_id": "segment-of-another-book", "selected_text": "Xin chào."}],
            [{"segment_id": self.first, "selected_text": "Xin chào."},
             {"segment_id": self.second, "selected_text": "lạc đề"}],
        ):
            reply = self.call("annotations.add", {"book_id": self.book.id, "pieces": pieces})
            self.assertFalse(reply["ok"])
            self.assertEqual(reply["error"], "annotations:not_in_book")
        self.assertEqual(self.repository.annotations_for(self.book.id), ())
        self.assertFalse(self.call("annotations.add", {"book_id": "khong-co", "pieces": [
            {"segment_id": self.first, "selected_text": "Xin"}]})["ok"])
        self.assertFalse(self.call("annotations.add", {"book_id": self.book.id, "pieces": [
            {"segment_id": self.first, "selected_text": "Xin"}], "style": 9})["ok"])

    def test_curled_quotes_and_case_still_find_the_words(self) -> None:
        reply = self.call("annotations.add", {"book_id": self.book.id, "pieces": [
            {"segment_id": self.first, "selected_text": "XIN   chào"}]})
        self.assertTrue(reply["ok"], reply)

    # RE-NOTE-007
    def test_only_a_highlight_made_here_changes_colour(self) -> None:
        mine = self.call("annotations.add", {"book_id": self.book.id, "pieces": [
            {"segment_id": self.first, "selected_text": "Xin chào."}]})["result"]["annotations"][0]
        self.repository.replace_annotations(self.book.id, "applebooks", [
            StoredAnnotation(id="AB-1", segment_id=self.second, selected_text="Tiếng Việt.",
                             style=2, source="applebooks"),
        ])
        self.assertTrue(self.call("annotations.restyle", {
            "book_id": self.book.id, "annotation_id": mine["id"], "style": 4})["result"]["restyled"])
        self.assertFalse(self.call("annotations.restyle", {
            "book_id": self.book.id, "annotation_id": "AB-1", "style": 4})["result"]["restyled"])
        styles = {item.id: item.style for item in self.repository.annotations_for(self.book.id)}
        self.assertEqual(styles, {mine["id"]: 4, "AB-1": 2})
        self.assertFalse(self.call("annotations.restyle", {
            "book_id": self.book.id, "annotation_id": mine["id"], "style": 7})["ok"])

    def test_a_highlight_made_here_is_removed_and_edited_like_any_other(self) -> None:
        mine = self.call("annotations.add", {"book_id": self.book.id, "pieces": [
            {"segment_id": self.first, "selected_text": "Xin chào."}]})["result"]["annotations"][0]
        self.assertTrue(self.call("annotations.update", {
            "book_id": self.book.id, "annotation_id": mine["id"], "note": "sửa"})["result"]["updated"])
        self.assertEqual(self.repository.annotations_for(self.book.id)[0].note, "sửa")
        self.assertTrue(self.call("annotations.delete", {
            "book_id": self.book.id, "annotation_id": mine["id"]})["result"]["removed"])
        self.assertEqual(self.repository.annotations_for(self.book.id), ())


if __name__ == "__main__":
    unittest.main()
