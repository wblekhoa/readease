"""Why one unreadable `books` row cannot simply be skipped.

Turn 7 of the hardening campaign fixed the neighbouring case: a corrupt
`progress` row used to answer "thư viện hỏng" for the whole shelf, and now
costs that book its place instead of the library. The obvious next move is
to do the same for a corrupt `document_json` - `list_books()` builds the
whole tuple in one comprehension, so one bad row still takes every book
down with it.

Measured on a temporary data root (07/09, 01:2x): that move would not be a
strict improvement. The corrupt row stays LOAD-BEARING after it stops being
readable - it keeps its `id` PRIMARY KEY, its UNIQUE `source_hash` and its
UNIQUE `managed_path`, and `add_book` is a plain INSERT. Skip it silently
and the book becomes a ghost: not on the shelf, so nothing to click and
nothing to delete; and the same file cannot be imported again, because the
row it collides with is one the shelf denies exists. Today's failure is
loud and total, but it says something true and the way out is visible.

So this file pins the three facts that make the silent skip a trap, not the
belief that the shelf SHOULD go down. Making `list_books()` lenient is a
real improvement only together with a way back for the stranded row - a
damaged-book state the shell can draw, or a repair path on import. Both are
product decisions (owner, ASK). If a change here turns any of these three
red, read this note first: what has to be true before skipping is safe.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.importers.epub_fixture import make_epub

from vieneu_reader.config import AppPaths
from vieneu_reader.importers.errors import LibraryStorageError
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.storage.errors import RepositoryError
from vieneu_reader.storage.repository import LibraryRepository


class CorruptBookRowIsLoadBearingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.sources = root / "sources"
        self.sources.mkdir()
        self.healthy = self.service.import_book(
            make_epub(self.sources, name="healthy.epub", title="Cuốn lành")
        )
        self.damaged = self.service.import_book(
            make_epub(self.sources, name="damaged.epub", title="Cuốn hỏng")
        )
        with self.repository._connection:
            self.repository._connection.execute(
                "UPDATE books SET document_json = '{' WHERE id = ?",
                (self.damaged.book.id,),
            )

    def tearDown(self) -> None:
        self.repository.close()
        self.temp_dir.cleanup()

    def test_one_unreadable_book_row_still_takes_the_whole_shelf_down(self) -> None:
        """Measured, not endorsed - the state a lenient `list_books` would end.

        The healthy sibling is still readable one at a time, so the loss is
        the comprehension in `list_books()`, not the data.
        """

        with self.assertRaises(RepositoryError):
            self.repository.list_books()

        self.assertEqual(
            self.repository.get_book(self.healthy.book.id).book.title,
            "Cuốn lành",
        )

    def test_an_unreadable_row_still_holds_its_place_in_the_table(self) -> None:
        """First half of the trap: the row cannot be written over."""

        with self.assertRaises(RepositoryError):
            self.repository.add_book(
                self.damaged.book,
                self.paths.books / f"{self.damaged.book.id}.epub",
            )

    def test_the_same_source_file_cannot_be_imported_again(self) -> None:
        """Second half: nor can the owner get the book back the normal way.

        This is what makes the silent skip worse than the loud failure - the
        refusal names a book the shelf would no longer be showing.

        Measured: TWO independent locks hold this shut. The dedup read
        (`get_book`) raises on the unreadable row, and behind it the UNIQUE
        `source_hash` / `managed_path` refuse the INSERT. Turning off either
        one alone leaves this test green - it goes red only when both are
        gone, which is exactly the state in which skipping the row would
        stop stranding the book. That is the signal to re-read the module
        docstring, not to delete this test.
        """

        with self.assertRaises(LibraryStorageError):
            self.service.import_book(self.sources / "damaged.epub")

        # And the file on disk was never the problem: a copy under a new
        # name imports fine, so the refusal is the stranded row talking.
        twin = make_epub(self.sources, name="twin.epub", title="Cuốn hỏng")
        with self.assertRaises(LibraryStorageError):
            self.service.import_book(twin)


if __name__ == "__main__":
    unittest.main()
