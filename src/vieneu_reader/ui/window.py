"""Native-control Qt window for the ReadEase MVP."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMimeData, QSignalBlocker, Qt, Signal
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
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vieneu_reader.config import default_app_root
from vieneu_reader.identity import PRODUCT_DISPLAY_NAME
from vieneu_reader.integrations.macos_settings import (
    open_accessibility_settings as open_accessibility_settings_pane,
)
from vieneu_reader.integrations.selection_shortcut import (
    DEFAULT_SHORTCUT,
    ReadOnCopyPreferenceStore,
    Shortcut,
    ShortcutPreferenceStore,
)
from vieneu_reader.playback.coordinator import PlaybackState
from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore
from vieneu_reader.speech.vieneu import DEFAULT_PRECISION, PRECISIONS

from .controller import ReaderController, ReaderViewState
from .external_reading_view import ExternalReadingView
from vieneu_reader.integrations.apple_books import (
    AppleBooksLibrary,
    AmbiguousAsset,
    AppleBooksNotPermitted,
    AppleBooksUnavailable,
    AppleBooksUnreadable,
    SameBook,
    build_transfer_plan,
)
from vieneu_reader.integrations.apple_books_writer import (
    AppleBooksBusy,
    NothingToCopy,
    apple_books_is_running,
    back_up,
    copy_annotations,
    prune_backups,
)

from .transfer_notes_view import TransferNotesView
from .i18n import Language, LanguagePreferenceStore, Localizer
from .library_view import LibraryView
from .paste_view import PasteTextView

_BACKUP_DIRECTORY = "AppleBooksBackups"


def _backup_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


class ReaderWindow(QMainWindow):
    selectionShortcutChanged = Signal(object)
    readOnCopyChanged = Signal(bool)

    def __init__(
        self,
        controller: ReaderController,
        model_setup: Any,
        parent: QWidget | None = None,
        *,
        open_accessibility_settings: Callable[[], object] | None = None,
        localizer: Localizer | None = None,
        language_store: LanguagePreferenceStore | None = None,
        selection_shortcut: Shortcut | None = None,
        shortcut_store: ShortcutPreferenceStore | None = None,
        read_on_copy: bool = False,
        read_on_copy_store: ReadOnCopyPreferenceStore | None = None,
        voice_quality_store: VoiceQualityPreferenceStore | None = None,
        apple_books: AppleBooksLibrary | None = None,
        backup_root: Path | None = None,
        confirm_transfer: Callable[[str, str], bool] | None = None,
        books_is_running: Callable[[], bool] = apple_books_is_running,
    ):
        super().__init__(parent)
        self._controller = controller
        self._model_setup = model_setup
        self._apple_books = apple_books
        self._backup_root = backup_root
        self._confirm_transfer_with = confirm_transfer
        self._books_is_running = books_is_running
        self._language_store = language_store
        self._shortcut_store = shortcut_store
        self._read_on_copy_store = read_on_copy_store
        self._voice_quality_store = voice_quality_store
        self._selection_shortcut = selection_shortcut or DEFAULT_SHORTCUT
        self._read_on_copy = bool(read_on_copy)
        self._localizer = localizer or Localizer(
            language_store.load() if language_store is not None else Language.VIETNAMESE
        )
        self._open_accessibility_settings = (
            open_accessibility_settings or open_accessibility_settings_pane
        )
        self._model_ready = False
        self._model_setup_failed = False
        self._rendering = False
        self._workspace_initialized = False
        self._rendered_session_history = None
        self._model_status_source = "Sẵn sàng tải giọng đọc."
        self._available_voices: tuple[Any, ...] = ()

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
        self._retranslate()
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

        self.model_setup_title = QLabel()
        title_font = QFont(self.model_setup_title.font())
        title_font.setPointSize(title_font.pointSize() + 8)
        title_font.setBold(True)
        self.model_setup_title.setFont(title_font)
        self.model_setup_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.model_setup_title)

        self.model_setup_description = QLabel()
        self.model_setup_description.setWordWrap(True)
        self.model_setup_description.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.model_setup_description.setMaximumWidth(620)
        layout.addWidget(
            self.model_setup_description,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        language_row = QHBoxLayout()
        language_row.addStretch(1)
        self.setup_language_label = QLabel()
        language_row.addWidget(self.setup_language_label)
        self.setup_language_combo = self._build_language_combo("setupLanguageCombo")
        language_row.addWidget(self.setup_language_combo)
        language_row.addStretch(1)
        layout.addLayout(language_row)

        quality_row = QHBoxLayout()
        quality_row.addStretch(1)
        self.setup_quality_label = QLabel()
        quality_row.addWidget(self.setup_quality_label)
        self.setup_quality_combo = QComboBox()
        self.setup_quality_combo.setObjectName("setupQualityCombo")
        for precision in PRECISIONS:
            self.setup_quality_combo.addItem("", precision)
        quality_row.addWidget(self.setup_quality_combo)
        quality_row.addStretch(1)
        layout.addLayout(quality_row)

        # Shown only once the choice actually changes, so the screen stays calm
        # for the many people who never touch it.
        self.quality_restart_note = QLabel()
        self.quality_restart_note.setWordWrap(True)
        self.quality_restart_note.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.quality_restart_note.setMaximumWidth(620)
        self.quality_restart_note.hide()
        layout.addWidget(
            self.quality_restart_note,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        self.model_progress = QProgressBar()
        self.model_progress.setObjectName("modelProgress")
        self.model_progress.setRange(0, 100)
        self.model_progress.setValue(0)
        self.model_progress.setTextVisible(True)
        self.model_progress.setMaximumWidth(520)
        layout.addWidget(self.model_progress, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.model_status = QLabel()
        self.model_status.setWordWrap(True)
        self.model_status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.model_status)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.prepare_model_button = QPushButton()
        self.prepare_model_button.setObjectName("prepareModelButton")
        self.cancel_model_button = QPushButton()
        self.cancel_model_button.setObjectName("cancelModelButton")
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
        self.toolbar_open_button = QPushButton()
        self.toolbar_open_button.setObjectName("openBookButton")
        header.addWidget(self.toolbar_open_button)
        self.toolbar_paste_button = QPushButton()
        self.toolbar_paste_button.setObjectName("pasteTextButton")
        header.addWidget(self.toolbar_paste_button)
        self.language_label = QLabel()
        header.addWidget(self.language_label)
        self.language_combo = self._build_language_combo("languageCombo")
        header.addWidget(self.language_combo)
        root.addLayout(header)

        self.feature_navigation = QTabBar()
        self.feature_navigation.setObjectName("featureNavigation")
        self.feature_navigation.setExpanding(False)
        # A tab bar draws a base to join itself to the framed page beneath it.
        # This one sits above a plain stacked widget with no frame, so the base
        # rendered as a stray rounded edge attached to nothing.
        self.feature_navigation.setDrawBase(False)
        for _index in range(4):
            self.feature_navigation.addTab("")
        # Left-aligned under the app title rather than floating in the middle of
        # the window, so the tabs read as belonging to the content below them.
        navigation_row = QHBoxLayout()
        navigation_row.setContentsMargins(0, 0, 0, 0)
        navigation_row.addWidget(self.feature_navigation)
        navigation_row.addStretch(1)
        root.addLayout(navigation_row)

        self.feature_stack = QStackedWidget()
        self.feature_stack.setObjectName("featureStack")
        self.library_view = LibraryView(localizer=self._localizer)
        self.paste_text_view = PasteTextView(localizer=self._localizer)
        self.external_reading_view = ExternalReadingView(
            localizer=self._localizer,
            shortcut=self._selection_shortcut,
            read_on_copy=self._read_on_copy,
        )
        self.transfer_notes_view = TransferNotesView(localizer=self._localizer)
        for feature_view in (
            self.library_view,
            self.paste_text_view,
            self.external_reading_view,
            self.transfer_notes_view,
        ):
            self.feature_stack.addWidget(feature_view)
        root.addWidget(self.feature_stack, 1)

        spare_row = QHBoxLayout()
        spare_row.addStretch(1)
        self.spare_build_label = QLabel()
        self.spare_build_label.setWordWrap(True)
        spare_row.addWidget(self.spare_build_label)
        self.spare_build_button = QPushButton()
        self.spare_build_button.setObjectName("removeSpareBuildButton")
        spare_row.addWidget(self.spare_build_button)
        spare_row.addStretch(1)
        self.spare_build_row = QWidget()
        self.spare_build_row.setLayout(spare_row)
        self.spare_build_row.hide()
        root.addWidget(self.spare_build_row)

        player = QFrame()
        player.setFrameShape(QFrame.Shape.StyledPanel)
        player_layout = QHBoxLayout(player)
        player_layout.setContentsMargins(12, 8, 12, 8)
        player_layout.setSpacing(8)

        self.previous_button = QToolButton()
        self.play_button = QPushButton()
        self.play_button.setObjectName("playButton")
        self.stop_button = QToolButton()
        self.next_button = QToolButton()
        self.session_history_button = QToolButton()
        self.session_history_button.setObjectName("sessionHistoryButton")
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
        self.voice_label = QLabel()
        player_layout.addWidget(self.voice_label)
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(170)
        player_layout.addWidget(self.voice_combo)
        self.rate_label = QLabel()
        player_layout.addWidget(self.rate_label)
        self.quality_label = QLabel()
        player_layout.addWidget(self.quality_label)
        self.quality_combo = QComboBox()
        self.quality_combo.setObjectName("qualityCombo")
        for precision in PRECISIONS:
            self.quality_combo.addItem("", precision)
        player_layout.addWidget(self.quality_combo)
        self.rate_combo = QComboBox()
        # Finer steps where reading actually happens: the jump from 1.0 to
        # 1.25 skipped the speeds this reader uses most.
        for rate in (0.5, 0.75, 1.0, 1.15, 1.2, 1.25, 1.5, 2.0):
            self.rate_combo.addItem(f"{rate:g}×", rate)
        player_layout.addWidget(self.rate_combo)
        root.addWidget(player)

        status_row = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        status_row.addWidget(self.status_label)
        self.reading_location_label = QLabel()
        self.reading_location_label.setObjectName("readingLocationLabel")
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
        self.open_accessibility_settings_button = QPushButton()
        self.open_accessibility_settings_button.setObjectName(
            "openAccessibilitySettingsButton"
        )
        self.open_accessibility_settings_button.hide()
        status_row.addWidget(self.open_accessibility_settings_button)
        root.addLayout(status_row)
        return page

    @staticmethod
    def _build_language_combo(object_name: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(object_name)
        combo.addItem("🇻🇳 Tiếng Việt", Language.VIETNAMESE.value)
        combo.addItem("🇬🇧 English", Language.ENGLISH.value)
        return combo

    def _load_transfer_books(self, index: int) -> None:
        """Load the Apple Books library the first time its tab is opened.

        Reading it eagerly at startup would touch a person's book library for a
        feature they may never open, so this waits until they ask.
        """

        if self.feature_stack.widget(index) is not self.transfer_notes_view:
            return
        if self._apple_books is None:
            self.transfer_notes_view.show_unavailable(
                self._localizer.text("transfer.unsupported")
            )
            return
        try:
            self.transfer_notes_view.set_books(self._apple_books.books())
        except AppleBooksNotPermitted:
            self.transfer_notes_view.show_unavailable(
                self._localizer.text("transfer.not_permitted")
            )
        except (AppleBooksUnavailable, AppleBooksUnreadable) as error:
            self.transfer_notes_view.show_unavailable(
                self._localizer.runtime(str(error))
            )

    def _preview_transfer(self, source_asset_id: str, target_asset_id: str) -> None:
        plan = self._plan_or_report(source_asset_id, target_asset_id)
        if plan is not None:
            self.transfer_notes_view.show_plan(plan)

    def _plan_or_report(self, source_asset_id: str, target_asset_id: str):
        """Build the plan, or put the reason on screen and return None."""

        if self._apple_books is None:
            return None
        try:
            plan = build_transfer_plan(
                self._apple_books, source_asset_id, target_asset_id
            )
        except AppleBooksNotPermitted:
            self.transfer_notes_view.show_unavailable(
                self._localizer.text("transfer.not_permitted")
            )
            return
        except SameBook:
            # The view disables the button for this; belt and braces.
            return
        except AmbiguousAsset:
            self.transfer_notes_view.show_unavailable(
                self._localizer.text("transfer.ambiguous")
            )
            return
        except LookupError:
            # str(UnknownAsset) is the bare asset id - meaningless to read.
            self.transfer_notes_view.show_unavailable(
                self._localizer.text("transfer.book_gone")
            )
            return
        except (AppleBooksUnavailable, AppleBooksUnreadable) as error:
            self.transfer_notes_view.show_unavailable(
                self._localizer.runtime(str(error))
            )
            return None
        return plan

    def _transfer_notes(self, source_asset_id: str, target_asset_id: str) -> None:
        text = self._localizer.text
        # Rebuild the plan rather than trusting the view's cached count: the
        # library may have changed since the preview, and this decides what the
        # confirmation promises.
        plan = self._plan_or_report(source_asset_id, target_asset_id)
        if plan is None:
            return
        if not plan.items:
            self.transfer_notes_view.show_transfer_result(text("transfer.no_notes"))
            return
        if not plan.copyable:
            # Everything is over there already. Stop before the dialog rather
            # than asking someone to approve a copy of nothing.
            self.transfer_notes_view.show_transfer_result(
                text("transfer.all_already_there", count=len(plan.items))
            )
            return
        if self._apple_books is None:
            return
        database = self._apple_books.annotation_database
        if database is None:
            self.transfer_notes_view.show_transfer_result(text("transfer.unsupported"))
            return
        # The number someone approves must be the number that gets written, and
        # the writer skips what is already there.
        if not self._confirm_transfer(len(plan.copyable), plan.target.title):
            return
        # Ask again after the dialog: Apple Books may have been opened while it
        # was up, and a backup taken then would capture a torn write-ahead log.
        if self._books_is_running():
            self.transfer_notes_view.show_transfer_result(text("transfer.books_open"))
            return

        backup_root = self._backup_root or (default_app_root() / _BACKUP_DIRECTORY)
        destination = backup_root / _backup_stamp()
        try:
            backup = back_up(database, destination)
        except OSError:
            self.transfer_notes_view.show_transfer_result(
                text("transfer.backup_failed")
            )
            return

        try:
            written = copy_annotations(
                database,
                source_asset_id,
                target_asset_id,
                backup=backup,
                # Only the positions the plan proved mean the same thing over
                # there. The rest stay listed and unwritten.
                only_locations={
                    item.annotation.location for item in plan.copyable
                },
                books_is_running=self._books_is_running,
            )
        except AppleBooksBusy:
            self.transfer_notes_view.show_transfer_result(text("transfer.books_open"))
            return
        except NothingToCopy:
            # Everything in the plan is already on the target - the second press
            # of a copy that already worked. Nothing was written; say so plainly
            # rather than reporting it as a failure.
            self.transfer_notes_view.show_transfer_result(
                text("transfer.already_there")
            )
            return
        except Exception:
            # copy_annotations is atomic, so the library is as it was; say where
            # the backup is anyway, because that is what someone will look for.
            self.transfer_notes_view.show_transfer_result(
                text("transfer.copy_failed", path=str(backup))
            )
            return
        # Only once the write has landed: an older backup is worth more than a
        # tidy folder right up until the new one exists.
        prune_backups(backup_root)
        self.transfer_notes_view.show_transfer_result(
            text("transfer.copied", count=written, book=plan.target.title)
        )

    def _confirm_transfer(self, count: int, book: str) -> bool:
        text = self._localizer.text
        body = "\n\n".join(
            (
                text("transfer.confirm_body", count=count, book=book),
                text("transfer.confirm_icloud"),
            )
        )
        if self._confirm_transfer_with is not None:
            return bool(self._confirm_transfer_with(text("transfer.confirm_title"), body))
        answer = QMessageBox.question(
            self,
            text("transfer.confirm_title"),
            body,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _connect_actions(self) -> None:
        self.prepare_model_button.clicked.connect(self._start_model_setup)
        self.spare_build_button.clicked.connect(self._remove_spare_build)
        for combo in (self.setup_quality_combo, self.quality_combo):
            combo.currentIndexChanged.connect(self._quality_changed)
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
        self.external_reading_view.shortcutRecorded.connect(
            self.selectionShortcutChanged.emit
        )
        self.transfer_notes_view.previewRequested.connect(self._preview_transfer)
        self.transfer_notes_view.transferRequested.connect(self._transfer_notes)
        self.external_reading_view.readOnCopyChanged.connect(
            self._read_on_copy_changed
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
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.setup_language_combo.currentIndexChanged.connect(
            self._language_changed
        )

        self.open_action = QAction(self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_book_dialog)
        self.addAction(self.open_action)

    def set_selection_shortcut(self, shortcut: Shortcut) -> None:
        """Follow, and remember, the combination the helper registered."""

        self._selection_shortcut = shortcut
        self.external_reading_view.set_shortcut(shortcut)
        if self._shortcut_store is not None:
            self._shortcut_store.save(shortcut)

    def _read_on_copy_changed(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._read_on_copy:
            return
        self._read_on_copy = enabled
        if self._read_on_copy_store is not None:
            self._read_on_copy_store.save(enabled)
        self.readOnCopyChanged.emit(enabled)

    def _language_changed(self, index: int) -> None:
        combo = self.sender()
        if not isinstance(combo, QComboBox) or index < 0:
            return
        language = Language.parse(combo.itemData(index))
        if language is self._localizer.language:
            return
        self._localizer.set_language(language)
        if self._language_store is not None:
            self._language_store.save(language)
        self._rendered_session_history = None
        self._retranslate()

    def _sync_language_controls(self) -> None:
        for combo in (self.language_combo, self.setup_language_combo):
            blocker = QSignalBlocker(combo)
            index = combo.findData(self._localizer.language.value)
            if index >= 0:
                combo.setCurrentIndex(index)
            del blocker

    def _retranslate(self) -> None:
        text = self._localizer.text
        self._sync_language_controls()
        for label in (self.language_label, self.setup_language_label):
            label.setText(text("language.label"))
        for combo in (self.language_combo, self.setup_language_combo):
            combo.setAccessibleName(text("language.accessible"))
        self.model_setup_title.setText(text("model.title"))
        self.model_setup_description.setText(text("model.description"))
        self.setup_quality_label.setText(text("model.quality"))
        self.quality_label.setText(text("player.quality"))
        self._sync_quality_controls()
        self.quality_restart_note.setText(text("model.quality_restart"))
        self._refresh_spare_build()
        prepare_key = "model.retry" if self._model_setup_failed else "model.prepare"
        self.prepare_model_button.setText(text(prepare_key))
        self.prepare_model_button.setAccessibleName(
            text("model.prepare_accessible")
        )
        self.cancel_model_button.setText(text("model.cancel"))
        self.cancel_model_button.setAccessibleName(text("model.cancel_accessible"))
        self._set_model_status(self._model_status_source)
        self.toolbar_open_button.setText(text("toolbar.open"))
        self.toolbar_open_button.setAccessibleName(text("toolbar.open_accessible"))
        self.toolbar_paste_button.setText(text("toolbar.paste"))
        self.toolbar_paste_button.setAccessibleName(text("toolbar.paste_accessible"))
        self.feature_navigation.setAccessibleName(text("nav.accessible"))
        for index, key in enumerate(
            ("nav.library", "nav.paste", "nav.external", "nav.transfer")
        ):
            self.feature_navigation.setTabText(index, text(key))
        self.library_view.retranslate()
        self.paste_text_view.retranslate()
        self.external_reading_view.retranslate()
        self.transfer_notes_view.retranslate()
        self.previous_button.setText(text("player.previous"))
        self.previous_button.setAccessibleName(text("player.previous_accessible"))
        self.play_button.setAccessibleName(text("player.play_accessible"))
        self.stop_button.setText(text("player.stop"))
        self.stop_button.setAccessibleName(text("player.stop_accessible"))
        self.next_button.setText(text("player.next"))
        self.next_button.setAccessibleName(text("player.next_accessible"))
        self.session_history_button.setText(text("player.history"))
        self.session_history_button.setAccessibleName(
            text("player.history_accessible")
        )
        self.voice_label.setText(text("player.voice"))
        self.voice_combo.setAccessibleName(text("player.voice_accessible"))
        self._populate_voice_combo()
        self.rate_label.setText(text("player.speed"))
        self.rate_combo.setAccessibleName(text("player.speed_accessible"))
        self.reading_location_label.setAccessibleName(
            text("status.location_accessible")
        )
        self.open_accessibility_settings_button.setText(text("permission.open"))
        self.open_accessibility_settings_button.setAccessibleName(
            text("permission.open_accessible")
        )
        self.open_action.setText(text("dialog.open_title"))
        self._render_state(self._controller.state)

    def _set_model_status(self, source: str) -> None:
        self._model_status_source = source
        self.model_status.setText(self._localizer.runtime(source))

    def _start_model_setup(self) -> None:
        self._model_setup_failed = False
        self.prepare_model_button.setEnabled(False)
        self.cancel_model_button.show()
        self.model_progress.setRange(0, 100)
        self._set_model_status("Đang chuẩn bị giọng đọc…")
        self._model_setup.start()

    def _cancel_model_setup(self) -> None:
        self.cancel_model_button.setEnabled(False)
        self._set_model_status("Đang dừng sau bước tải hiện tại…")
        self._model_setup.cancel()

    def _on_model_progress(self, progress: float, message: str) -> None:
        self.model_progress.setValue(round(max(0.0, min(progress, 1.0)) * 100))
        self._set_model_status(message)

    def _on_model_ready(self, voices: object) -> None:
        self._model_ready = True
        self._model_setup_failed = False
        self._available_voices = tuple(voices)
        self._controller.reconcile_voice(
            tuple(voice.id for voice in self._available_voices)
        )
        self._populate_voice_combo()
        self.root_stack.setCurrentWidget(self.reader_page)
        self._render_state(self._controller.state)

    def _populate_voice_combo(self) -> None:
        selected_voice_id = self.voice_combo.currentData()
        if selected_voice_id is None:
            selected_voice_id = self._controller.state.voice_id
        blocker = QSignalBlocker(self.voice_combo)
        self.voice_combo.clear()
        for voice in self._available_voices:
            label = voice.label.replace("—", "-").replace("–", "-")
            self.voice_combo.addItem(self._localizer.runtime(label), voice.id)
        index = self.voice_combo.findData(selected_voice_id)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        del blocker

    def _on_model_failed(self, message: str) -> None:
        self._model_ready = False
        self._model_setup_failed = True
        self.prepare_model_button.setText(self._localizer.text("model.retry"))
        self.prepare_model_button.setEnabled(True)
        self.cancel_model_button.setEnabled(True)
        self.cancel_model_button.hide()
        self._set_model_status(message)

    def _on_model_cancelled(self) -> None:
        self._model_ready = False
        self._model_setup_failed = False
        self.prepare_model_button.setEnabled(True)
        self.cancel_model_button.setEnabled(True)
        self.cancel_model_button.hide()
        self._set_model_status("Đã hủy chuẩn bị giọng đọc.")

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
            self.status_label.setText(self._localizer.runtime(state.status))
            self._render_reading_location(state)
            self.error_label.setText(self._localizer.runtime(state.error))
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
            self._localizer.text("player.pause")
            if state.playback_state is PlaybackState.PLAYING
            else self._localizer.text("player.resume")
            if state.playback_state is PlaybackState.PAUSED
            else self._localizer.text("player.play")
        )

    def _render_reading_location(self, state: ReaderViewState) -> None:
        reader_visible = (
            self.feature_stack.currentWidget() is self.library_view
            and self.library_view.is_reader_visible()
        )
        self.reading_location_label.setText(
            self._localizer.runtime(state.reading_location)
        )
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
            self._localizer.text("player.history_count", count=len(history))
            if history
            else self._localizer.text("player.history_empty")
        )
        if history == self._rendered_session_history:
            return
        self._rendered_session_history = history
        self.session_history_menu.clear()
        for item in history:
            action = self.session_history_menu.addAction(
                f"{self._localizer.text(f'player.source.{item.source}')} · {item.preview}"
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
                self._localizer.text("player.history_clear")
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
        self._load_transfer_books(index)
        self._render_playback_controls(self._controller.state)
        self._render_reading_location(self._controller.state)
        self._render_contextual_status(self._controller.state)

    def _library_surface_changed(self) -> None:
        self._render_playback_controls(self._controller.state)
        self._render_reading_location(self._controller.state)

    def _show_feature(self, index: int) -> None:
        self.feature_navigation.setCurrentIndex(index)
        self.feature_stack.setCurrentIndex(index)

    def _sync_quality_controls(self) -> None:
        text = self._localizer.text
        chosen = (
            self._voice_quality_store.load()
            if self._voice_quality_store is not None
            else DEFAULT_PRECISION
        )
        for combo in (self.setup_quality_combo, self.quality_combo):
            blocker = QSignalBlocker(combo)
            combo.setAccessibleName(text("model.quality_accessible"))
            for index in range(combo.count()):
                precision = combo.itemData(index)
                suffix = "standard" if precision == DEFAULT_PRECISION else "maximum"
                combo.setItemText(index, text(f"model.quality_{suffix}"))
            position = combo.findData(chosen)
            if position >= 0:
                combo.setCurrentIndex(position)
            del blocker

    @staticmethod
    def _readable_size(byte_count: int) -> str:
        if byte_count >= 1024 * 1024 * 1024:
            return f"{byte_count / 1024 / 1024 / 1024:.1f} GB"
        return f"{round(byte_count / 1024 / 1024)} MB"

    def _refresh_spare_build(self) -> None:
        spare = None
        if hasattr(self._model_setup, "unused_build"):
            spare = self._model_setup.unused_build()
        if spare is None:
            self.spare_build_row.hide()
            return
        precision, size = spare
        text = self._localizer.text
        suffix = "standard" if precision == DEFAULT_PRECISION else "maximum"
        self.spare_build_label.setText(
            text(
                "model.spare_build",
                name=text(f"model.quality_{suffix}").split("·")[0].strip(),
                size=self._readable_size(size),
            )
        )
        self.spare_build_button.setText(text("model.spare_remove"))
        self.spare_build_row.show()

    def _remove_spare_build(self) -> None:
        spare = self._model_setup.unused_build()
        if spare is None:
            self.spare_build_row.hide()
            return
        reclaimed = self._readable_size(spare[1])
        if self._model_setup.remove_unused_build():
            self._set_model_status(
                self._localizer.text("model.spare_removed", size=reclaimed)
            )
        else:
            self._set_model_status(self._localizer.text("model.spare_failed"))
        self._refresh_spare_build()

    def _quality_changed(self, index: int) -> None:
        combo = self.sender()
        if self._rendering or index < 0 or self._voice_quality_store is None:
            return
        if not isinstance(combo, QComboBox):
            return
        precision = combo.itemData(index)
        if not precision or precision == self._voice_quality_store.load():
            return
        self._voice_quality_store.save(str(precision))
        self._refresh_spare_build()
        # Both controls show the same choice, wherever it was made.
        self._sync_quality_controls()
        # The engine is built once at startup, so the change lands on reopen.
        self.quality_restart_note.show()
        self._set_model_status(self._localizer.text("model.quality_restart"))

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
            self._localizer.text("dialog.open_title"),
            str(Path.home()),
            self._localizer.text("dialog.open_filter"),
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
