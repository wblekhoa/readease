"""Native-control Qt window for the ReadEase MVP."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QKeySequence,
    QPalette,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vieneu_reader.identity import PRODUCT_DISPLAY_NAME
from vieneu_reader.integrations.macos_settings import (
    open_accessibility_settings as open_accessibility_settings_pane,
)
from vieneu_reader.playback.coordinator import PlaybackState

from .controller import ReaderController, ReaderViewState
from .external_reading_view import ExternalReadingView
from .library_view import LibraryView
from .paste_view import PasteTextView


class ReaderWindow(QMainWindow):
    def __init__(
        self,
        controller: ReaderController,
        model_setup: Any,
        parent: QWidget | None = None,
        *,
        open_accessibility_settings: Callable[[], object] | None = None,
    ):
        super().__init__(parent)
        self._controller = controller
        self._model_setup = model_setup
        self._open_accessibility_settings = (
            open_accessibility_settings or open_accessibility_settings_pane
        )
        self._model_ready = False
        self._rendering = False
        self._workspace_initialized = False
        self._rendered_session_history = None

        self.setWindowTitle(PRODUCT_DISPLAY_NAME)
        self.setMinimumSize(900, 600)
        self.resize(1180, 760)
        self.setAcceptDrops(True)

        self.root_stack = QStackedWidget()
        self.root_stack.setObjectName("rootStack")
        self.model_setup_page = self._build_model_setup_page()
        self.reader_page = self._build_reader_page()
        self.root_stack.addWidget(self.model_setup_page)
        self.root_stack.addWidget(self.reader_page)
        self.setCentralWidget(self.root_stack)

        self._connect_actions()
        self._model_setup.progressChanged.connect(self._on_model_progress)
        self._model_setup.ready.connect(self._on_model_ready)
        self._model_setup.failed.connect(self._on_model_failed)
        self._model_setup.cancelled.connect(self._on_model_cancelled)
        self._controller.add_listener(self._render_state)

        if self._model_setup.is_ready:
            self._model_setup.start()
        else:
            self.root_stack.setCurrentWidget(self.model_setup_page)

    def _build_model_setup_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("modelSetupPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(80, 64, 80, 64)
        layout.setSpacing(16)
        layout.addStretch(1)

        title = QLabel("Chuẩn bị giọng đọc tiếng Việt")
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 8)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        self.model_setup_description = QLabel(
            "ReadEase cần tải khoảng 330 MB dữ liệu giọng đọc ở lần đầu. "
            "Sau đó bạn có thể đọc sách hoàn toàn offline và không cần API key."
        )
        self.model_setup_description.setWordWrap(True)
        self.model_setup_description.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.model_setup_description.setMaximumWidth(620)
        layout.addWidget(
            self.model_setup_description,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        self.model_progress = QProgressBar()
        self.model_progress.setObjectName("modelProgress")
        self.model_progress.setRange(0, 100)
        self.model_progress.setValue(0)
        self.model_progress.setTextVisible(True)
        self.model_progress.setMaximumWidth(520)
        layout.addWidget(self.model_progress, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.model_status = QLabel("Sẵn sàng tải giọng đọc.")
        self.model_status.setWordWrap(True)
        self.model_status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.model_status)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.prepare_model_button = QPushButton("Chuẩn bị giọng đọc")
        self.prepare_model_button.setObjectName("prepareModelButton")
        self.prepare_model_button.setAccessibleName("Chuẩn bị giọng đọc tiếng Việt")
        self.cancel_model_button = QPushButton("Hủy")
        self.cancel_model_button.setObjectName("cancelModelButton")
        self.cancel_model_button.setAccessibleName("Hủy chuẩn bị giọng đọc")
        self.cancel_model_button.hide()
        actions.addWidget(self.prepare_model_button)
        actions.addWidget(self.cancel_model_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)
        return page

    def _build_reader_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("readerPage")
        root = QVBoxLayout(page)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        self.brand_title = QLabel(PRODUCT_DISPLAY_NAME)
        self.brand_title.setObjectName("brandTitle")
        title_font = QFont(self.brand_title.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self.brand_title.setFont(title_font)
        header.addWidget(self.brand_title)
        header.addStretch(1)
        self.toolbar_open_button = QPushButton("Mở PDF hoặc EPUB")
        self.toolbar_open_button.setObjectName("openBookButton")
        self.toolbar_open_button.setAccessibleName("Mở thêm sách PDF hoặc EPUB")
        header.addWidget(self.toolbar_open_button)
        self.toolbar_paste_button = QPushButton("Dán nội dung")
        self.toolbar_paste_button.setObjectName("pasteTextButton")
        self.toolbar_paste_button.setAccessibleName("Dán nội dung để đọc")
        header.addWidget(self.toolbar_paste_button)
        root.addLayout(header)

        self.feature_navigation = QTabBar()
        self.feature_navigation.setObjectName("featureNavigation")
        self.feature_navigation.setAccessibleName("Chọn tính năng ReadEase")
        self.feature_navigation.setExpanding(False)
        for label in ("Thư viện", "Dán nội dung", "Đọc sách"):
            self.feature_navigation.addTab(label)
        root.addWidget(self.feature_navigation)

        self.feature_stack = QStackedWidget()
        self.feature_stack.setObjectName("featureStack")
        self.library_view = LibraryView()
        self.paste_text_view = PasteTextView()
        self.external_reading_view = ExternalReadingView()
        for feature_view in (
            self.library_view,
            self.paste_text_view,
            self.external_reading_view,
        ):
            self.feature_stack.addWidget(feature_view)
        root.addWidget(self.feature_stack, 1)

        player = QFrame()
        player.setFrameShape(QFrame.Shape.StyledPanel)
        player_layout = QHBoxLayout(player)
        player_layout.setContentsMargins(12, 8, 12, 8)
        player_layout.setSpacing(8)

        self.previous_button = QToolButton()
        self.previous_button.setText("Trước")
        self.previous_button.setAccessibleName("Đọc đoạn trước")
        self.play_button = QPushButton("Đọc")
        self.play_button.setObjectName("playButton")
        self.play_button.setAccessibleName("Bắt đầu đọc hoặc tạm dừng")
        self.stop_button = QToolButton()
        self.stop_button.setText("Dừng")
        self.stop_button.setAccessibleName("Dừng đọc")
        self.next_button = QToolButton()
        self.next_button.setText("Sau")
        self.next_button.setAccessibleName("Đọc đoạn tiếp theo")
        self.session_history_button = QToolButton()
        self.session_history_button.setObjectName("sessionHistoryButton")
        self.session_history_button.setText("Lịch sử phiên")
        self.session_history_button.setAccessibleName(
            "Mở lịch sử nội dung đã đọc trong phiên"
        )
        self.session_history_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.session_history_menu = QMenu(self.session_history_button)
        self.session_history_menu.setObjectName("sessionHistoryMenu")
        self.session_history_button.setMenu(self.session_history_menu)
        for control in (
            self.previous_button,
            self.play_button,
            self.stop_button,
            self.next_button,
            self.session_history_button,
        ):
            control.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            player_layout.addWidget(control)

        player_layout.addStretch(1)
        voice_label = QLabel("Giọng")
        player_layout.addWidget(voice_label)
        self.voice_combo = QComboBox()
        self.voice_combo.setAccessibleName("Chọn giọng đọc")
        self.voice_combo.setMinimumWidth(170)
        player_layout.addWidget(self.voice_combo)
        rate_label = QLabel("Tốc độ")
        player_layout.addWidget(rate_label)
        self.rate_combo = QComboBox()
        self.rate_combo.setAccessibleName("Chọn tốc độ đọc")
        for rate in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
            self.rate_combo.addItem(f"{rate:g}×", rate)
        player_layout.addWidget(self.rate_combo)
        root.addWidget(player)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Sẵn sàng.")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        status_row.addWidget(self.status_label)
        self.reading_location_label = QLabel()
        self.reading_location_label.setObjectName("readingLocationLabel")
        self.reading_location_label.setAccessibleName("Vị trí đọc trong sách")
        status_row.addWidget(self.reading_location_label)
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        error_palette = QPalette(self.error_label.palette())
        error_palette.setColor(
            QPalette.ColorRole.WindowText,
            self.palette().color(QPalette.ColorRole.LinkVisited),
        )
        self.error_label.setPalette(error_palette)
        self.error_label.hide()
        status_row.addWidget(self.error_label, 2)
        self.open_accessibility_settings_button = QPushButton("Mở Cài đặt quyền")
        self.open_accessibility_settings_button.setObjectName(
            "openAccessibilitySettingsButton"
        )
        self.open_accessibility_settings_button.setAccessibleName(
            "Mở cài đặt quyền Trợ năng của macOS"
        )
        self.open_accessibility_settings_button.hide()
        status_row.addWidget(self.open_accessibility_settings_button)
        root.addLayout(status_row)
        return page

    def _connect_actions(self) -> None:
        self.prepare_model_button.clicked.connect(self._start_model_setup)
        self.cancel_model_button.clicked.connect(self._cancel_model_setup)
        self.toolbar_open_button.clicked.connect(self.open_book_dialog)
        self.toolbar_paste_button.clicked.connect(self.show_paste_view)
        self.feature_navigation.currentChanged.connect(self._feature_changed)
        self.library_view.openRequested.connect(self.open_book_dialog)
        self.library_view.pasteRequested.connect(self.show_paste_view)
        self.library_view.bookActivated.connect(self._activate_library_book)
        self.library_view.surfaceChanged.connect(self._library_surface_changed)
        self.paste_text_view.readRequested.connect(self._read_pasted_text)
        self.library_view.book_reader_view.chapterActivated.connect(
            self._controller.select_chapter
        )
        self.library_view.book_reader_view.segmentActivated.connect(
            self._controller.select_segment
        )
        self.library_view.book_reader_view.readSelectionRequested.connect(
            self._controller.read_selection
        )
        self.external_reading_view.openAccessibilitySettingsRequested.connect(
            self._open_accessibility_settings
        )
        self.external_reading_view.replayRequested.connect(
            self._controller.replay_session_reading
        )
        self.play_button.clicked.connect(self._toggle_playback)
        self.stop_button.clicked.connect(self._controller.stop)
        self.previous_button.clicked.connect(self._controller.previous)
        self.next_button.clicked.connect(self._controller.next)
        self.open_accessibility_settings_button.clicked.connect(
            self._open_accessibility_settings
        )
        self.voice_combo.currentIndexChanged.connect(self._voice_changed)
        self.rate_combo.currentIndexChanged.connect(self._rate_changed)

        open_action = QAction("Mở sách", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_book_dialog)
        self.addAction(open_action)

    def _start_model_setup(self) -> None:
        self.prepare_model_button.setEnabled(False)
        self.cancel_model_button.show()
        self.model_progress.setRange(0, 100)
        self.model_status.setText("Đang chuẩn bị giọng đọc…")
        self._model_setup.start()

    def _cancel_model_setup(self) -> None:
        self.cancel_model_button.setEnabled(False)
        self.model_status.setText("Đang dừng sau bước tải hiện tại…")
        self._model_setup.cancel()

    def _on_model_progress(self, progress: float, message: str) -> None:
        self.model_progress.setValue(round(max(0.0, min(progress, 1.0)) * 100))
        self.model_status.setText(message)

    def _on_model_ready(self, voices: object) -> None:
        self._model_ready = True
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        for voice in voices:
            label = voice.label.replace("—", "-").replace("–", "-")
            self.voice_combo.addItem(label, voice.id)
        self.voice_combo.blockSignals(False)
        self.root_stack.setCurrentWidget(self.reader_page)
        self._render_state(self._controller.state)

    def _on_model_failed(self, message: str) -> None:
        self._model_ready = False
        self.prepare_model_button.setText("Thử lại")
        self.prepare_model_button.setEnabled(True)
        self.cancel_model_button.setEnabled(True)
        self.cancel_model_button.hide()
        self.model_status.setText(message)

    def _on_model_cancelled(self) -> None:
        self._model_ready = False
        self.prepare_model_button.setEnabled(True)
        self.cancel_model_button.setEnabled(True)
        self.cancel_model_button.hide()
        self.model_status.setText("Đã hủy chuẩn bị giọng đọc.")

    def _render_state(self, state: ReaderViewState) -> None:
        self._rendering = True
        try:
            self.library_view.render(state.library, state.active_book_id)
            self._render_active_book_title(state)
            self.library_view.book_reader_view.render_chapters(
                state.chapters,
                state.active_chapter_id,
            )
            self.library_view.book_reader_view.render_segments(
                state.segments,
                state.active_segment_id,
                state.figures,
            )
            self.library_view.book_reader_view.set_selection_available(
                self._model_ready and state.can_play
            )
            self._sync_voice(state.voice_id)
            self._sync_rate(state.rate)
            has_book = state.active_book_id is not None
            if self._model_ready and not self._workspace_initialized:
                self._show_feature(0)
                if has_book:
                    self.library_view.show_reader()
                else:
                    self.library_view.show_library()
                self._workspace_initialized = True
            self.toolbar_open_button.setVisible(bool(state.library))
            self.toolbar_paste_button.setVisible(bool(state.library))
            self._render_playback_controls(state)
            self._render_session_history(state)
            self.external_reading_view.render(
                state.external_reading_state,
                state.session_history,
                state.error,
            )
            self.voice_combo.setEnabled(self._model_ready)
            self.rate_combo.setEnabled(self._model_ready)
            self.status_label.setText(state.status)
            self._render_reading_location(state)
            self.error_label.setText(state.error or "")
            self._render_contextual_status(state)
        finally:
            self._rendering = False

    def _render_playback_controls(self, state: ReaderViewState) -> None:
        reader_visible = (
            self.feature_stack.currentWidget() is self.library_view
            and self.library_view.is_reader_visible()
        )
        active_transport = state.playback_state in {
            PlaybackState.PLAYING,
            PlaybackState.PAUSED,
        }
        loading = state.playback_state is PlaybackState.LOADING
        self.play_button.setEnabled(
            self._model_ready
            and not loading
            and (active_transport or (reader_visible and state.can_play))
        )
        can_navigate = (
            self._model_ready
            and reader_visible
            and state.can_play
            and not loading
            and not state.is_selection_playback
        )
        self.previous_button.setEnabled(can_navigate)
        self.next_button.setEnabled(can_navigate)
        self.stop_button.setEnabled(state.playback_state is not PlaybackState.IDLE)
        self.play_button.setText(
            "Tạm dừng"
            if state.playback_state is PlaybackState.PLAYING
            else "Tiếp tục"
            if state.playback_state is PlaybackState.PAUSED
            else "Đọc"
        )

    def _render_reading_location(self, state: ReaderViewState) -> None:
        reader_visible = (
            self.feature_stack.currentWidget() is self.library_view
            and self.library_view.is_reader_visible()
        )
        self.reading_location_label.setText(state.reading_location)
        self.reading_location_label.setVisible(
            reader_visible and bool(state.reading_location)
        )

    def _render_contextual_status(self, state: ReaderViewState) -> None:
        external_visible = (
            self.feature_stack.currentWidget() is self.external_reading_view
        )
        self.status_label.setVisible(
            not external_visible or state.playback_state is not PlaybackState.IDLE
        )
        self.error_label.setVisible(bool(state.error) and not external_visible)
        self.open_accessibility_settings_button.setVisible(
            state.can_open_accessibility_settings and not external_visible
        )

    def _render_session_history(self, state: ReaderViewState) -> None:
        history = state.session_history
        self.session_history_button.setEnabled(self._model_ready and bool(history))
        self.session_history_button.setToolTip(
            f"Mở {len(history)} nội dung gần đây"
            if history
            else "Chưa có nội dung đã đọc trong phiên"
        )
        if history == self._rendered_session_history:
            return
        self._rendered_session_history = history
        self.session_history_menu.clear()
        for item in history:
            action = self.session_history_menu.addAction(
                f"{item.source_label} · {item.preview}"
            )
            action.setData(item.id)
            action.setToolTip(item.preview)
            action.triggered.connect(
                lambda _checked=False, item_id=item.id: (
                    self._controller.replay_session_reading(item_id)
                )
            )
        if history:
            self.session_history_menu.addSeparator()
            clear_action = self.session_history_menu.addAction(
                "Xóa lịch sử phiên"
            )
            clear_action.triggered.connect(self._controller.clear_session_history)

    def _render_active_book_title(self, state: ReaderViewState) -> None:
        title = next(
            (
                item.title
                for item in state.library
                if item.id == state.active_book_id
            ),
            "",
        )
        self.library_view.book_reader_view.set_active_book_title(title)

    def _sync_voice(self, voice_id: str) -> None:
        index = self.voice_combo.findData(voice_id)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)

    def _sync_rate(self, rate: float) -> None:
        index = self.rate_combo.findData(rate)
        if index >= 0:
            self.rate_combo.setCurrentIndex(index)

    def _activate_library_book(self, book_id: str) -> None:
        self._controller.select_book(book_id)
        if self._controller.state.active_book_id == book_id:
            self._show_feature(0)
            self.library_view.show_reader()

    def _toggle_playback(self) -> None:
        state = self._controller.state.playback_state
        if state is PlaybackState.PLAYING:
            self._controller.pause()
        elif state is PlaybackState.PAUSED:
            self._controller.resume()
        else:
            self._controller.play_current()

    def show_paste_view(self) -> None:
        self._show_feature(1)
        self.paste_text_view.text_edit.setFocus()

    def _read_pasted_text(self, text: str) -> None:
        self._controller.read_pasted_text(text)

    def _feature_changed(self, index: int) -> None:
        if 0 <= index < self.feature_stack.count():
            self.feature_stack.setCurrentIndex(index)
        if index == 1:
            self.paste_text_view.text_edit.setFocus()
        self._render_playback_controls(self._controller.state)
        self._render_reading_location(self._controller.state)
        self._render_contextual_status(self._controller.state)

    def _library_surface_changed(self) -> None:
        self._render_playback_controls(self._controller.state)
        self._render_reading_location(self._controller.state)

    def _show_feature(self, index: int) -> None:
        self.feature_navigation.setCurrentIndex(index)
        self.feature_stack.setCurrentIndex(index)

    def _voice_changed(self, index: int) -> None:
        if not self._rendering and index >= 0:
            voice_id = self.voice_combo.itemData(index)
            if voice_id:
                self._controller.set_voice(str(voice_id))

    def _rate_changed(self, index: int) -> None:
        if not self._rendering and index >= 0:
            rate = self.rate_combo.itemData(index)
            if rate is not None:
                self._controller.set_rate(float(rate))

    def open_book_dialog(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Mở sách",
            str(Path.home()),
            "Sách (*.pdf *.epub);;PDF (*.pdf);;EPUB (*.epub)",
        )
        if filename:
            self.import_path(Path(filename))

    def import_path(self, path: Path) -> None:
        self._controller.import_book(Path(path))
        if (
            self._controller.state.active_book_id is not None
            and self._controller.state.error is None
        ):
            self._show_feature(0)
            self.library_view.show_reader()

    @staticmethod
    def accepts_path(path: Path) -> bool:
        return Path(path).suffix.lower() in {".pdf", ".epub"}

    @classmethod
    def _drop_path(cls, mime_data: QMimeData) -> Path | None:
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if cls.accepts_path(path):
                return path
        return None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._drop_path(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        path = self._drop_path(event.mimeData())
        if path is None:
            event.ignore()
            return
        self.import_path(path)
        event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._controller.stop()
        self._model_setup.cancel()
        super().closeEvent(event)
