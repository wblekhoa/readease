"""Preview which Apple Books notes could move from one copy of a book to another.

This surface only ever reads. It shows what a transfer would mean and stops there,
because writing into Apple Books' own database is unsupported by Apple and would put
every book's annotations at risk for the sake of a few.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vieneu_reader.integrations.apple_books import Book, TransferPlan

from .i18n import Localizer

_PREVIEW_ROW_LIMIT = 200
_BOOKMARK_KIND = 3


class TransferNotesView(QWidget):
    """Pick two books, see what would carry over."""

    previewRequested = Signal(str, str)
    transferRequested = Signal(str, str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        localizer: Localizer | None = None,
    ):
        super().__init__(parent)
        self._localizer = localizer or Localizer()
        self.setObjectName("transferNotesView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self.title_label = QLabel()
        self.title_label.setObjectName("transferNotesTitle")
        self.description = QLabel()
        self.description.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description)

        pickers = QHBoxLayout()
        pickers.setSpacing(12)
        self.source_label = QLabel()
        self.source_selector = QComboBox()
        self.source_selector.setObjectName("transferSourceSelector")
        self.target_label = QLabel()
        self.target_selector = QComboBox()
        self.target_selector.setObjectName("transferTargetSelector")
        for label, selector in (
            (self.source_label, self.source_selector),
            (self.target_label, self.target_selector),
        ):
            pickers.addWidget(label)
            pickers.addWidget(selector, 1)
        self.preview_button = QPushButton()
        self.preview_button.setObjectName("transferPreviewButton")
        pickers.addWidget(self.preview_button)
        self.transfer_button = QPushButton()
        self.transfer_button.setObjectName("transferCopyButton")
        pickers.addWidget(self.transfer_button)
        layout.addLayout(pickers)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("transferSummary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.plan_table = QTableWidget(0, 3)
        self.plan_table.setObjectName("transferPlanTable")
        self.plan_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.plan_table.verticalHeader().setVisible(False)
        header = self.plan_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.plan_table, 1)

        self.source_selector.currentIndexChanged.connect(self._selection_changed)
        self.target_selector.currentIndexChanged.connect(self._selection_changed)
        self.preview_button.clicked.connect(self._request_preview)
        self.transfer_button.clicked.connect(self._request_transfer)

        self._unavailable = False
        # Copying is allowed only for the exact pair a preview was shown for, so
        # that what someone approved on screen is what actually gets written.
        self._previewed: tuple[str, str] | None = None
        self._previewed_count = 0
        self.retranslate()
        # A QPushButton starts enabled; nothing is selected yet, so it must not.
        self._refresh_buttons()

    # -- language -----------------------------------------------------------

    def retranslate(self, localizer: Localizer | None = None) -> None:
        if localizer is not None:
            self._localizer = localizer
        text = self._localizer.text
        self.title_label.setText(text("transfer.title"))
        self.description.setText(text("transfer.description"))
        self.source_label.setText(text("transfer.source"))
        self.target_label.setText(text("transfer.target"))
        self.preview_button.setText(text("transfer.preview"))
        self.preview_button.setAccessibleName(text("transfer.preview_accessible"))
        self.transfer_button.setText(text("transfer.copy"))
        self.transfer_button.setAccessibleName(text("transfer.copy_accessible"))
        self.summary_label.setAccessibleName(text("transfer.table_accessible"))
        self.source_selector.setAccessibleName(text("transfer.source"))
        self.target_selector.setAccessibleName(text("transfer.target"))
        self.plan_table.setAccessibleName(text("transfer.table_accessible"))
        self.plan_table.setHorizontalHeaderLabels(
            [text("transfer.column_kind"), text("transfer.column_text"),
             text("transfer.column_verdict")]
        )
        if self.plan_table.rowCount() == 0 and not self._unavailable:
            self.summary_label.setText(text("transfer.pick_two"))

    # -- state --------------------------------------------------------------

    def set_books(self, books: tuple[Book, ...]) -> None:
        self._unavailable = False
        self._forget_preview()
        for selector in (self.source_selector, self.target_selector):
            selector.blockSignals(True)
            selector.clear()
            for label, book in zip(self._book_labels(books), books):
                selector.addItem(label, book.asset_id)
            selector.setCurrentIndex(-1)
            selector.blockSignals(False)
        self.plan_table.setRowCount(0)
        self.summary_label.setText(self._localizer.text("transfer.pick_two"))
        self._refresh_buttons()

    def show_plan(self, plan: TransferPlan) -> None:
        self._unavailable = False
        self._previewed = (plan.source.asset_id, plan.target.asset_id)
        # What arms the button is what would be written, not what is listed:
        # a plan of items that are all already there copies nothing.
        self._previewed_count = len(plan.copyable)
        rows = plan.items[:_PREVIEW_ROW_LIMIT]
        self.plan_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            annotation = item.annotation
            kind = self._localizer.text(self._kind_key(annotation))
            excerpt = (annotation.note or annotation.selected_text or "").strip()
            if not excerpt:
                excerpt = self._localizer.text("transfer.no_text")
            cells = (kind, excerpt, self._verdict_text(item.verdict))
            for column, value in enumerate(cells):
                cell = QTableWidgetItem(value)
                cell.setToolTip(value)
                cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.plan_table.setItem(row, column, cell)
        self.summary_label.setText(self._summary(plan, shown=len(rows)))
        self._refresh_buttons()

    def show_unavailable(self, message: str) -> None:
        # Only a library we could not load at all blocks the button. A preview that
        # failed with books still listed is worth retrying, so it must not lock up.
        self._unavailable = self.source_selector.count() == 0
        self._forget_preview()
        self.plan_table.setRowCount(0)
        self.summary_label.setText(message)
        self._refresh_buttons()

    def show_transfer_result(self, message: str) -> None:
        """Report a finished copy, and require a fresh preview before another.

        Leaving the button live would let a second click duplicate every note.
        """

        self._forget_preview()
        self.summary_label.setText(message)
        self._refresh_buttons()

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _book_labels(books: tuple[Book, ...]) -> tuple[str, ...]:
        """Label each book, disambiguating copies that would otherwise collide.

        Two copies of one book is the case this feature exists for, and they share
        a title and often a reading position, so the plain label would show the
        same text twice and leave no way to tell which is which.
        """

        plain = [
            f"{round(book.reading_progress * 100)}% · {book.title}" for book in books
        ]
        labels = []
        for index, label in enumerate(plain):
            if plain.count(label) > 1:
                position = f"{round(books[index].reading_progress * 100)}%"
                label = label.replace(
                    position, f"{position} ({books[index].asset_id[:4]})", 1
                )
            labels.append(label)
        return tuple(labels)

    @staticmethod
    def _kind_key(annotation) -> str:
        if annotation.has_note:
            return "transfer.kind_note"
        if annotation.kind == _BOOKMARK_KIND:
            return "transfer.kind_bookmark"
        return "transfer.kind_highlight"

    def _verdict_text(self, verdict: str) -> str:
        key = {
            "same-edition": "transfer.verdict_same",
            "already-there": "transfer.verdict_already",
        }.get(verdict, "transfer.verdict_review")
        return self._localizer.text(key)

    def _summary(self, plan: TransferPlan, *, shown: int) -> str:
        text = self._localizer.text
        if not plan.items:
            return text("transfer.no_notes")
        copyable = len(plan.copyable)
        carried = sum(1 for item in plan.items if item.verdict == "already-there")
        risky = len(plan.items) - copyable - carried
        if not copyable:
            key = "transfer.none_safe" if risky else "transfer.all_already_there"
            return text(key, count=risky or carried)
        body = text("transfer.count", count=copyable)
        if carried:
            body = f"{body} {text('transfer.some_already_there', count=carried)}"
        if risky:
            body = f"{body} {text('transfer.some_need_review', count=risky)}"
        if shown < len(plan.items):
            body = f"{body} {text('transfer.truncated', shown=shown)}"
        return body

    def _selection(self) -> tuple[str | None, str | None]:
        return (
            self.source_selector.currentData(),
            self.target_selector.currentData(),
        )

    def _forget_preview(self) -> None:
        self._previewed = None
        self._previewed_count = 0

    def _selection_changed(self) -> None:
        # A preview describes one pair of books. Change either one and the
        # approval it earned no longer applies.
        self._forget_preview()
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        source, target = self._selection()
        pair_is_usable = (
            not self._unavailable
            and bool(source)
            and bool(target)
            and source != target
        )
        self.preview_button.setEnabled(pair_is_usable)
        self.transfer_button.setEnabled(
            pair_is_usable
            and self._previewed == (source, target)
            and self._previewed_count > 0
        )

    def _request_preview(self) -> None:
        source, target = self._selection()
        if source and target and source != target:
            self.previewRequested.emit(source, target)

    def _request_transfer(self) -> None:
        source, target = self._selection()
        if self._previewed == (source, target) and self._previewed_count > 0:
            self.transferRequested.emit(source, target)
