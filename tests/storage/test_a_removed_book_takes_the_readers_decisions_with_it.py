"""A promise the app makes in writing, and the one flow that breaks it.

Deleting a single highlight asks `notes.remove_confirm`: **"Xoá hẳn, đồng bộ
lại cũng không quay về?"** - delete for good, even on a re-sync. That promise
is kept by two tables: `annotations_forgotten` remembers the deletion so the
next Apple Books sync cannot put the highlight back, and `annotations_edited`
remembers the reader's own words so the sync cannot overwrite them with the
ones the highlight arrived with. Both mechanisms are deliberate; their
docstrings in `repository.py` say why.

Both tables are `REFERENCES books(id) ON DELETE CASCADE`. So removing the
BOOK deletes the reader's DECISIONS about its highlights - not just the book.
Measured 10/09 on a temporary data root, importing the same file again (the
id is content-derived, so it is the same book) and syncing once:

    before  hl-1 -> 'LỜI CỦA TÔI, tôi tự viết'   hl-2 -> gone
    after   hl-1 -> 'ghi chú GỐC từ Apple Books'  hl-2 -> back

The reader asked to remove a book. They did not ask to un-delete a highlight
they had deleted for good, and they certainly did not ask to have their own
note replaced by Apple Books' text. Nothing on screen said either would
happen; `library.remove_confirm` now names the cost, which keeps the app
honest but does not make the promise true again.

**These tests are RED on purpose and opt-in**, so the suite neither pretends
the gap is fixed nor goes red on every run for something only the owner can
authorise. Run them with:

    VIENEU_READER_KNOWN_GAPS=1 .venv/bin/python -m unittest \
        tests.storage.test_a_removed_book_takes_the_readers_decisions_with_it

The fix is to drop `ON DELETE CASCADE` from those two tables so a decision
outlives the book row it is about. SQLite cannot ALTER a foreign key away, so
it is a table rebuild - `SCHEMA_VERSION` 1 -> 2 and the FIRST entry ever put
in `_MIGRATIONS`, which is empty today. The ladder that would run it is built
and tested (one transaction, manual BEGIN so DDL rolls back, refuse-newer),
but has never carried a real library. That is a migration, and migrations are
the owner's call - hence red-and-parked rather than fixed here.

When it lands, delete the skip and these become ordinary tests.
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.importers.epub_fixture import make_epub

from vieneu_reader.config import AppPaths
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.storage.repository import LibraryRepository, StoredAnnotation

KNOWN_GAPS = os.environ.get("VIENEU_READER_KNOWN_GAPS") == "1"

#: What Apple Books hands over, both times it is asked.
APPLE_BOOKS_SAYS = (
    ("hl-1", "câu được tô", "ghi chú gốc từ Apple Books"),
    ("hl-2", "câu thứ hai", "ghi chú thứ hai"),
)

MY_OWN_WORDS = "Lời của tôi, tôi tự viết."


@unittest.skipUnless(KNOWN_GAPS, "known gap, owner decision pending - see docstring")
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
