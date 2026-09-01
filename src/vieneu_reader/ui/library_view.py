"""Library surface for choosing or importing a readable book."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .book_reader_view import BookReaderView
from .controller import LibraryItem
from .i18n import Localizer


class _KeyboardActivatingListWidget(QListWidget):
    """Give the selected library row a deterministic Return-key action."""

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item is not None:
                self.itemActivated.emit(item)
                event.accept()
                return
        super().keyPressEvent(event)


class LibraryView(QWidget):
    """Own the imported-book shelf and its nested in-app reading surface."""

    openRequested = Signal()
    pasteRequested = Signal()
    bookActivated = Signal(str)
    surfaceChanged = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        localizer: Localizer | None = None,
    ):
        super().__init__(parent)
        self._localizer = localizer or Localizer()
        self.setObjectName("libraryView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.surface_stack = QStackedWidget()
        self.surface_stack.setObjectName("libraryStack")
        layout.addWidget(self.surface_stack)

        self.library_page = QWidget()
        self.library_page.setObjectName("libraryShelfView")
        shelf_layout = QVBoxLayout(self.library_page)
        shelf_layout.setContentsMargins(24, 20, 24, 20)
        shelf_layout.setSpacing(12)

        self.title_label = QLabel()
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        shelf_layout.addWidget(self.title_label)

        self.library_list = _KeyboardActivatingListWidget()
        self.library_list.setObjectName("libraryList")
        self.library_list.setFrameShape(QFrame.Shape.NoFrame)
        self.library_list.setAlternatingRowColors(True)

        # An empty library used to render as an empty box with the two ways in
        # parked underneath it. Nothing to list means the invitation is the
        # content, so it stands where the books will be.
        self.empty_state = QWidget()
        self.empty_state.setObjectName("libraryEmptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(12)
        empty_layout.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)
        self.open_button = QPushButton()
        self.open_button.setObjectName("emptyOpenButton")
        actions.addWidget(self.open_button)
        self.paste_button = QPushButton()
        self.paste_button.setObjectName("emptyPasteTextButton")
        actions.addWidget(self.paste_button)
        actions.addStretch(1)
        empty_layout.addLayout(actions)

        # The constraint belongs next to the choice it constrains, not at the
        # top of a screen someone has not acted on yet.
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(self.description_label)
        empty_layout.addStretch(1)

        self.shelf_stack = QStackedWidget()
        self.shelf_stack.setObjectName("libraryShelfStack")
        self.shelf_stack.addWidget(self.empty_state)
        self.shelf_stack.addWidget(self.library_list)
        shelf_layout.addWidget(self.shelf_stack, 1)

        self.book_reader_view = BookReaderView(localizer=self._localizer)
        self.surface_stack.addWidget(self.library_page)
        self.surface_stack.addWidget(self.book_reader_view)

        self.library_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._signature: tuple[tuple[str, str, str], ...] = ()
        self.open_button.clicked.connect(self.openRequested.emit)
        self.paste_button.clicked.connect(self.pasteRequested.emit)
        self.library_list.itemClicked.connect(self._emit_book_activation)
        self.library_list.itemActivated.connect(self._emit_book_activation)
        self.book_reader_view.backRequested.connect(self.show_library)
        self.surface_stack.currentChanged.connect(self._surface_changed)
        self.retranslate()

    def retranslate(self) -> None:
        self.title_label.setText(self._localizer.text("library.title"))
        self.description_label.setText(self._localizer.text("library.description"))
        self.library_list.setAccessibleName(
            self._localizer.text("library.list_accessible")
        )
        self.open_button.setText(self._localizer.text("toolbar.open"))
        self.open_button.setAccessibleName(
            self._localizer.text("library.open_accessible")
        )
        self.paste_button.setText(self._localizer.text("toolbar.paste"))
        self.paste_button.setAccessibleName(
            self._localizer.text("library.paste_accessible")
        )
        self.book_reader_view.retranslate()

    def show_library(self) -> None:
        self.surface_stack.setCurrentWidget(self.library_page)
        self.library_list.setFocus()

    def show_reader(self) -> None:
        self.surface_stack.setCurrentWidget(self.book_reader_view)

    def is_reader_visible(self) -> bool:
        return self.surface_stack.currentWidget() is self.book_reader_view

    def render(
        self,
        items: tuple[LibraryItem, ...],
        active_book_id: str | None,
    ) -> None:
        blocker = QSignalBlocker(self.library_list)
        signature = tuple((item.id, item.title, item.source_format) for item in items)
        if signature != self._signature:
            self.library_list.clear()
            for item in items:
                row = QListWidgetItem(
                    f"{item.title}  ·  {item.source_format.upper()}"
                )
                row.setData(Qt.ItemDataRole.UserRole, item.id)
                self.library_list.addItem(row)
            self._signature = signature
        self.shelf_stack.setCurrentWidget(
            self.library_list if items else self.empty_state
        )
        self._select_book(active_book_id)
        del blocker

    def _select_book(self, book_id: str | None) -> None:
        if book_id is None:
            self.library_list.setCurrentRow(-1)
            return
        for index in range(self.library_list.count()):
            item = self.library_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == book_id:
                self.library_list.setCurrentItem(item)
                return

    def _emit_book_activation(self, item: QListWidgetItem) -> None:
        book_id = item.data(Qt.ItemDataRole.UserRole)
        if book_id:
            self.bookActivated.emit(str(book_id))

    def _surface_changed(self, _index: int) -> None:
        self.surfaceChanged.emit()
