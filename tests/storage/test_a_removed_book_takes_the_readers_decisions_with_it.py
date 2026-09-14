"""A promise the app makes in writing, and the one flow that breaks it.

Deleting a single highlight asks `notes.remove_confirm`: **"Xoá hẳn, đồng bộ
lại cũng không quay về?"** - delete for good, even on a re-sync. That promise
is kept by two tables: `annotations_forgotten` remembers the deletion so the
next Apple Books sync cannot put the highlight back, and `annotations_edited`
remembers the reader's own words so the sync cannot overwrite them with the
ones the highlight arrived with. Both mechanisms are deliberate; their
docstrings in `repository.py` say why.

Until schema v2 both tables were `REFERENCES books(id) ON DELETE CASCADE`,
so removing the BOOK deleted the reader's DECISIONS about its highlights -
not just the book. Measured 10/09 on a temporary data root, importing the
same file again (the id is content-derived, so it is the same book) and
syncing once:

    before  hl-1 -> 'LỜI CỦA TÔI, tôi tự viết'   hl-2 -> gone
    after   hl-1 -> 'ghi chú GỐC từ Apple Books'  hl-2 -> back

The reader asked to remove a book. They did not ask to un-delete a highlight
they had deleted for good, and they certainly did not ask to have their own
note replaced by Apple Books' text.

Schema v2 (the first entry in `_MIGRATIONS`) rebuilds both tables without the
foreign key, so a decision outlives the book row it is about. These tests
prove the promise through the service: remove, import the same file, sync.
The migration of a real v1 store is proven in `test_repository.py`.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.importers.epub_fixture import make_epub

from vieneu_reader.config import AppPaths
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.storage.repository import LibraryRepository, StoredAnnotation

#: What Apple Books hands over, both times it is asked.
APPLE_BOOKS_SAYS = (
    ("hl-1", "câu được tô", "ghi chú gốc từ Apple Books"),
    ("hl-2", "câu thứ hai", "ghi chú thứ hai"),
)

MY_OWN_WORDS = "Lời của tôi, tôi tự viết."


class ARemovedBookTakesTheReadersDecisionsWithItTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        sources = root / "sources"
        sources.mkdir()
        self.epub = make_epub(sources, name="sach.epub", title="Cuốn có ghi chú")

        stored = self.service.import_book(self.epub)
        self.book_id = stored.book.id
        segment = stored.book.chapters[0].segments[0].id
        self.from_apple_books = tuple(
            StoredAnnotation(item_id, segment, selected, note)
            for item_id, selected, note in APPLE_BOOKS_SAYS
        )

        self._sync()
        # The two decisions this file is about, both made in this app.
        self.repository.edit_annotation(self.book_id, "hl-1", MY_OWN_WORDS)
        self.repository.forget_annotation(self.book_id, "hl-2")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _sync(self) -> None:
        self.repository.replace_annotations(
            self.book_id, "applebooks", self.from_apple_books
        )

    def _notes(self) -> dict[str, str | None]:
        return {
            item.id: item.note
            for item in self.repository.annotations_for(self.book_id)
        }

    def _remove_and_import_the_same_file_again(self) -> None:
        self.service.remove_book(self.book_id)
        again = self.service.import_book(self.epub)
        self.assertEqual(
            again.book.id, self.book_id, "cùng một file phải cho cùng một book id"
        )
        self._sync()

    def test_both_decisions_survive_an_ordinary_sync(self) -> None:
        """The mechanism works. This one is GREEN - it is here so a failure
        below cannot be blamed on the guard never having worked at all."""

        self._sync()

        self.assertEqual(self._notes(), {"hl-1": MY_OWN_WORDS})

    def test_a_highlight_deleted_for_good_stays_deleted_across_a_reimport(self) -> None:
        self._remove_and_import_the_same_file_again()

        self.assertNotIn(
            "hl-2",
            self._notes(),
            "highlight người đọc đã xoá hẳn quay lại sau khi nhập lại sách",
        )

    def test_the_readers_own_words_survive_a_reimport(self) -> None:
        self._remove_and_import_the_same_file_again()

        self.assertEqual(
            self._notes().get("hl-1"),
            MY_OWN_WORDS,
            "ghi chú người đọc tự viết bị Apple Books ghi đè sau khi nhập lại",
        )


if __name__ == "__main__":
    unittest.main()
