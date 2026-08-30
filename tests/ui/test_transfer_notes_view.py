from __future__ import annotations

import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from vieneu_reader.integrations.apple_books import (
    Annotation,
    Book,
    TransferItem,
    TransferPlan,
)
from vieneu_reader.ui.i18n import Localizer
from vieneu_reader.ui.transfer_notes_view import TransferNotesView

SOURCE = Book("SRC", "Bản một", "urn:uuid:same", 0.30)
TARGET = Book("DST", "Bản hai", "urn:uuid:same", 0.60)


def _plan(count: int) -> TransferPlan:
    items = tuple(
        TransferItem(
            annotation=Annotation(
                asset_id="SRC",
                kind=2,
                location=f"epubcfi(/6/26!/4/{index})",
                selected_text="đoạn được bôi",
                note="ghi chú" if index % 2 else None,
            ),
            verdict="same-edition",
        )
        for index in range(count)
    )
    return TransferPlan(source=SOURCE, target=TARGET, items=items)


class TransferNotesViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _view(self) -> TransferNotesView:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        return view

    def test_it_starts_empty_and_cannot_preview_yet(self) -> None:
        view = self._view()
        self.assertEqual(view.plan_table.rowCount(), 0)
        self.assertFalse(view.preview_button.isEnabled())

    def test_choosing_two_different_books_enables_preview(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        self.assertEqual(view.source_selector.count(), 2)
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        self.assertTrue(view.preview_button.isEnabled())

    def test_the_same_book_on_both_sides_is_refused(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(0)
        self.assertFalse(view.preview_button.isEnabled())

    def test_asking_for_a_preview_names_both_books(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        seen: list[tuple[str, str]] = []
        view.previewRequested.connect(lambda a, b: seen.append((a, b)))
        view.preview_button.click()
        self.assertEqual(seen, [("SRC", "DST")])

    def test_a_plan_fills_one_row_per_annotation(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.show_plan(_plan(5))
        self.assertEqual(view.plan_table.rowCount(), 5)
        self.assertIn("5", view.summary_label.text())

    def test_a_book_with_no_notes_says_so_instead_of_showing_an_empty_grid(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.show_plan(_plan(0))
        self.assertEqual(view.plan_table.rowCount(), 0)
        self.assertTrue(view.summary_label.text().strip())

    def test_apple_books_being_unavailable_is_a_state_not_a_crash(self) -> None:
        view = self._view()
        view.show_unavailable("Không tìm thấy dữ liệu Apple Books trên máy này.")
        self.assertEqual(view.plan_table.rowCount(), 0)
        self.assertIn("Apple Books", view.summary_label.text())
        self.assertFalse(view.preview_button.isEnabled())

    def test_the_table_and_selectors_are_reachable_without_sight(self) -> None:
        view = self._view()
        for widget in (view.plan_table, view.source_selector, view.target_selector):
            self.assertTrue(
                widget.accessibleName().strip(),
                f"{widget.objectName()} needs an accessible name",
            )

    def test_the_persons_own_words_are_shown_but_never_the_raw_repr(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.show_plan(_plan(2))
        cell = view.plan_table.item(0, 1)
        self.assertIsNotNone(cell)
        self.assertNotIn("Annotation(", cell.text())


if __name__ == "__main__":
    unittest.main()



class TransferNotesRenderingTests(unittest.TestCase):
    """What the table actually says - the part a person reads."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _view(self) -> TransferNotesView:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        view.set_books((SOURCE, TARGET))
        return view

    def test_a_same_edition_row_says_it_carries_over(self) -> None:
        view = self._view()
        view.show_plan(_plan(1))
        self.assertEqual(view.plan_table.item(0, 2).text(), "Chuyển được nguyên vẹn")

    def test_a_row_that_cannot_carry_over_says_why(self) -> None:
        """"Needs checking" hid the reason; the chapter differing is the reason."""

        view = self._view()
        other = Book("OTHER", "Bản khác", "urn:uuid:different", 0.1)
        items = tuple(
            TransferItem(annotation=item.annotation, verdict="needs-review")
            for item in _plan(1).items
        )
        view.show_plan(TransferPlan(source=SOURCE, target=other, items=items))
        self.assertEqual(view.plan_table.item(0, 2).text(), "Chương này khác nhau")
        self.assertFalse(
            view.transfer_button.isEnabled(), "offered to copy a position it cannot vouch for"
        )
        self.assertIn("khác nhau", view.summary_label.text())

    def test_each_row_is_labelled_from_its_own_annotation(self) -> None:
        """A set comparison would pass with the two labels swapped."""
        plan = _plan(2)
        view = self._view()
        view.show_plan(plan)
        for row, item in enumerate(plan.items):
            expected = "Ghi chú" if item.annotation.has_note else "Đoạn bôi màu"
            self.assertEqual(
                view.plan_table.item(row, 0).text(),
                expected,
                f"row {row} has_note={item.annotation.has_note}",
            )

    def test_a_long_plan_is_truncated_and_says_so(self) -> None:
        view = self._view()
        view.show_plan(_plan(250))
        self.assertEqual(view.plan_table.rowCount(), 200)
        self.assertIn("250", view.summary_label.text())
        self.assertIn("200", view.summary_label.text())

    def test_becoming_unavailable_clears_what_was_on_screen(self) -> None:
        view = self._view()
        view.show_plan(_plan(3))
        self.assertEqual(view.plan_table.rowCount(), 3)
        view.show_unavailable("Không đọc được.")
        self.assertEqual(view.plan_table.rowCount(), 0)

    def test_reopening_the_tab_does_not_leave_the_last_book_on_screen(self) -> None:
        view = self._view()
        view.show_plan(_plan(3))
        view.set_books((SOURCE, TARGET))
        self.assertEqual(view.plan_table.rowCount(), 0)

    def test_a_failed_preview_can_be_retried(self) -> None:
        view = self._view()
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.show_unavailable("Không đọc được cuốn này.")
        self.assertTrue(
            view.preview_button.isEnabled(),
            "books are still listed, so the person must be able to try again",
        )

    def test_two_copies_of_one_book_can_be_told_apart(self) -> None:
        twin = Book("DST", "Bản một", "urn:uuid:same", 0.30)
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        view.set_books((SOURCE, twin))
        labels = {
            view.source_selector.itemText(index)
            for index in range(view.source_selector.count())
        }
        self.assertEqual(len(labels), 2, "identical labels leave no way to choose")

    def test_the_table_cannot_be_edited(self) -> None:
        view = self._view()
        view.show_plan(_plan(1))
        self.assertFalse(
            view.plan_table.item(0, 1).flags() & Qt.ItemFlag.ItemIsEditable
        )


class TransferNotesReadabilityTests(unittest.TestCase):
    """What the screen actually communicates, as opposed to what it contains."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _view(self) -> TransferNotesView:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        return view

    @staticmethod
    def _annotation(kind: int, selected: str | None, note: str | None) -> Annotation:
        return Annotation(
            asset_id="SRC",
            kind=kind,
            location="epubcfi(/6/26!/4/1)",
            selected_text=selected,
            note=note,
        )

    def _single(self, annotation: Annotation) -> TransferPlan:
        return TransferPlan(
            source=SOURCE,
            target=TARGET,
            items=(TransferItem(annotation=annotation, verdict="same-edition"),),
        )

    def test_a_bookmark_is_not_called_a_highlight(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.show_plan(self._single(self._annotation(3, None, None)))
        self.assertEqual(view.plan_table.item(0, 0).text(), "Đánh dấu trang")

    def test_an_entry_with_no_text_says_so_instead_of_showing_a_blank(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.show_plan(self._single(self._annotation(3, None, None)))
        self.assertTrue(
            view.plan_table.item(0, 1).text().strip(),
            "a blank cell reads as a bug, not as an entry without text",
        )

    def test_what_tells_two_copies_apart_survives_a_narrow_dropdown(self) -> None:
        """The titles are long and identical; a suffix is cut off before it is read."""
        first = Book("A", "Đừng bắt tôi phải suy nghĩ! — Tái bản", "urn:uuid:x", 0.30)
        second = Book("B", "Đừng bắt tôi phải suy nghĩ! — Tái bản", "urn:uuid:x", 0.60)
        view = self._view()
        view.set_books((first, second))
        labels = [
            view.source_selector.itemText(index)
            for index in range(view.source_selector.count())
        ]
        prefixes = {label[:14] for label in labels}
        self.assertEqual(
            len(prefixes), 2, f"first 14 characters must already differ: {labels}"
        )


class TransferPermissionTests(unittest.TestCase):
    """Copying is allowed only for the exact pair someone previewed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _armed_view(self) -> TransferNotesView:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.show_plan(_plan(3))
        return view

    def test_nothing_can_be_copied_before_a_preview(self) -> None:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        self.assertTrue(view.preview_button.isEnabled())
        self.assertFalse(
            view.transfer_button.isEnabled(),
            "copying was offered for a pair nobody has looked at",
        )

    def test_a_preview_arms_the_copy_button(self) -> None:
        self.assertTrue(self._armed_view().transfer_button.isEnabled())

    def test_changing_a_book_withdraws_the_approval(self) -> None:
        view = self._armed_view()
        view.set_books((SOURCE, TARGET, Book("THIRD", "Bản ba", "urn:uuid:other", 0.1)))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(2)
        self.assertFalse(
            view.transfer_button.isEnabled(),
            "approval for one pair carried over to a different pair",
        )

    def test_a_finished_copy_does_not_stay_armed(self) -> None:
        """A second click would duplicate every note."""

        view = self._armed_view()
        view.show_transfer_result("xong")
        self.assertFalse(view.transfer_button.isEnabled())

    def test_an_empty_preview_cannot_be_copied(self) -> None:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.show_plan(_plan(0))
        self.assertFalse(view.transfer_button.isEnabled())

    def test_a_failed_preview_disarms_the_copy_button(self) -> None:
        view = self._armed_view()
        view.show_unavailable("không đọc được")
        self.assertFalse(view.transfer_button.isEnabled())

    def test_the_signal_carries_the_pair_that_was_previewed(self) -> None:
        view = self._armed_view()
        seen: list[tuple[str, str]] = []
        view.transferRequested.connect(lambda a, b: seen.append((a, b)))
        view.transfer_button.click()
        self.assertEqual(seen, [("SRC", "DST")])

    def test_a_plan_for_other_books_does_not_arm_the_button(self) -> None:
        """A preview that arrives describing a different pair must not count.

        The plan comes back from the window, not from the selectors, so it can
        describe books other than the ones now chosen - and arming on it would
        copy notes nobody looked at.
        """

        third = Book("THIRD", "Bản ba", "urn:uuid:other", 0.1)
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        view.set_books((SOURCE, TARGET, third))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)

        mismatched = TransferPlan(
            source=SOURCE, target=third, items=_plan(3).items
        )
        view.show_plan(mismatched)

        self.assertFalse(
            view.transfer_button.isEnabled(),
            "armed on a plan describing books other than the chosen pair",
        )


class AlreadyThereTests(unittest.TestCase):
    """A preview that promises notes the copy will skip is a preview that lies."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _view(self, plan: TransferPlan) -> TransferNotesView:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.show_plan(plan)
        return view

    @staticmethod
    def _mixed(copied: int, total: int = 3) -> TransferPlan:
        items = tuple(
            TransferItem(
                annotation=_plan(total).items[index].annotation,
                verdict="already-there" if index < copied else "same-edition",
            )
            for index in range(total)
        )
        return TransferPlan(source=SOURCE, target=TARGET, items=items)

    def test_the_count_is_what_would_be_copied_not_what_is_listed(self) -> None:
        view = self._view(self._mixed(copied=2))
        summary = view.summary_label.text()
        self.assertIn("1", summary, summary)
        self.assertIn("2", summary, "the skipped ones are not accounted for")
        self.assertEqual(view.plan_table.rowCount(), 3, "all three stay visible")

    def test_a_plan_with_nothing_left_to_copy_disarms_the_button(self) -> None:
        view = self._view(self._mixed(copied=3))
        self.assertFalse(
            view.transfer_button.isEnabled(),
            "offered a copy that would write nothing",
        )
        self.assertIn("đã có ở cuốn kia", view.summary_label.text())

    def test_one_new_note_among_copied_ones_is_still_copyable(self) -> None:
        self.assertTrue(self._view(self._mixed(copied=2)).transfer_button.isEnabled())

    def test_each_row_says_which_side_it_is_on(self) -> None:
        view = self._view(self._mixed(copied=2))
        verdicts = [view.plan_table.item(row, 2).text() for row in range(3)]
        self.assertEqual(verdicts.count("Đã có ở cuốn kia"), 2, verdicts)
        self.assertEqual(verdicts.count("Chuyển được nguyên vẹn"), 1, verdicts)


class PresentationTests(unittest.TestCase):
    """What the tab looks like before anything has been chosen.

    An audit of the rendered window found this tab was the only one of four
    whose title carried no heading font, and that its empty table filled the
    view with column headers and nothing else.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _view(self) -> TransferNotesView:
        view = TransferNotesView(localizer=Localizer("vi"))
        self.addCleanup(view.deleteLater)
        return view

    def test_the_title_reads_as_a_heading_not_another_sentence(self) -> None:
        view = self._view()
        title = view.title_label.font()
        body = view.description.font()
        self.assertGreater(title.pointSize(), body.pointSize(), "title is body size")
        self.assertTrue(title.bold(), "title is not bold")

    def test_an_empty_table_is_not_shown_at_all(self) -> None:
        view = self._view()
        self.assertEqual(view.plan_table.rowCount(), 0)
        # isVisible() is False for any widget whose window was never shown, so
        # it passes whether or not the code hides anything. isVisibleTo asks the
        # question that matters: hidden relative to the view it sits in.
        self.assertFalse(
            view.plan_table.isVisibleTo(view), "an empty grid fills the view"
        )

    def test_the_table_appears_once_there_is_something_in_it(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.show_plan(_plan(3))
        self.assertEqual(view.plan_table.rowCount(), 3)
        self.assertTrue(view.plan_table.isVisibleTo(view), "rows exist but stay hidden")

    def test_the_table_goes_away_again_when_the_books_change(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.show_plan(_plan(3))
        view.set_books((SOURCE, TARGET))
        self.assertFalse(view.plan_table.isVisibleTo(view))

    def test_a_failed_preview_leaves_no_empty_grid_behind(self) -> None:
        view = self._view()
        view.set_books((SOURCE, TARGET))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.show_plan(_plan(3))
        view.show_unavailable("không đọc được")
        self.assertFalse(view.plan_table.isVisibleTo(view))
        self.assertIn("không đọc được", view.summary_label.text())

    def test_the_description_stays_short_enough_to_read(self) -> None:
        """It was 260 characters - more than double every other tab's."""

        from vieneu_reader.ui.i18n import _TEXT

        others = [
            len(_TEXT[key][0])
            for key in ("library.description", "paste.description")
        ]
        self.assertLessEqual(len(_TEXT["transfer.description"][0]), max(others))
