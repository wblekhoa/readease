"""Companion surface for reading selected text from Apple Books."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .controller import ExternalReadingState, SessionReadingItem


class ExternalReadingView(QWidget):
    """Render the explicit Apple Books workflow and transient session context."""

    openAccessibilitySettingsRequested = Signal()
    replayRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("externalReadingView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Đọc từ Apple Books")
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.status_label = QLabel("Đang chuẩn bị phím tắt…")
        self.status_label.setObjectName("externalReadingStatus")
        self.status_label.setAccessibleName("Trạng thái đọc từ Apple Books")
        self.status_label.setWordWrap(True)
        status_font = QFont(self.status_label.font())
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)

        self.detail_label = QLabel()
        self.detail_label.setObjectName("externalReadingDetail")
        self.detail_label.setAccessibleName("Chi tiết trạng thái đọc từ Apple Books")
        self.detail_label.setWordWrap(True)
        self.detail_label.hide()
        layout.addWidget(self.detail_label)

        body = QHBoxLayout()
        body.setSpacing(28)
        guide = QVBoxLayout()
        guide.setSpacing(10)

        description = QLabel(
            "Giữ ReadEase đang chạy, quét chọn đoạn văn trong Apple Books, "
            "rồi dùng phím tắt bên dưới để nghe bằng giọng Việt cục bộ."
        )
        description.setWordWrap(True)
        guide.addWidget(description)

        steps = QLabel(
            "1. Mở sách trong Apple Books.\n"
            "2. Quét chọn đúng phần bạn muốn nghe.\n"
            "3. Nhấn phím tắt; ReadEase sẽ đọc mà không đưa cửa sổ này lên trước."
        )
        steps.setObjectName("externalReadingSteps")
        steps.setAccessibleName("Hướng dẫn đọc phần đã chọn trong Apple Books")
        steps.setWordWrap(True)
        guide.addWidget(steps)

        shortcut_caption = QLabel("Phím tắt")
        caption_font = QFont(shortcut_caption.font())
        caption_font.setBold(True)
        shortcut_caption.setFont(caption_font)
        guide.addWidget(shortcut_caption)

        shortcut = QLabel("Control + Option + Command + R")
        shortcut.setObjectName("externalReadingShortcut")
        shortcut.setAccessibleName(
            "Phím tắt đọc phần đã chọn: Control Option Command R"
        )
        shortcut_font = QFont(shortcut.font())
        shortcut_font.setPointSize(shortcut_font.pointSize() + 2)
        shortcut_font.setBold(True)
        shortcut.setFont(shortcut_font)
        shortcut.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        guide.addWidget(shortcut)

        permission_note = QLabel(
            "Lần đầu sử dụng, macOS cần cho phép ReadEase điều khiển thao tác sao "
            "chép trong Apple Books. Bạn có thể mở đúng mục Trợ năng tại đây."
        )
        permission_note.setWordWrap(True)
        guide.addWidget(permission_note)

        permission_row = QHBoxLayout()
        self.permission_button = QPushButton("Mở Cài đặt quyền")
        self.permission_button.setObjectName(
            "externalAccessibilitySettingsButton"
        )
        self.permission_button.setAccessibleName(
            "Mở cài đặt quyền Trợ năng của macOS cho ReadEase"
        )
        permission_row.addWidget(self.permission_button)
        permission_row.addStretch(1)
        guide.addLayout(permission_row)

        privacy_note = QLabel(
            "ReadEase chỉ xử lý khi bạn bấm phím tắt trong Apple Books; không "
            "theo dõi màn hình hoặc clipboard ở chế độ nền."
        )
        privacy_note.setWordWrap(True)
        guide.addWidget(privacy_note)
        guide.addStretch(1)

        recent = QVBoxLayout()
        recent.setSpacing(8)
        recent_title = QLabel("Đã đọc từ Apple Books trong phiên")
        recent_title_font = QFont(recent_title.font())
        recent_title_font.setBold(True)
        recent_title.setFont(recent_title_font)
        recent.addWidget(recent_title)

        self.history_empty = QLabel(
            "Chưa có đoạn nào. Phần bạn đọc bằng phím tắt sẽ xuất hiện ở đây "
            "và tự mất khi đóng ReadEase."
        )
        self.history_empty.setObjectName("externalReadingHistoryEmpty")
        self.history_empty.setWordWrap(True)
        self.history_empty.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.history_empty.setMaximumHeight(64)
        recent.addWidget(self.history_empty)

        self.history_list = QListWidget()
        self.history_list.setObjectName("externalReadingHistoryList")
        self.history_list.setAccessibleName(
            "Các phần đã đọc từ Apple Books trong phiên"
        )
        self.history_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.history_list.setWordWrap(False)
        self.history_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.history_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.history_list.setMinimumHeight(140)
        self.history_list.setMaximumHeight(220)
        recent.addWidget(self.history_list, 1)

        replay_row = QHBoxLayout()
        self.replay_button = QPushButton("Nghe lại phần đã chọn")
        self.replay_button.setObjectName("externalReadingReplayButton")
        self.replay_button.setAccessibleName(
            "Nghe lại phần Apple Books đang chọn trong lịch sử phiên"
        )
        self.replay_button.setEnabled(False)
        replay_row.addWidget(self.replay_button)
        replay_row.addStretch(1)
        recent.addLayout(replay_row)
        recent.addStretch(1)

        body.addLayout(guide, 3)
        body.addLayout(recent, 2)
        layout.addLayout(body, 1)

        self.permission_button.clicked.connect(
            self.openAccessibilitySettingsRequested.emit
        )
        self.history_list.currentItemChanged.connect(
            lambda current, _previous: self.replay_button.setEnabled(
                current is not None
            )
        )
        self.history_list.itemDoubleClicked.connect(
            lambda item: self.replayRequested.emit(
                str(item.data(Qt.ItemDataRole.UserRole))
            )
        )
        self.replay_button.clicked.connect(self._replay_current)

    def render(
        self,
        state: ExternalReadingState,
        history: tuple[SessionReadingItem, ...],
        error: str | None,
    ) -> None:
        status_messages = {
            ExternalReadingState.STARTING: "Đang chuẩn bị phím tắt…",
            ExternalReadingState.READY: "Sẵn sàng đọc từ Apple Books",
            ExternalReadingState.RECEIVED: "Đã nhận phần chọn gần nhất",
            ExternalReadingState.PERMISSION_REQUIRED: "Cần quyền Trợ năng",
            ExternalReadingState.FAILED: "Chưa thể đọc phần đã chọn",
        }
        self.status_label.setText(status_messages[state])
        detail = (
            error
            if state
            in {
                ExternalReadingState.PERMISSION_REQUIRED,
                ExternalReadingState.FAILED,
            }
            else None
        )
        self.detail_label.setText(detail or "")
        self.detail_label.setVisible(bool(detail))

        apple_books_items = tuple(
            item for item in history if item.source == "apple_books"
        )
        selected_id = None
        current = self.history_list.currentItem()
        if current is not None:
            selected_id = current.data(Qt.ItemDataRole.UserRole)

        self.history_list.clear()
        selected_row = -1
        for row, item in enumerate(apple_books_items):
            list_item = QListWidgetItem(item.preview)
            list_item.setData(Qt.ItemDataRole.UserRole, item.id)
            list_item.setToolTip(item.preview)
            self.history_list.addItem(list_item)
            if item.id == selected_id:
                selected_row = row

        has_history = bool(apple_books_items)
        self.history_empty.setVisible(not has_history)
        self.history_list.setVisible(has_history)
        if has_history:
            row_height = max(24, self.history_list.sizeHintForRow(0))
            self.history_list.setFixedHeight(
                min(220, max(72, row_height * len(apple_books_items) + 6))
            )
            self.history_list.setCurrentRow(selected_row if selected_row >= 0 else 0)
        else:
            self.replay_button.setEnabled(False)

    def _replay_current(self) -> None:
        item = self.history_list.currentItem()
        if item is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if item_id:
            self.replayRequested.emit(str(item_id))
