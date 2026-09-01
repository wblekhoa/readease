"""Companion surface for reading text selected in any app."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
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

from vieneu_reader.integrations.selection_shortcut import (
    DEFAULT_SHORTCUT,
    Shortcut,
)

from .controller import ExternalReadingState, SessionReadingItem
from .i18n import Localizer
from .shortcut_recorder import ShortcutRecorderButton


class ExternalReadingView(QWidget):
    """Render the explicit read-selection workflow and transient session context."""

    openAccessibilitySettingsRequested = Signal()
    replayRequested = Signal(str)
    shortcutRecorded = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        localizer: Localizer | None = None,
        shortcut: Shortcut | None = None,
    ):
        super().__init__(parent)
        self._localizer = localizer or Localizer()
        self._shortcut = shortcut or DEFAULT_SHORTCUT
        self._rendered_state = ExternalReadingState.STARTING
        self._rendered_history: tuple[SessionReadingItem, ...] = ()
        self._rendered_error: str | None = None
        self.setObjectName("externalReadingView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self.title_label = QLabel()
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.status_label = QLabel()
        self.status_label.setObjectName("externalReadingStatus")
        self.status_label.setWordWrap(True)
        # Body weight on purpose. Bold, directly under a bold heading, made two
        # lines compete for the same role and neither read as the title.
        layout.addWidget(self.status_label)

        self.detail_label = QLabel()
        self.detail_label.setObjectName("externalReadingDetail")
        self.detail_label.setWordWrap(True)
        self.detail_label.hide()
        layout.addWidget(self.detail_label)

        body = QHBoxLayout()
        body.setSpacing(28)
        guide = QVBoxLayout()
        guide.setSpacing(10)


        self.steps_label = QLabel()
        self.steps_label.setObjectName("externalReadingSteps")
        self.steps_label.setWordWrap(True)
        guide.addWidget(self.steps_label)

        self.shortcut_caption = QLabel()
        # A section label, and the right column's own label is emphasised the
        # same way. Dropping it here left a bare line dangling between two
        # paragraphs and made the two columns disagree.
        caption_font = QFont(self.shortcut_caption.font())
        caption_font.setBold(True)
        self.shortcut_caption.setFont(caption_font)
        guide.addWidget(self.shortcut_caption)

        shortcut_row = QHBoxLayout()
        shortcut_row.setSpacing(12)
        shortcut = QLabel(self._shortcut.label)
        shortcut.setObjectName("externalReadingShortcut")
        self.shortcut_label = shortcut
        shortcut_font = QFont(shortcut.font())
        shortcut_font.setPointSize(shortcut_font.pointSize() + 2)
        shortcut_font.setBold(True)
        shortcut.setFont(shortcut_font)
        shortcut.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        shortcut_row.addWidget(shortcut)
        self.shortcut_recorder = ShortcutRecorderButton()
        self.shortcut_recorder.setObjectName("externalReadingShortcutRecorder")
        shortcut_row.addWidget(self.shortcut_recorder)
        shortcut_row.addStretch(1)
        guide.addLayout(shortcut_row)

        self.shortcut_hint = QLabel()
        self.shortcut_hint.setObjectName("externalReadingShortcutHint")
        self.shortcut_hint.setWordWrap(True)
        self.shortcut_hint.hide()
        guide.addWidget(self.shortcut_hint)

        self.permission_note = QLabel()
        self.permission_note.setWordWrap(True)
        guide.addWidget(self.permission_note)

        permission_row = QHBoxLayout()
        self.permission_button = QPushButton()
        self.permission_button.setObjectName(
            "externalAccessibilitySettingsButton"
        )
        permission_row.addWidget(self.permission_button)
        permission_row.addStretch(1)
        guide.addLayout(permission_row)


        guide.addStretch(1)

        recent = QVBoxLayout()
        recent.setSpacing(8)
        self.recent_title = QLabel()
        recent_title_font = QFont(self.recent_title.font())
        recent_title_font.setBold(True)
        self.recent_title.setFont(recent_title_font)
        recent.addWidget(self.recent_title)

        self.history_empty = QLabel()
        self.history_empty.setObjectName("externalReadingHistoryEmpty")
        self.history_empty.setWordWrap(True)
        self.history_empty.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.history_empty.setMaximumHeight(64)
        recent.addWidget(self.history_empty)

        self.history_list = QListWidget()
        self.history_list.setObjectName("externalReadingHistoryList")
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
        self.replay_button = QPushButton()
        self.replay_button.setObjectName("externalReadingReplayButton")
        # Appears with something to replay, rather than sitting under an empty
        # list greyed out.
        self.replay_button.setEnabled(False)
        self.replay_button.hide()
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
            lambda current, _previous: self._show_replay(current is not None)
        )
        self.history_list.itemDoubleClicked.connect(
            lambda item: self.replayRequested.emit(
                str(item.data(Qt.ItemDataRole.UserRole))
            )
        )
        self.replay_button.clicked.connect(self._replay_current)
        self.shortcut_recorder.recordingChanged.connect(self._recording_changed)
        self.shortcut_recorder.shortcutRecorded.connect(
            self.shortcutRecorded.emit
        )
        self.retranslate()

    def set_shortcut(self, shortcut: Shortcut) -> None:
        """Show the combination the helper has actually registered."""

        self._shortcut = shortcut
        self.shortcut_label.setText(shortcut.label)
        self.shortcut_label.setAccessibleName(
            self._localizer.text(
                "external.shortcut_accessible",
                shortcut=shortcut.label,
            )
        )

    def _recording_changed(self, recording: bool) -> None:
        self.shortcut_recorder.setText(
            self._localizer.text(
                "external.shortcut_recording"
                if recording
                else "external.shortcut_change"
            )
        )
        self.shortcut_hint.setVisible(recording)

    def retranslate(self) -> None:
        self.title_label.setText(self._localizer.text("external.title"))
        self.status_label.setAccessibleName(
            self._localizer.text("external.status_accessible")
        )
        self.detail_label.setAccessibleName(
            self._localizer.text("external.detail_accessible")
        )
        self.steps_label.setText(self._localizer.text("external.steps"))
        self.steps_label.setAccessibleName(
            self._localizer.text("external.steps_accessible")
        )
        self.shortcut_caption.setText(self._localizer.text("external.shortcut"))
        self.set_shortcut(self._shortcut)
        self.shortcut_recorder.setAccessibleName(
            self._localizer.text("external.shortcut_change_accessible")
        )
        self.shortcut_hint.setText(
            self._localizer.text("external.shortcut_hint")
        )
        self._recording_changed(self.shortcut_recorder.is_recording)
        self.permission_note.setText(
            self._localizer.text("external.permission_note")
        )
        self.permission_button.setText(
            self._localizer.text("external.open_settings")
        )
        self.permission_button.setAccessibleName(
            self._localizer.text("external.open_settings_accessible")
        )
        self.recent_title.setText(self._localizer.text("external.recent_title"))
        self.history_empty.setText(self._localizer.text("external.history_empty"))
        self.history_list.setAccessibleName(
            self._localizer.text("external.history_accessible")
        )
        self.replay_button.setText(self._localizer.text("external.replay"))
        self.replay_button.setAccessibleName(
            self._localizer.text("external.replay_accessible")
        )
        self.render(
            self._rendered_state,
            self._rendered_history,
            self._rendered_error,
        )

    def render(
        self,
        state: ExternalReadingState,
        history: tuple[SessionReadingItem, ...],
        error: str | None,
    ) -> None:
        self._rendered_state = state
        self._rendered_history = history
        self._rendered_error = error
        status_messages = {
            ExternalReadingState.STARTING: self._localizer.text("external.starting"),
            ExternalReadingState.READY: self._localizer.text("external.ready"),
            ExternalReadingState.RECEIVED: self._localizer.text("external.received"),
            ExternalReadingState.PERMISSION_REQUIRED: self._localizer.text(
                "external.permission_required"
            ),
            ExternalReadingState.FAILED: self._localizer.text("external.failed"),
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
        self.detail_label.setText(self._localizer.runtime(detail))
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
            self._show_replay(False)

    def _show_replay(self, usable: bool) -> None:
        self.replay_button.setEnabled(usable)
        self.replay_button.setVisible(usable)

    def _replay_current(self) -> None:
        item = self.history_list.currentItem()
        if item is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if item_id:
            self.replayRequested.emit(str(item_id))
