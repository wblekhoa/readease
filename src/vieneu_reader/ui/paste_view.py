"""Inline surface for transient pasted-text playback."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vieneu_reader.domain.segmenter import MAX_PASTED_TEXT_CHARS


class PasteTextView(QWidget):
    """Collect text in memory without importing it into the book library."""

    readRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("pasteTextView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Dán nội dung để đọc")
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.description = QLabel(
            "Dán đoạn văn hoặc bài viết vào đây. Nội dung chỉ dùng trong phiên "
            "đọc này: không thêm vào thư viện và không được lưu vào cache."
        )
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("pasteTextEdit")
        self.text_edit.setAccessibleName("Nội dung cần đọc")
        self.text_edit.setPlaceholderText("Dán nội dung tiếng Việt vào đây…")
        layout.addWidget(self.text_edit, 1)

        actions = QHBoxLayout()
        self.counter_label = QLabel()
        self.counter_label.setObjectName("pasteCharacterCount")
        self.counter_label.setAccessibleName("Số ký tự nội dung đã dán")
        actions.addWidget(self.counter_label)
        actions.addStretch(1)
        self.read_button = QPushButton("Đọc nội dung")
        self.read_button.setObjectName("readPastedTextButton")
        self.read_button.setAccessibleName("Bắt đầu đọc nội dung đã dán")
        self.read_button.setEnabled(False)
        actions.addWidget(self.read_button)
        layout.addLayout(actions)

        self.text_edit.textChanged.connect(self._update_read_action)
        self.read_button.clicked.connect(self._emit_read_request)
        self._update_read_action()

    def _update_read_action(self) -> None:
        text = self.text()
        count = len(text)
        formatted_count = f"{count:,}".replace(",", ".")
        formatted_limit = f"{MAX_PASTED_TEXT_CHARS:,}".replace(",", ".")
        if count > MAX_PASTED_TEXT_CHARS:
            self.counter_label.setText(
                f"Vượt giới hạn {formatted_limit} ký tự · hiện có {formatted_count}"
            )
            self.read_button.setEnabled(False)
            return
        self.counter_label.setText(f"{formatted_count} / {formatted_limit} ký tự")
        self.read_button.setEnabled(bool(text.strip()))

    def text(self) -> str:
        return self.text_edit.toPlainText()

    def _emit_read_request(self) -> None:
        self.readRequested.emit(self.text())
