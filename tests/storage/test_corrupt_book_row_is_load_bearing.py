"""Why one unreadable `books` row cannot simply be skipped - and what the
shelf does instead.

Turn 7 of the hardening campaign fixed the neighbouring case: a corrupt
`progress` row used to answer "thư viện hỏng" for the whole shelf, and now
costs that book its place instead of the library. The obvious next move was
to do the same for a corrupt `document_json` - `list_books()` builds the
whole tuple in one comprehension, so one bad row took every book down.

Measured on a temporary data root (08/09, 01:2x): a silent skip would not
have been a strict improvement. The corrupt row stays LOAD-BEARING after it
stops being readable - it keeps its `id` PRIMARY KEY, its UNIQUE
`source_hash` and its UNIQUE `managed_path`, and `add_book` is a plain
INSERT. Skip it silently and the book becomes a ghost: not on the shelf, so
nothing to click and nothing to delete; and the same file cannot be imported
again, because the row it collides with is one the shelf denies exists.

So the shelf does not skip. `list_shelf()` hands the row back as a
`DamagedBook`, the server lists it with `damaged: true`, the shell draws it
as a card that cannot be opened and names the way out - remove it, or import
the original file again, which heals the row in place. `list_books()` stays
strict for callers that need whole books. The first two tests pin the facts
that made the skip a trap; the rest prove the two ways out.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.importers.epub_fixture import make_epub

from vieneu_reader.config import AppPaths
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.storage.errors import RepositoryError
from vieneu_reader.storage.repository import (
    DamagedBook,
    LibraryRepository,
    StoredBook,
)


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

    def test_one_unreadable_book_row_still_takes_the_strict_list_down(self) -> None:
        """`list_books` is for callers that need whole books; for them a
        shorter list would be a lie. The healthy sibling is still readable
        one at a time, so the loss is the comprehension, not the data."""

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

    def test_the_shelf_lists_the_damaged_row_beside_the_healthy_one(self) -> None:
        shelf = self.repository.list_shelf()

        by_id = {item.id if isinstance(item, DamagedBook) else item.book.id: item
                 for item in shelf}
        self.assertIsInstance(by_id[self.healthy.book.id], StoredBook)
        damaged = by_id[self.damaged.book.id]
        self.assertIsInstance(damaged, DamagedBook)
        self.assertEqual(damaged.title, "Cuốn hỏng")
        self.assertEqual(damaged.source_format, "epub")
        self.assertEqual(damaged.managed_path, self.damaged.managed_path)

    def test_a_damaged_book_can_be_removed_and_takes_its_copy_with_it(self) -> None:
        """The first way out. `remove_book` used to go through `get_book`,
        which raised on this row - the trash button on a damaged card would
        have failed the same way the shelf used to."""

        managed = self.damaged.managed_path
        self.assertTrue(managed.exists())

        self.assertTrue(self.service.remove_book(self.damaged.book.id))

        self.assertFalse(managed.exists())
        self.assertEqual(
            [item.book.id for item in self.repository.list_books()],
            [self.healthy.book.id],
        )

    def test_importing_the_same_file_again_heals_the_row(self) -> None:
        """The second way out, and the one the card's hint names. The file
        on disk was never the problem; the dedup read that refused it was."""

        healed = self.service.import_book(self.sources / "damaged.epub")

        self.assertEqual(healed.book.id, self.damaged.book.id)
        self.assertFalse(healed.was_existing)
        self.assertEqual(healed.book.title, "Cuốn hỏng")
        # Whole again: the strict list works, and the row decodes.
        titles = sorted(item.book.title for item in self.repository.list_books())
        self.assertEqual(titles, ["Cuốn hỏng", "Cuốn lành"])
        self.assertTrue(healed.managed_path.exists())

    def test_healing_keeps_the_readers_decisions_about_its_highlights(self) -> None:
        """Same id, same decisions: the reason schema v2 came first."""

        self.repository.forget_annotation(self.damaged.book.id, "hl-2")

        self.service.import_book(self.sources / "damaged.epub")

        with self.repository._connection:
            rows = self.repository._connection.execute(
                "SELECT annotation_id FROM annotations_forgotten WHERE book_id = ?",
                (self.damaged.book.id,),
            ).fetchall()
        self.assertEqual([row[0] for row in rows], ["hl-2"])


if __name__ == "__main__":
    unittest.main()
