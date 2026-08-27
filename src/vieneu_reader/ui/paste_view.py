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

from .i18n import Language, Localizer


class PasteTextView(QWidget):
    """Collect text in memory without importing it into the book library."""

    readRequested = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        localizer: Localizer | None = None,
    ):
        super().__init__(parent)
        self._localizer = localizer or Localizer()
        self.setObjectName("pasteTextView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self.title_label = QLabel()
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.description = QLabel()
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("pasteTextEdit")
        layout.addWidget(self.text_edit, 1)

        actions = QHBoxLayout()
        self.counter_label = QLabel()
        self.counter_label.setObjectName("pasteCharacterCount")
        actions.addWidget(self.counter_label)
        actions.addStretch(1)
        self.read_button = QPushButton()
        self.read_button.setObjectName("readPastedTextButton")
        self.read_button.setEnabled(False)
        actions.addWidget(self.read_button)
        layout.addLayout(actions)

        self.text_edit.textChanged.connect(self._update_read_action)
        self.read_button.clicked.connect(self._emit_read_request)
        self.retranslate()
        self._update_read_action()

    def retranslate(self) -> None:
        self.title_label.setText(self._localizer.text("paste.title"))
        self.description.setText(self._localizer.text("paste.description"))
        self.text_edit.setAccessibleName(
            self._localizer.text("paste.editor_accessible")
        )
        self.text_edit.setPlaceholderText(self._localizer.text("paste.placeholder"))
        self.counter_label.setAccessibleName(
            self._localizer.text("paste.count_accessible")
        )
        self.read_button.setText(self._localizer.text("paste.read"))
        self.read_button.setAccessibleName(
            self._localizer.text("paste.read_accessible")
        )
        self._update_read_action()

    def _update_read_action(self) -> None:
        text = self.text()
        count = len(text)
        formatted_count = f"{count:,}"
        formatted_limit = f"{MAX_PASTED_TEXT_CHARS:,}"
        if self._localizer.language is Language.VIETNAMESE:
            formatted_count = formatted_count.replace(",", ".")
            formatted_limit = formatted_limit.replace(",", ".")
        if count > MAX_PASTED_TEXT_CHARS:
            self.counter_label.setText(
                self._localizer.text(
                    "paste.over_limit",
                    limit=formatted_limit,
                    count=formatted_count,
                )
            )
            self.read_button.setEnabled(False)
            return
        self.counter_label.setText(
            self._localizer.text(
                "paste.count",
                count=formatted_count,
                limit=formatted_limit,
            )
        )
        self.read_button.setEnabled(bool(text.strip()))

    def text(self) -> str:
        return self.text_edit.toPlainText()

    def _emit_read_request(self) -> None:
        self.readRequested.emit(self.text())
