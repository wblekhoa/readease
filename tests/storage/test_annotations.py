"""What the person did here beats what the mirror says.

`replace_annotations` is a mirror: one sync's highlights for one book,
replaced wholesale, so a highlight deleted in Apple Books disappears here
too. That is right, and it is also the mechanism by which every local act
gets quietly undone - the next sync writes the other side's version over it.

Two local acts have to survive that, and they are opposites:

  * a highlight REMOVED here must stay removed  (tombstone)
  * a note REWRITTEN here must stay rewritten   (edit)

Neither was testable from the outside before the edit existed - the
tombstone had no test at all, which is how a wholesale-replace can be
written twice and get it wrong the second time. Both live here, sharing a
sync, because the case that actually breaks is the two of them meeting on
one id.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.config import AppPaths
from vieneu_reader.storage.repository import LibraryRepository, StoredAnnotation

from tests.domain.book_fixture import sample_book

APPLE = "applebooks"


def highlight(identifier: str, note: str | None = None) -> StoredAnnotation:
    return StoredAnnotation(
        id=identifier,
        segment_id="segment-0",
        selected_text="Một câu đã tô.",
        note=note,
        style=0,
        source=APPLE,
    )


class AnnotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.paths = AppPaths.create(Path(self.temp_dir.name) / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.book = sample_book("ghi chú")
        managed = self.paths.books / f"{self.book.id}.epub"
        managed.write_bytes(b"managed copy")
        self.repository.add_book(self.book, managed)

    def tearDown(self) -> None:
        self.repository.close()
        self.temp_dir.cleanup()

    def sync(self, *items: StoredAnnotation) -> None:
        self.repository.replace_annotations(self.book.id, APPLE, items)

    def notes(self) -> dict[str, str | None]:
        return {
            item.id: item.note
            for item in self.repository.annotations_for(self.book.id)
        }

    # --- the mirror itself -------------------------------------------------

    def test_a_sync_is_a_mirror_of_the_other_side(self) -> None:
        self.sync(highlight("a"), highlight("b"))
        self.sync(highlight("a"))
        self.assertEqual(set(self.notes()), {"a"})

    # --- removed here stays removed ---------------------------------------

    def test_a_highlight_removed_here_is_not_handed_back_by_the_next_sync(self) -> None:
        # Owner, 03/09: "xoá hẳn luôn". Without the tombstone the mirror
        # restores it within seconds and the delete button looks broken.
        self.sync(highlight("a"), highlight("b"))
        self.assertTrue(self.repository.forget_annotation(self.book.id, "a"))
        self.sync(highlight("a"), highlight("b"))
        self.assertEqual(set(self.notes()), {"b"})

    def test_removing_one_that_is_already_gone_says_so(self) -> None:
        self.assertFalse(self.repository.forget_annotation(self.book.id, "ghost"))

    # --- rewritten here stays rewritten ------------------------------------

    def test_a_note_written_here_survives_the_next_sync(self) -> None:
        self.sync(highlight("a", "ghi chú của Apple"))
        self.assertTrue(
            self.repository.edit_annotation(self.book.id, "a", "chữ của tôi")
        )
        self.assertEqual(self.notes()["a"], "chữ của tôi")

        self.sync(highlight("a", "ghi chú của Apple"))
        self.assertEqual(self.notes()["a"], "chữ của tôi")

    def test_it_survives_a_second_sync_and_a_second_edit(self) -> None:
        # The edit record is updated in place, not stacked: a second edit
        # that left the first one lying around would resurrect it later.
        self.sync(highlight("a", "gốc"))
        self.repository.edit_annotation(self.book.id, "a", "lần một")
        self.sync(highlight("a", "gốc"))
        self.repository.edit_annotation(self.book.id, "a", "lần hai")
        self.sync(highlight("a", "gốc"))
        self.assertEqual(self.notes()["a"], "lần hai")

    def test_a_note_can_be_taken_back_and_stays_taken_back(self) -> None:
        # Clearing is a real answer, not a no-op: emptying the box and
        # having the old words return on the next sync reads as data loss.
        self.sync(highlight("a", "ghi chú của Apple"))
        self.assertTrue(self.repository.edit_annotation(self.book.id, "a", "   "))
        self.assertIsNone(self.notes()["a"])
        self.sync(highlight("a", "ghi chú của Apple"))
        self.assertIsNone(self.notes()["a"])

    def test_a_note_can_be_added_to_a_highlight_that_never_had_one(self) -> None:
        self.sync(highlight("a"))
        self.repository.edit_annotation(self.book.id, "a", "của riêng tôi")
        self.sync(highlight("a"))
        self.assertEqual(self.notes()["a"], "của riêng tôi")

    def test_an_edit_touches_only_the_one_it_names(self) -> None:
        self.sync(highlight("a", "gốc a"), highlight("b", "gốc b"))
        self.repository.edit_annotation(self.book.id, "a", "sửa a")
        self.sync(highlight("a", "gốc a"), highlight("b", "gốc b"))
        self.assertEqual(self.notes(), {"a": "sửa a", "b": "gốc b"})

    def test_editing_one_that_is_gone_says_so_and_writes_nothing(self) -> None:
        # An edit record for a row that cannot exist is rot: it would sit
        # in the table forever, and re-apply itself if the id came back.
        self.assertFalse(self.repository.edit_annotation(self.book.id, "ghost", "x"))
        self.sync(highlight("ghost", "gốc"))
        self.assertEqual(self.notes()["ghost"], "gốc")

    # --- the two of them meeting on one id ---------------------------------

    def test_removing_beats_editing_and_the_edit_does_not_resurrect_it(self) -> None:
        self.sync(highlight("a", "gốc"))
        self.repository.edit_annotation(self.book.id, "a", "chữ của tôi")
        self.assertTrue(self.repository.forget_annotation(self.book.id, "a"))
        self.sync(highlight("a", "gốc"))
        self.assertEqual(self.notes(), {})

    def test_an_edit_after_a_removal_is_refused(self) -> None:
        self.sync(highlight("a", "gốc"))
        self.repository.forget_annotation(self.book.id, "a")
        self.assertFalse(self.repository.edit_annotation(self.book.id, "a", "về đi"))
        self.sync(highlight("a", "gốc"))
        self.assertEqual(self.notes(), {})

    # --- other books are other books ---------------------------------------

    def test_an_edit_belongs_to_one_book(self) -> None:
        other = sample_book("sách khác")
        managed = self.paths.books / f"{other.id}.epub"
        managed.write_bytes(b"managed copy")
        self.repository.add_book(other, managed)

        self.sync(highlight("a", "gốc"))
        self.repository.edit_annotation(self.book.id, "a", "chữ của tôi")
        self.repository.replace_annotations(other.id, APPLE, (highlight("a", "gốc"),))

        self.assertEqual(
            [item.note for item in self.repository.annotations_for(other.id)],
            ["gốc"],
        )


if __name__ == "__main__":
    unittest.main()
