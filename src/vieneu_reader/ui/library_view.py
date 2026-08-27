"""Library surface for choosing or importing a readable book."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .book_reader_view import BookReaderView
from .controller import LibraryItem


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

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
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

        title = QLabel("Thư viện sách")
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title.setFont(title_font)
        shelf_layout.addWidget(title)

        description = QLabel(
            "Mở sách EPUB hoặc PDF có lớp văn bản. Sách được giữ cục bộ để bạn "
            "có thể tiếp tục từ vị trí đang đọc."
        )
        description.setWordWrap(True)
        shelf_layout.addWidget(description)

        self.library_list = _KeyboardActivatingListWidget()
        self.library_list.setObjectName("libraryList")
        self.library_list.setAccessibleName("Danh sách sách trong thư viện")
        self.library_list.setAlternatingRowColors(True)
        shelf_layout.addWidget(self.library_list, 1)

        actions = QHBoxLayout()
        self.open_button = QPushButton("Mở PDF hoặc EPUB")
        self.open_button.setObjectName("emptyOpenButton")
        self.open_button.setAccessibleName("Mở sách PDF hoặc EPUB")
        actions.addWidget(self.open_button)

        self.paste_button = QPushButton("Dán nội dung")
        self.paste_button.setObjectName("emptyPasteTextButton")
        self.paste_button.setAccessibleName("Chuyển sang màn hình dán nội dung")
        actions.addWidget(self.paste_button)
        actions.addStretch(1)
        shelf_layout.addLayout(actions)

        self.book_reader_view = BookReaderView()
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
