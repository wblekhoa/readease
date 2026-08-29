from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import sqlite3
from dataclasses import replace
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAccessible, QTextCursor, QTextFormat
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QTextBrowser,
    QToolButton,
)

from vieneu_reader.config import AppPaths
from vieneu_reader.domain.models import Voice
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.integrations.selection_shortcut import (
    CMD_KEY,
    CONTROL_KEY,
    OPTION_KEY,
    ReadOnCopyPreferenceStore,
    Shortcut,
)
from vieneu_reader.playback.coordinator import PlaybackSnapshot, PlaybackState
from vieneu_reader.playback.preferences import VoicePreferenceStore
from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore
from vieneu_reader.storage.repository import LibraryRepository
from vieneu_reader.ui.controller import ExternalReadingState, ReaderController
from vieneu_reader.ui.i18n import Language, LanguagePreferenceStore
from vieneu_reader.integrations.apple_books import (
    Annotation as AppleAnnotation,
    AppleBooksUnavailable,
    Book as AppleBook,
)
from vieneu_reader.ui.window import ReaderWindow

from tests.importers.epub_fixture import make_epub, make_png
from tests.ui.test_controller import FakePlayback


class FakeModelSetup(QObject):
    progressChanged = Signal(float, str)
    ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, *, ready: bool, complete_on_start: bool = True):
        super().__init__()
        self.is_ready = ready
        self.complete_on_start = complete_on_start
        self.start_count = 0
        self.cancel_count = 0

    def start(self) -> None:
        self.start_count += 1
        self.progressChanged.emit(0.5, "Đang kiểm tra giọng đọc…")
        if self.complete_on_start:
            self.is_ready = True
            self.ready.emit(
                (
                    Voice("Adam", "Adam - Nam Bộ"),
                    Voice("Trúc Ly", "Trúc Ly - Bắc Bộ"),
                )
            )

    def cancel(self) -> None:
        self.cancel_count += 1
        self.cancelled.emit()

    spare: tuple[str, int] | None = None
    removal_succeeds = True
    removed = 0

    downloaded_builds: tuple[str, ...] = ()

    def is_build_downloaded(self, precision: str) -> bool:
        return precision in self.downloaded_builds

    def unused_build(self) -> tuple[str, int] | None:
        return self.spare

    def remove_unused_build(self) -> bool:
        self.removed += 1
        if not self.removal_succeeds:
            return False
        self.spare = None
        return True


class _FakeAppleBooks:
    """Two copies of one edition, five annotations on the first."""

    SOURCE = AppleBook("SRC", "Bản một", "urn:uuid:same", 0.30)
    TARGET = AppleBook("DST", "Bản hai", "urn:uuid:same", 0.60)
    # Declared so a test that forgets to point this at a database gets the
    # window's own "unsupported" path rather than an AttributeError, which Qt
    # swallows inside a slot and turns into a silent do-nothing.
    annotation_database = None

    def __init__(
        self,
        carried: tuple[int, ...] = (),
        root: Path | None = None,
        differs_at: int | None = None,
    ) -> None:
        self.calls = 0
        # Which of SRC's positions the target already holds. Without this the
        # double cannot express a partly-copied book, and no window test can
        # reach the already-there path at all.
        self.carried = carried
        # The plan compares the book files, so a double with no files behind it
        # can only ever produce "needs-review". Given a directory it writes a
        # matching pair, optionally differing in one chapter.
        self.source, self.target = self.SOURCE, self.TARGET
        if root is not None:
            from tests.integrations.test_apple_books import _make_book

            first = _make_book(root, "fake-src.epub")
            second = _make_book(root, "fake-dst.epub", differs_at=differs_at)
            self.source = replace(self.SOURCE, path=str(first))
            self.target = replace(self.TARGET, path=str(second))

    def books(self):
        self.calls += 1
        return (self.source, self.target)

    def book(self, asset_id):
        return self.source if asset_id == "SRC" else self.target

    def annotations(self, asset_id):
        return self.annotations_for(asset_id).get(asset_id, ())

    def annotations_for(self, *asset_ids):
        # `reads` counts trips to the database; `asked` records which books were
        # named. One read naming two books is not the same as two reads.
        self.reads = getattr(self, "reads", 0) + 1
        self.asked = getattr(self, "asked", [])
        self.asked.extend(asset_ids)
        def note(asset: str, index: int) -> AppleAnnotation:
            return AppleAnnotation(
                asset_id=asset,
                kind=2,
                location=f"epubcfi(/6/26!/4/{index})",
                selected_text="đoạn được bôi",
                note="ghi chú" if index % 2 else None,
            )

        found = {key: () for key in asset_ids}
        if "SRC" in found:
            # Numbered from one to match the annotation database fixture; the
            # copy intersects the two by position, so they must agree.
            found["SRC"] = tuple(note("SRC", index) for index in range(1, 6))
        if "DST" in found:
            found["DST"] = tuple(note("DST", index) for index in self.carried)
        return found


class SpareModelBuildTests(unittest.TestCase):
    """Only one build is ever downloaded; the other must not be stuck on disk."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.playback = FakePlayback(self.repository)
        self.windows: list[ReaderWindow] = []

    def tearDown(self) -> None:
        for window in self.windows:
            window.close()
        self.application.processEvents()
        self.repository.close()
        self.temporary_directory.cleanup()

    def make_window(self, model_setup) -> ReaderWindow:
        window = ReaderWindow(
            ReaderController(
                self.repository,
                self.service,
                self.playback,
                dispatch=lambda action: action(),
            ),
            model_setup,
        )
        self.windows.append(window)
        return window

    def test_nothing_is_shown_when_only_one_build_is_downloaded(self):
        window = self.make_window(FakeModelSetup(ready=True))

        self.assertFalse(window.spare_build_row.isVisibleTo(window))

    def test_the_unused_build_is_named_with_what_it_costs(self):
        setup = FakeModelSetup(ready=True)
        setup.spare = ("fp32", 453 * 1024 * 1024)

        window = self.make_window(setup)

        self.assertTrue(window.spare_build_row.isVisibleTo(window))
        self.assertIn("453 MB", window.spare_build_label.text())

    def test_removing_it_reports_the_space_and_takes_the_offer_away(self):
        setup = FakeModelSetup(ready=True)
        setup.spare = ("int8", 158 * 1024 * 1024)
        window = self.make_window(setup)

        window.spare_build_button.click()

        self.assertEqual(setup.removed, 1)
        self.assertFalse(window.spare_build_row.isVisibleTo(window))
        self.assertIn("158 MB", window.model_status.text())

    def test_a_removal_that_fails_says_so_and_keeps_the_offer(self):
        setup = FakeModelSetup(ready=True)
        setup.spare = ("int8", 158 * 1024 * 1024)
        setup.removal_succeeds = False
        window = self.make_window(setup)

        window.spare_build_button.click()

        self.assertTrue(window.spare_build_row.isVisibleTo(window))
        self.assertNotIn("158 MB", window.model_status.text())


class VoiceQualityChoiceTests(unittest.TestCase):
    """Both builds ship, so the choice has to be visible and it has to stick."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.playback = FakePlayback(self.repository)
        self.settings_path = self.paths.root / "settings.json"
        self.windows: list[ReaderWindow] = []

    def tearDown(self) -> None:
        for window in self.windows:
            window.close()
        self.application.processEvents()
        self.repository.close()
        self.temporary_directory.cleanup()

    def make_window(self, confirm_quality=None, model_setup=None) -> ReaderWindow:
        window = ReaderWindow(
            ReaderController(
                self.repository,
                self.service,
                self.playback,
                dispatch=lambda action: action(),
            ),
            model_setup or FakeModelSetup(ready=False, complete_on_start=False),
            voice_quality_store=VoiceQualityPreferenceStore(self.settings_path),
            confirm_quality=confirm_quality or (lambda title, body: True),
        )
        self.windows.append(window)
        return window

    def test_both_builds_are_offered_with_what_they_cost(self):
        window = self.make_window()

        offered = [
            window.setup_quality_combo.itemData(index)
            for index in range(window.setup_quality_combo.count())
        ]
        labels = " ".join(
            window.setup_quality_combo.itemText(index)
            for index in range(window.setup_quality_combo.count())
        )

        self.assertEqual(sorted(offered), ["fp32", "int8"])
        # The download size is the whole trade-off; it must be on the control.
        self.assertIn("158 MB", labels)
        self.assertIn("453 MB", labels)

    def test_the_saved_choice_is_the_one_selected(self):
        VoiceQualityPreferenceStore(self.settings_path).save("fp32")

        window = self.make_window()

        self.assertEqual(window.setup_quality_combo.currentData(), "fp32")

    def test_choosing_the_other_build_is_saved_and_explained(self):
        window = self.make_window()
        self.assertFalse(window.quality_restart_note.isVisibleTo(window))

        index = window.setup_quality_combo.findData("fp32")
        window.setup_quality_combo.setCurrentIndex(index)

        self.assertEqual(
            VoiceQualityPreferenceStore(self.settings_path).load(), "fp32"
        )
        # It only takes effect on reopen, so saying nothing would be a lie.
        self.assertTrue(window.quality_restart_note.isVisibleTo(window))

    def test_the_default_is_the_small_build(self):
        window = self.make_window()

        self.assertEqual(window.setup_quality_combo.currentData(), "int8")

    def test_the_choice_is_reachable_once_the_model_is_ready(self):
        """The setup screen is never shown again after the first download, so a
        control that only lives there cannot be used by anyone who has one."""
        window = ReaderWindow(
            ReaderController(
                self.repository,
                self.service,
                self.playback,
                dispatch=lambda action: action(),
            ),
            FakeModelSetup(ready=True),
            voice_quality_store=VoiceQualityPreferenceStore(self.settings_path),
        )
        self.windows.append(window)

        self.assertIs(window.root_stack.currentWidget(), window.reader_page)
        self.assertTrue(window.quality_combo.isVisibleTo(window.reader_page))
        self.assertEqual(
            sorted(
                window.quality_combo.itemData(i)
                for i in range(window.quality_combo.count())
            ),
            ["fp32", "int8"],
        )

    def test_changing_it_anywhere_updates_both_controls(self):
        """Two controls, one choice - either one must move the other."""
        for source, mirror in (
            ("quality_combo", "setup_quality_combo"),
            ("setup_quality_combo", "quality_combo"),
        ):
            with self.subTest(changed=source):
                window = self.make_window()
                changed = getattr(window, source)
                other = getattr(window, mirror)

                changed.setCurrentIndex(changed.findData("fp32"))

                self.assertEqual(changed.currentData(), "fp32")
                self.assertEqual(other.currentData(), "fp32")
                self.assertEqual(
                    VoiceQualityPreferenceStore(self.settings_path).load(), "fp32"
                )
                VoiceQualityPreferenceStore(self.settings_path).save("int8")

    def test_the_promised_download_matches_the_selected_build(self):
        window = self.make_window()

        self.assertIn("330 MB", window.model_setup_description.text())

        window.setup_quality_combo.setCurrentIndex(
            window.setup_quality_combo.findData("fp32")
        )

        self.assertIn("625 MB", window.model_setup_description.text())
        self.assertNotIn("330 MB", window.model_setup_description.text())

    def test_the_player_bar_names_the_builds_without_their_sizes(self):
        window = self.make_window()

        player_labels = " ".join(
            window.quality_combo.itemText(index)
            for index in range(window.quality_combo.count())
        )
        setup_labels = " ".join(
            window.setup_quality_combo.itemText(index)
            for index in range(window.setup_quality_combo.count())
        )

        self.assertNotIn("MB", player_labels)
        self.assertIn("Tiêu chuẩn", player_labels)
        self.assertIn("Cao nhất", player_labels)
        # The size stays where a download is about to start.
        self.assertIn("158 MB", setup_labels)

    def test_switching_from_the_player_bar_asks_first_and_names_the_download(self):
        """Its note lives on the setup page, which is gone by then, so without
        this question the switch would spend 453 MB with nothing said."""
        asked = []
        window = self.make_window(
            confirm_quality=lambda title, body: (asked.append(body), True)[1]
        )

        window.quality_combo.setCurrentIndex(window.quality_combo.findData("fp32"))

        self.assertEqual(len(asked), 1)
        self.assertIn("453 MB", asked[0])
        self.assertEqual(
            VoiceQualityPreferenceStore(self.settings_path).load(), "fp32"
        )

    def test_declining_leaves_the_choice_and_the_controls_where_they_were(self):
        window = self.make_window(confirm_quality=lambda title, body: False)

        window.quality_combo.setCurrentIndex(window.quality_combo.findData("fp32"))

        self.assertEqual(
            VoiceQualityPreferenceStore(self.settings_path).load(), "int8"
        )
        self.assertEqual(window.quality_combo.currentData(), "int8")
        self.assertEqual(window.setup_quality_combo.currentData(), "int8")

    def test_a_build_already_on_disk_is_not_announced_as_a_download(self):
        model_setup = FakeModelSetup(ready=False, complete_on_start=False)
        model_setup.downloaded_builds = ("fp32",)
        asked = []
        window = self.make_window(
            confirm_quality=lambda title, body: (asked.append(body), True)[1],
            model_setup=model_setup,
        )

        window.quality_combo.setCurrentIndex(window.quality_combo.findData("fp32"))

        self.assertEqual(len(asked), 1)
        self.assertNotIn("MB", asked[0])

    def test_the_setup_page_explains_instead_of_asking(self):
        asked = []
        window = self.make_window(
            confirm_quality=lambda title, body: (asked.append(body), True)[1]
        )

        index = window.setup_quality_combo.findData("fp32")
        window.setup_quality_combo.setCurrentIndex(index)

        self.assertEqual(asked, [])
        self.assertTrue(window.quality_restart_note.isVisibleTo(window))

    def test_a_saved_choice_shows_on_both_controls_at_startup(self):
        VoiceQualityPreferenceStore(self.settings_path).save("fp32")

        window = self.make_window()

        self.assertEqual(window.setup_quality_combo.currentData(), "fp32")
        self.assertEqual(window.quality_combo.currentData(), "fp32")


class RestoredVoiceIsShownTests(unittest.TestCase):
    """What the person sees must agree with what the app will actually read."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.playback = FakePlayback(self.repository)
        self.settings_path = self.paths.root / "settings.json"
        self.windows: list[ReaderWindow] = []

    def tearDown(self) -> None:
        for window in self.windows:
            window.close()
        self.application.processEvents()
        self.repository.close()
        self.temporary_directory.cleanup()

    def test_the_remembered_voice_and_speed_are_the_ones_on_screen(self):
        VoicePreferenceStore(self.settings_path).save("Trúc Ly", 1.25)
        controller = ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=lambda action: action(),
            voice_store=VoicePreferenceStore(self.settings_path),
        )

        window = ReaderWindow(controller, FakeModelSetup(ready=True))
        self.windows.append(window)

        self.assertEqual(window.voice_combo.currentData(), "Trúc Ly")
        self.assertEqual(window.rate_combo.currentData(), 1.25)

    def test_the_speeds_offered_cover_the_range_reading_happens_in(self):
        window = ReaderWindow(
            ReaderController(
                self.repository,
                self.service,
                self.playback,
                dispatch=lambda action: action(),
            ),
            FakeModelSetup(ready=True),
        )
        self.windows.append(window)

        offered = [
            window.rate_combo.itemData(index)
            for index in range(window.rate_combo.count())
        ]

        self.assertEqual(offered, sorted(offered))
        for wanted in (1.15, 1.2, 1.25):
            self.assertIn(wanted, offered)

    def test_a_voice_the_model_dropped_never_reaches_playback(self):
        VoicePreferenceStore(self.settings_path).save("Giọng đã biến mất", 1.0)
        controller = ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=lambda action: action(),
            voice_store=VoicePreferenceStore(self.settings_path),
        )

        window = ReaderWindow(controller, FakeModelSetup(ready=True))
        self.windows.append(window)
        controller.read_external_selection("Xin chào.")

        self.assertEqual(window.voice_combo.currentData(), controller.state.voice_id)
        self.assertEqual(self.playback.selection_calls[-1][1], "Adam")


class ReaderWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.playback = FakePlayback(self.repository)
        self.controller = ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=lambda action: action(),
        )
        self.sources = root / "sources"
        self.sources.mkdir()
        self.windows: list[ReaderWindow] = []

    def tearDown(self) -> None:
        for window in self.windows:
            window.close()
        self.application.processEvents()
        self.repository.close()
        self.temporary_directory.cleanup()

    def make_window(
        self,
        model_setup: FakeModelSetup,
        *,
        language_store: LanguagePreferenceStore | None = None,
        selection_shortcut: Shortcut | None = None,
        read_on_copy_store: ReadOnCopyPreferenceStore | None = None,
        apple_books=None,
        backup_root: Path | None = None,
        confirm_transfer=None,
        books_is_running=lambda: False,
    ) -> ReaderWindow:
        window = ReaderWindow(
            self.controller,
            model_setup,
            language_store=language_store,
            selection_shortcut=selection_shortcut,
            read_on_copy=(
                read_on_copy_store.load() if read_on_copy_store is not None else False
            ),
            read_on_copy_store=read_on_copy_store,
            apple_books=apple_books,
            backup_root=backup_root,
            confirm_transfer=confirm_transfer,
            books_is_running=books_is_running,
        )
        self.windows.append(window)
        window.show()
        self.application.processEvents()
        return window

    # -- transfer-notes tab ------------------------------------------

    def _open_tab(self, library):
        window = self.make_window(FakeModelSetup(ready=True), apple_books=library)
        view = window.transfer_notes_view
        window.feature_navigation.setCurrentIndex(window.feature_stack.indexOf(view))
        return window, view

    def test_the_library_is_untouched_until_the_tab_is_opened(self) -> None:
        library = _FakeAppleBooks()
        window = self.make_window(FakeModelSetup(ready=True), apple_books=library)
        self.assertEqual(library.calls, 0)
        view = window.transfer_notes_view
        window.feature_navigation.setCurrentIndex(window.feature_stack.indexOf(view))
        self.assertEqual(library.calls, 1)
        self.assertEqual(view.source_selector.count(), 2)

    def test_previewing_two_copies_lists_every_note(self) -> None:
        _window, view = self._open_tab(_FakeAppleBooks())
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.preview_button.click()
        self.assertEqual(view.plan_table.rowCount(), 5)
        self.assertIn("5", view.summary_label.text())

    # -- copying them across -----------------------------------------

    def _writable_library(self):
        """A fake library backed by a real annotation database on disk."""

        from tests.integrations.test_apple_books_writer import _database

        library = _FakeAppleBooks(root=Path(self.temporary_directory.name))
        library.database = _database(Path(self.temporary_directory.name), count=5)
        library.annotation_database = library.database
        return library

    def _ready_to_copy(self, *, confirm=True, books_is_running=lambda: False):
        library = self._writable_library()
        self.backup_root = Path(self.temporary_directory.name) / "backups"
        window = self.make_window(
            FakeModelSetup(ready=True),
            apple_books=library,
            backup_root=self.backup_root,
            confirm_transfer=lambda title, body: confirm,
            books_is_running=books_is_running,
        )
        view = window.transfer_notes_view
        window.feature_navigation.setCurrentIndex(window.feature_stack.indexOf(view))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.preview_button.click()
        return library, view

    def _rows_on(self, library, asset_id: str) -> int:
        connection = sqlite3.connect(library.database)
        try:
            return connection.execute(
                "SELECT COUNT(*) FROM ZAEANNOTATION WHERE ZANNOTATIONASSETID = ?"
                " AND ZANNOTATIONDELETED = 0",
                (asset_id,),
            ).fetchone()[0]
        finally:
            connection.close()

    def test_saying_no_to_the_confirmation_writes_nothing(self) -> None:
        library, view = self._ready_to_copy(confirm=False)
        view.transfer_button.click()
        self.assertEqual(self._rows_on(library, "DST"), 0)
        self.assertFalse(self.backup_root.exists(), "backed up a copy nobody approved")

    def test_nothing_is_written_while_apple_books_is_open(self) -> None:
        library, view = self._ready_to_copy(books_is_running=lambda: True)
        view.transfer_button.click()
        self.assertEqual(self._rows_on(library, "DST"), 0)
        self.assertIn("Apple Books", view.summary_label.text())

    def test_confirming_copies_the_notes_into_the_other_book(self) -> None:
        library, view = self._ready_to_copy()
        self.assertTrue(view.transfer_button.isEnabled())
        view.transfer_button.click()
        self.assertEqual(self._rows_on(library, "DST"), 5)
        self.assertEqual(
            self._rows_on(library, "SRC"), 5, "the source book was altered"
        )

    def test_a_backup_exists_before_the_write_lands(self) -> None:
        library, view = self._ready_to_copy()
        view.transfer_button.click()
        saved = list(self.backup_root.glob("*/" + library.database.name))
        self.assertEqual(len(saved), 1, f"no backup was kept: {self.backup_root}")

    def test_a_successful_copy_clears_out_the_older_backups(self) -> None:
        """Pruning lives in the writer; this pins that the window calls it.

        Without this the call could be deleted and every other test would still
        pass, because they all run with fewer backups than the limit.
        """

        library, view = self._ready_to_copy()
        for day in range(1, 9):
            (self.backup_root / f"2026-08-0{day}-120000").mkdir(parents=True)

        view.transfer_button.click()

        kept = sorted(item.name for item in self.backup_root.iterdir())
        self.assertLessEqual(len(kept), 5, kept)
        self.assertNotIn("2026-08-01-120000", kept, "the oldest survived")
        self.assertEqual(self._rows_on(library, "DST"), 5, "the copy itself broke")

    def test_clicking_twice_does_not_duplicate_every_note(self) -> None:
        library, view = self._ready_to_copy()
        view.transfer_button.click()
        view.transfer_button.click()
        self.assertEqual(self._rows_on(library, "DST"), 5)

    def test_the_confirmation_counts_what_will_be_written_not_what_is_listed(self) -> None:
        """Approving "5 items" and getting 2 is consent for something else.

        This is the partly-copied case: some notes carried over earlier, more
        were added to the source since. The preview says 2; so must the dialog.
        """

        from tests.integrations.test_apple_books_writer import _database

        library = _FakeAppleBooks(
            carried=(1, 2, 3), root=Path(self.temporary_directory.name)
        )
        library.annotation_database = _database(Path(self.temporary_directory.name))
        asked: list[str] = []
        window = self.make_window(
            FakeModelSetup(ready=True),
            apple_books=library,
            backup_root=Path(self.temporary_directory.name) / "backups",
            confirm_transfer=lambda title, body: (asked.append(body), False)[1],
        )
        view = window.transfer_notes_view
        window.feature_navigation.setCurrentIndex(window.feature_stack.indexOf(view))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.preview_button.click()
        view.transfer_button.click()

        self.assertEqual(len(asked), 1, "no confirmation was shown")
        self.assertIn("2", asked[0], asked[0])
        self.assertNotIn("5", asked[0], "the dialog offered to copy all five")

    def test_a_fully_copied_book_is_not_put_up_for_approval(self) -> None:
        library = _FakeAppleBooks(
            carried=(1, 2, 3, 4, 5), root=Path(self.temporary_directory.name)
        )
        asked: list[str] = []
        window = self.make_window(
            FakeModelSetup(ready=True),
            apple_books=library,
            backup_root=Path(self.temporary_directory.name) / "backups",
            confirm_transfer=lambda title, body: (asked.append(body), True)[1],
        )
        view = window.transfer_notes_view
        window.feature_navigation.setCurrentIndex(window.feature_stack.indexOf(view))
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.preview_button.click()

        self.assertFalse(view.transfer_button.isEnabled())
        window._transfer_notes("SRC", "DST")  # even if reached another way
        self.assertEqual(asked, [], "asked to approve copying nothing")

    def test_a_second_copy_says_they_are_already_there_not_that_it_failed(self) -> None:
        """Re-previewing and pressing again is what a careful person does."""

        library, view = self._ready_to_copy()
        view.transfer_button.click()
        self.assertEqual(self._rows_on(library, "DST"), 5)

        view.preview_button.click()
        view.transfer_button.click()

        self.assertEqual(self._rows_on(library, "DST"), 5)
        summary = view.summary_label.text()
        self.assertIn("đã có sẵn", summary, summary)


    def test_other_tabs_never_reach_into_the_books_library(self) -> None:
        """The guard behind "nothing is read until you open that tab"."""
        library = _FakeAppleBooks()
        window = self.make_window(FakeModelSetup(ready=True), apple_books=library)
        transfer = window.feature_stack.indexOf(window.transfer_notes_view)

        for index in range(window.feature_navigation.count()):
            if index != transfer:
                window.feature_navigation.setCurrentIndex(index)

        self.assertEqual(
            library.calls, 0, "only the transfer tab may read the Books library"
        )

    def test_the_preview_reads_the_two_chosen_books_and_no_others(self) -> None:
        """It reads the target too, to say what is already over there.

        That is a wider read than the source alone, so the bound that matters is
        this one: the two books named in the pickers, nothing else in the
        library, and one trip to the database rather than one per book.
        """

        library = _FakeAppleBooks()
        _window, view = self._open_tab(library)
        view.source_selector.setCurrentIndex(0)
        view.target_selector.setCurrentIndex(1)
        view.preview_button.click()
        self.assertEqual(sorted(getattr(library, "asked", [])), ["DST", "SRC"])
        self.assertEqual(getattr(library, "reads", 0), 1, "read the database twice")
        self.assertEqual(view.plan_table.rowCount(), 5)

    def test_a_library_it_cannot_read_becomes_a_message_not_a_crash(self) -> None:
        class Refusing(_FakeAppleBooks):
            def books(self):
                raise AppleBooksUnavailable(
                    "Không tìm thấy dữ liệu Apple Books trên máy này."
                )

        _window, view = self._open_tab(Refusing())
        self.assertEqual(view.plan_table.rowCount(), 0)
        self.assertIn("Apple Books", view.summary_label.text())
        self.assertFalse(view.preview_button.isEnabled())

    def test_language_switch_updates_all_core_views_and_persists(self) -> None:
        store = LanguagePreferenceStore(self.paths.root / "settings.json")
        window = self.make_window(
            FakeModelSetup(ready=True),
            language_store=store,
        )
        language_combo = window.findChild(QComboBox, "languageCombo")
        setup_language_combo = window.findChild(QComboBox, "setupLanguageCombo")

        self.assertIsNotNone(language_combo)
        self.assertIsNotNone(setup_language_combo)
        self.assertEqual(
            [
                language_combo.itemText(index)
                for index in range(language_combo.count())
            ],
            ["🇻🇳 Tiếng Việt", "🇬🇧 English"],
        )
        english_index = language_combo.findData(Language.ENGLISH.value)
        self.assertGreaterEqual(english_index, 0)

        language_combo.setCurrentIndex(english_index)
        self.application.processEvents()

        self.assertEqual(store.load(), Language.ENGLISH)
        self.assertEqual(
            [
                window.feature_navigation.tabText(index)
                for index in range(window.feature_navigation.count())
            ],
            ["Library", "Paste text", "Read a selection", "Move notes"],
        )
        self.assertEqual(window.library_view.title_label.text(), "Book library")
        self.assertEqual(window.paste_text_view.title_label.text(), "Paste text to read")
        self.assertEqual(
            window.external_reading_view.title_label.text(),
            "Read a selection",
        )
        self.assertEqual(window.previous_button.text(), "Previous")
        self.assertEqual(window.play_button.text(), "Read")
        self.assertEqual(window.stop_button.text(), "Stop")
        self.assertEqual(window.next_button.text(), "Next")
        self.assertEqual(window.session_history_button.text(), "Session history")
        self.assertEqual(window.model_setup_title.text(), "Set up Vietnamese voice")
        self.assertEqual(
            [
                window.voice_combo.itemText(index)
                for index in range(window.voice_combo.count())
            ],
            ["Adam - Southern Vietnamese", "Trúc Ly - Northern Vietnamese"],
        )
        self.assertEqual(setup_language_combo.currentData(), Language.ENGLISH.value)

        restored = self.make_window(
            FakeModelSetup(ready=True),
            language_store=store,
        )
        self.assertEqual(restored.language_combo.currentData(), Language.ENGLISH.value)
        self.assertEqual(restored.feature_navigation.tabText(0), "Library")

    def test_unprepared_model_shows_plain_language_setup_before_reader(self) -> None:
        model_setup = FakeModelSetup(ready=False)
        window = self.make_window(model_setup)
        stack = window.findChild(QStackedWidget, "rootStack")
        prepare = window.findChild(QPushButton, "prepareModelButton")

        self.assertEqual(stack.currentWidget().objectName(), "modelSetupPage")
        self.assertEqual(model_setup.start_count, 0)
        self.assertIn("330 MB", window.model_setup_description.text())

        prepare.click()
        self.application.processEvents()

        self.assertEqual(model_setup.start_count, 1)
        self.assertEqual(stack.currentWidget().objectName(), "readerPage")

    def test_language_switch_preserves_retry_state_after_model_failure(self) -> None:
        model_setup = FakeModelSetup(ready=False)
        window = self.make_window(model_setup)

        model_setup.failed.emit(
            "Không thể chuẩn bị giọng đọc. "
            "Hãy kiểm tra kết nối mạng và Thử lại."
        )
        english_index = window.language_combo.findData(Language.ENGLISH.value)
        window.language_combo.setCurrentIndex(english_index)
        self.application.processEvents()

        self.assertEqual(window.prepare_model_button.text(), "Try again")
        self.assertEqual(
            window.model_status.text(),
            "Could not prepare the voice. Check your connection and try again.",
        )

    def test_ready_empty_library_offers_book_and_pasted_text_actions(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))

        self.assertEqual(window.windowTitle(), "ReadEase — Thư Âm")
        self.assertEqual(window.brand_title.text(), "ReadEase — Thư Âm")
        self.assertTrue(window.library_view.open_button.isVisible())
        self.assertTrue(window.library_view.paste_button.isVisible())
        self.assertFalse(window.toolbar_open_button.isVisible())
        self.assertFalse(window.toolbar_paste_button.isVisible())
        self.assertFalse(window.play_button.isEnabled())
        self.assertEqual(window.library_view.library_list.count(), 0)

    def test_ready_workspace_has_four_persistent_feature_views(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))

        navigation = window.findChild(QTabBar, "featureNavigation")
        feature_stack = window.findChild(QStackedWidget, "featureStack")

        self.assertIsNotNone(navigation)
        self.assertIsNotNone(feature_stack)
        self.assertEqual(
            [navigation.tabText(index) for index in range(navigation.count())],
            ["Thư viện", "Dán nội dung", "Quét đọc", "Chuyển ghi chú"],
        )
        self.assertEqual(feature_stack.count(), 4)
        self.assertEqual(
            [feature_stack.widget(index).objectName() for index in range(3)],
            ["libraryView", "pasteTextView", "externalReadingView"],
        )
        self.assertEqual(feature_stack.currentWidget().objectName(), "libraryView")
        library_stack = feature_stack.widget(0).findChild(
            QStackedWidget,
            "libraryStack",
        )
        self.assertIsNotNone(library_stack)
        self.assertEqual(
            [library_stack.widget(index).objectName() for index in range(2)],
            ["libraryShelfView", "bookReaderView"],
        )
        self.assertEqual(
            library_stack.currentWidget().objectName(),
            "libraryShelfView",
        )
        self.assertIs(
            feature_stack.widget(0).findChild(QListWidget, "libraryList"),
            window.library_view.library_list,
        )
        self.assertIs(
            feature_stack.widget(1).findChild(QPlainTextEdit, "pasteTextEdit"),
            window.paste_text_view.text_edit,
        )
        self.assertIs(
            library_stack.widget(1).findChild(QListWidget, "chapterList"),
            window.library_view.book_reader_view.chapter_list,
        )
        self.assertIs(
            library_stack.widget(1).findChild(QTextBrowser, "readerText"),
            window.library_view.book_reader_view.reader_text,
        )
        shortcut = feature_stack.widget(2).findChild(
            QLabel,
            "externalReadingShortcut",
        )
        self.assertIsNotNone(shortcut)
        self.assertEqual(shortcut.text(), "Control + Option + Command + R")
        self.assertTrue(window.feature_navigation.isTabEnabled(2))
        self.assertFalse(window.paste_text_view.read_button.isEnabled())

    def test_shortcut_label_follows_the_setting_and_can_be_rerecorded(self) -> None:
        saved = Shortcut(key_code=38, modifiers=CONTROL_KEY | CMD_KEY)
        window = self.make_window(
            FakeModelSetup(ready=True),
            selection_shortcut=saved,
        )
        label = window.findChild(QLabel, "externalReadingShortcut")

        self.assertIsNotNone(label)
        self.assertEqual(label.text(), "Control + Command + J")
        self.assertEqual(
            label.accessibleName(),
            "Phím tắt đọc phần đã chọn: Control + Command + J",
        )

        recorder = window.findChild(QPushButton, "externalReadingShortcutRecorder")
        self.assertIsNotNone(recorder)
        self.assertEqual(recorder.text(), "Đổi phím tắt")

        chosen: list[Shortcut] = []
        window.selectionShortcutChanged.connect(chosen.append)
        recorder.click()
        self.application.processEvents()

        self.assertEqual(recorder.text(), "Nhấn tổ hợp phím mới…")
        QTest.keyClick(
            recorder,
            Qt.Key.Key_K,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
        )
        self.application.processEvents()

        self.assertEqual(
            chosen,
            [Shortcut(key_code=40, modifiers=CMD_KEY | OPTION_KEY)],
        )
        # The label only moves once the helper reports the choice registered.
        self.assertEqual(label.text(), "Control + Command + J")
        self.assertEqual(recorder.text(), "Đổi phím tắt")

        window.set_selection_shortcut(chosen[0])
        self.application.processEvents()

        self.assertEqual(label.text(), "Option + Command + K")
        self.assertEqual(
            label.accessibleName(),
            "Phím tắt đọc phần đã chọn: Option + Command + K",
        )

    def test_shortcut_controls_are_translated_without_losing_the_combination(
        self,
    ) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        language_combo = window.findChild(QComboBox, "languageCombo")
        label = window.findChild(QLabel, "externalReadingShortcut")
        recorder = window.findChild(QPushButton, "externalReadingShortcutRecorder")

        language_combo.setCurrentIndex(
            language_combo.findData(Language.ENGLISH.value)
        )
        self.application.processEvents()

        self.assertEqual(label.text(), "Control + Option + Command + R")
        self.assertEqual(
            label.accessibleName(),
            "Read-selection shortcut: Control + Option + Command + R",
        )
        self.assertEqual(recorder.text(), "Change shortcut")

    def test_a_shortcut_macos_refuses_explains_itself(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)

        self.controller.external_selection_failed("shortcut_unavailable")
        self.application.processEvents()

        detail = window.external_reading_view.detail_label
        self.assertTrue(detail.isVisible())
        self.assertIn("tổ hợp khác", detail.text())
        self.assertFalse(window.open_accessibility_settings_button.isVisible())

    def test_read_on_copy_is_off_by_default_and_labelled_in_both_languages(
        self,
    ) -> None:
        store = ReadOnCopyPreferenceStore(self.paths.root / "settings.json")
        window = self.make_window(
            FakeModelSetup(ready=True),
            read_on_copy_store=store,
        )
        toggle = window.findChild(QCheckBox, "externalReadingReadOnCopy")

        self.assertIsNotNone(toggle)
        self.assertFalse(toggle.isChecked())
        self.assertFalse(store.load())
        self.assertEqual(toggle.text(), "Đọc ngay khi sao chép trong Apple Books")

        changes: list[bool] = []
        window.readOnCopyChanged.connect(changes.append)
        toggle.click()
        self.application.processEvents()

        self.assertEqual(changes, [True])
        self.assertTrue(toggle.isChecked())
        # The choice has to survive a restart, not just this window.
        self.assertTrue(store.load())

        toggle.click()
        self.application.processEvents()

        # Switching it back off has to be remembered just as faithfully.
        self.assertEqual(changes, [True, False])
        self.assertFalse(store.load())

        toggle.click()
        self.application.processEvents()
        self.assertEqual(changes, [True, False, True])

        language_combo = window.findChild(QComboBox, "languageCombo")
        language_combo.setCurrentIndex(
            language_combo.findData(Language.ENGLISH.value)
        )
        self.application.processEvents()

        self.assertEqual(toggle.text(), "Read as soon as you copy in Apple Books")
        # Switching language must not switch the feature on or off.
        self.assertEqual(changes, [True, False, True])
        self.assertTrue(toggle.isChecked())
        self.assertTrue(store.load())

    def test_privacy_note_describes_read_on_copy_in_both_languages(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        note = window.external_reading_view.privacy_note

        vietnamese = note.text()
        self.assertIn("tắt", vietnamese)
        self.assertIn("clipboard", vietnamese.lower())

        window.external_reading_view.set_read_on_copy(True)
        self.assertNotEqual(note.text(), vietnamese)
        self.assertIn("clipboard", note.text().lower())

        language_combo = window.findChild(QComboBox, "languageCombo")
        language_combo.setCurrentIndex(
            language_combo.findData(Language.ENGLISH.value)
        )
        self.application.processEvents()

        self.assertIn("clipboard", note.text().lower())
        self.assertNotIn("does not monitor your screen or clipboard", note.text())

    def test_session_history_control_starts_disabled_and_accessible(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))

        button = window.findChild(QToolButton, "sessionHistoryButton")

        self.assertIsNotNone(button)
        self.assertEqual(button.text(), "Lịch sử phiên")
        self.assertEqual(
            button.accessibleName(),
            "Mở lịch sử nội dung đã đọc trong phiên",
        )
        self.assertFalse(button.isEnabled())
        self.assertEqual(button.menu().actions(), [])

    def test_session_history_menu_replays_any_transient_source(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)
        self.controller.read_pasted_text("Bản dán.")
        self.controller.read_selection("Phần trong sách.")
        self.controller.read_external_selection("Phần Apple Books.")
        self.application.processEvents()

        actions = [
            action
            for action in window.session_history_menu.actions()
            if not action.isSeparator()
        ]

        self.assertTrue(window.session_history_button.isEnabled())
        self.assertEqual(
            [action.text() for action in actions],
            [
                "Apple Books · Phần Apple Books.",
                "Trong sách · Phần trong sách.",
                "Dán nội dung · Bản dán.",
                "Xóa lịch sử phiên",
            ],
        )
        calls_before_replay = len(self.playback.selection_calls)

        actions[1].trigger()

        self.assertEqual(len(self.playback.selection_calls), calls_before_replay + 1)
        self.assertEqual(self.playback.selection_calls[-1][0], "Phần trong sách.")
        self.assertEqual(window.feature_stack.currentIndex(), 2)

    def test_session_history_clear_action_empties_and_disables_menu(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        self.controller.read_pasted_text("Nội dung nhạy cảm trong phiên.")
        self.application.processEvents()
        clear_action = next(
            action
            for action in window.session_history_menu.actions()
            if action.text() == "Xóa lịch sử phiên"
        )

        clear_action.trigger()
        self.application.processEvents()

        self.assertEqual(self.controller.state.session_history, ())
        self.assertFalse(window.session_history_button.isEnabled())
        self.assertEqual(window.session_history_menu.actions(), [])

    def test_session_history_menu_fits_minimum_window_with_long_preview(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.resize(900, 600)
        for number in range(10):
            self.controller.read_external_selection(
                f"Mục {number + 1}: " + "Nội dung tiếng Việt rất dài " * 12
            )
        self.application.processEvents()

        menu_size = window.session_history_menu.sizeHint()
        button_top = window.session_history_button.mapTo(
            window,
            window.session_history_button.rect().topLeft(),
        ).y()

        self.assertLessEqual(menu_size.width(), window.width() - 40)
        self.assertLessEqual(menu_size.height(), button_top - 20)
        self.assertLess(
            window.session_history_button.geometry().right(),
            window.voice_combo.geometry().left(),
        )
        self.assertLessEqual(
            window.rate_combo.geometry().right(),
            window.rate_combo.parentWidget().contentsRect().right(),
        )
        self.assertEqual(window.feature_navigation.count(), 4)
        self.assertEqual(
            window.session_history_button.focusPolicy(),
            Qt.FocusPolicy.StrongFocus,
        )

    def test_session_history_menu_opens_from_keyboard(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        self.controller.read_pasted_text("Nội dung mở bằng bàn phím.")
        self.application.processEvents()
        window.session_history_button.setFocus()
        opened = []
        window.session_history_menu.aboutToShow.connect(lambda: opened.append(True))
        QTimer.singleShot(50, window.session_history_menu.close)

        QTest.keyClick(window.session_history_button, Qt.Key.Key_Space)
        self.application.processEvents()

        self.assertEqual(opened, [True])

    def test_external_reading_view_opens_the_accessibility_settings(self) -> None:
        opened = []
        window = ReaderWindow(
            self.controller,
            FakeModelSetup(ready=True),
            open_accessibility_settings=lambda: opened.append(True),
        )
        self.windows.append(window)
        window.show()
        window.feature_navigation.setCurrentIndex(2)
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "externalReadingView",
        )
        button = window.feature_stack.currentWidget().findChild(
            QPushButton,
            "externalAccessibilitySettingsButton",
        )
        self.assertIsNotNone(button)
        self.assertTrue(button.isVisible())
        button.click()

        self.assertEqual(opened, [True])

    def test_external_view_shows_only_apple_books_history_and_replays_it(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)
        self.controller.read_pasted_text("Bản dán không thuộc Apple Books.")
        self.controller.read_external_selection("Đoạn Apple Books thứ nhất.")
        self.controller.read_external_selection("Đoạn Apple Books thứ hai.")
        self.application.processEvents()

        history = window.findChild(QListWidget, "externalReadingHistoryList")
        replay = window.findChild(QPushButton, "externalReadingReplayButton")

        self.assertIsNotNone(history)
        self.assertIsNotNone(replay)
        self.assertEqual(history.count(), 2)
        self.assertEqual(
            [history.item(index).text() for index in range(history.count())],
            ["Đoạn Apple Books thứ hai.", "Đoạn Apple Books thứ nhất."],
        )
        history.setCurrentRow(1)
        replay.click()

        self.assertEqual(
            self.playback.selection_calls[-1][0],
            "Đoạn Apple Books thứ nhất.",
        )

    def test_external_history_widgets_hold_only_bounded_preview_and_item_id(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)
        full_text = "Nội dung riêng tư " * 12

        self.controller.read_external_selection(full_text)
        self.application.processEvents()

        history = window.findChild(QListWidget, "externalReadingHistoryList")
        item = history.item(0)
        state_item = self.controller.state.session_history[0]

        self.assertEqual(item.text(), state_item.preview)
        self.assertLessEqual(len(item.text()), 72)
        self.assertNotEqual(item.text(), full_text.strip())
        self.assertEqual(item.data(Qt.ItemDataRole.UserRole), state_item.id)

    def test_external_view_renders_shortcut_lifecycle_state(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)
        status = window.findChild(QLabel, "externalReadingStatus")

        self.assertIsNotNone(status)
        self.assertEqual(
            self.controller.state.external_reading_state,
            ExternalReadingState.STARTING,
        )
        self.assertIn("chuẩn bị", status.text().lower())

        self.controller.external_selection_failed("ready")
        self.application.processEvents()
        self.assertIn("sẵn sàng", status.text().lower())

        self.controller.external_selection_failed("permission_required")
        self.application.processEvents()
        self.assertIn("cần quyền", status.text().lower())

        self.controller.read_external_selection("Đoạn vừa nhận.")
        self.application.processEvents()
        self.assertIn("đã nhận", status.text().lower())

    def test_external_permission_shows_only_its_contextual_settings_action(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)

        self.controller.external_selection_failed("permission_required")
        self.application.processEvents()

        contextual = window.findChild(
            QPushButton,
            "externalAccessibilitySettingsButton",
        )
        self.assertTrue(contextual.isVisible())
        self.assertFalse(window.open_accessibility_settings_button.isVisible())

    def test_external_error_detail_stays_inside_its_own_surface(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)

        self.controller.external_selection_failed("permission_required")
        self.application.processEvents()

        detail = window.findChild(QLabel, "externalReadingDetail")
        self.assertIsNotNone(detail)
        self.assertTrue(detail.isVisible())
        self.assertIn("Cài đặt hệ thống", detail.text())
        self.assertFalse(window.error_label.isVisible())

    def test_external_idle_hides_global_status_but_playback_shows_progress(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.feature_navigation.setCurrentIndex(2)

        self.assertFalse(window.status_label.isVisible())

        self.controller.read_external_selection("Đoạn đang được đọc.")
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=None,
                segment_id=None,
                is_selection=True,
                generation=1,
                sequence=1,
            )
        )
        self.application.processEvents()

        self.assertTrue(window.status_label.isVisible())
        self.assertEqual(window.status_label.text(), "Đang đọc")

    def test_external_history_list_remains_compact_at_large_window_size(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.resize(1180, 792)
        window.feature_navigation.setCurrentIndex(2)
        for number in range(10):
            self.controller.read_external_selection(f"Đoạn Apple Books {number}.")
        self.application.processEvents()

        history = window.findChild(QListWidget, "externalReadingHistoryList")

        self.assertLessEqual(history.height(), 260)
        self.assertFalse(history.wordWrap())
        self.assertEqual(
            history.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

    def test_short_external_history_does_not_expand_into_a_blank_panel(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.resize(1180, 792)
        window.feature_navigation.setCurrentIndex(2)
        self.controller.read_external_selection("Đoạn Apple Books một.")
        self.controller.read_external_selection("Đoạn Apple Books hai.")
        self.application.processEvents()

        history = window.findChild(QListWidget, "externalReadingHistoryList")

        self.assertLessEqual(history.height(), 100)

    def test_imported_book_location_is_visible_only_in_library_reader(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        self.application.processEvents()

        self.assertTrue(window.reading_location_label.isVisible())

        window.feature_navigation.setCurrentIndex(2)
        self.application.processEvents()

        self.assertFalse(window.reading_location_label.isVisible())

        window.feature_navigation.setCurrentIndex(0)
        self.application.processEvents()

        self.assertTrue(window.reading_location_label.isVisible())

    def test_paste_action_opens_inline_view_and_preserves_the_draft(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))

        window.library_view.paste_button.click()
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "pasteTextView",
        )
        window.paste_text_view.text_edit.setPlainText("Bản nháp chỉ nằm trong phiên này.")
        window.feature_navigation.setCurrentIndex(0)
        window.feature_navigation.setCurrentIndex(1)

        self.assertEqual(
            window.paste_text_view.text_edit.toPlainText(),
            "Bản nháp chỉ nằm trong phiên này.",
        )

    def test_permission_error_offers_accessibility_settings_action(self) -> None:
        opened = []
        window = ReaderWindow(
            self.controller,
            FakeModelSetup(ready=True),
            open_accessibility_settings=lambda: opened.append(True),
        )
        self.windows.append(window)
        window.show()

        self.controller.external_selection_failed("permission_required")
        self.application.processEvents()

        self.assertTrue(window.open_accessibility_settings_button.isVisible())
        self.assertEqual(
            window.open_accessibility_settings_button.text(),
            "Mở Cài đặt quyền",
        )
        window.open_accessibility_settings_button.click()
        self.assertEqual(opened, [True])

    def test_non_permission_error_hides_accessibility_settings_action(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))

        self.controller.external_selection_failed("no_selection")
        self.application.processEvents()

        self.assertFalse(window.open_accessibility_settings_button.isVisible())

    def test_empty_state_can_read_pasted_text_without_importing_a_book(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.library_view.paste_button.click()
        window.paste_text_view.text_edit.setPlainText("  Nội dung dán để ReadEase đọc.  ")
        self.application.processEvents()
        window.paste_text_view.read_button.click()

        self.assertTrue(self.playback.selection_calls)
        self.assertEqual(
            self.playback.selection_calls[-1][0],
            "  Nội dung dán để ReadEase đọc.  ",
        )
        self.assertEqual(self.repository.list_books(), ())

    def test_invalid_inline_paste_cannot_start_playback(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.library_view.paste_button.click()
        window.paste_text_view.text_edit.setPlainText(" \n\t ")
        self.application.processEvents()

        self.assertFalse(window.paste_text_view.read_button.isEnabled())
        window.paste_text_view.read_button.click()
        self.assertEqual(self.playback.selection_calls, [])

    def test_pasted_text_playback_can_pause_and_resume_without_a_book(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                is_selection=True,
                generation=1,
                sequence=1,
            )
        )
        self.application.processEvents()

        self.assertTrue(window.play_button.isEnabled())
        self.assertFalse(window.previous_button.isEnabled())
        self.assertFalse(window.next_button.isEnabled())
        self.assertEqual(window.play_button.text(), "Tạm dừng")
        window.play_button.click()
        self.assertEqual(self.playback.commands[-1], "pause")

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PAUSED,
                is_selection=True,
                generation=1,
                sequence=2,
            )
        )
        self.application.processEvents()
        self.assertTrue(window.play_button.isEnabled())
        self.assertEqual(window.play_button.text(), "Tiếp tục")
        window.play_button.click()
        self.assertEqual(self.playback.commands[-1], "resume")

    def test_switching_feature_views_does_not_stop_active_playback(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=self.controller.state.active_book_id,
                segment_id=self.controller.state.active_segment_id,
                generation=1,
                sequence=1,
            )
        )
        commands_before_navigation = list(self.playback.commands)

        window.feature_navigation.setCurrentIndex(1)
        window.feature_navigation.setCurrentIndex(2)
        window.feature_navigation.setCurrentIndex(0)
        self.application.processEvents()

        self.assertEqual(self.playback.commands, commands_before_navigation)
        self.assertEqual(self.controller.state.playback_state, PlaybackState.PLAYING)

    def test_idle_book_transport_is_disabled_outside_the_reader_view(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        self.assertTrue(window.play_button.isEnabled())
        self.assertTrue(window.previous_button.isEnabled())
        play_calls_before_navigation = list(self.playback.play_calls)

        window.feature_navigation.setCurrentIndex(2)
        self.application.processEvents()

        self.assertFalse(window.play_button.isEnabled())
        self.assertFalse(window.previous_button.isEnabled())
        self.assertFalse(window.next_button.isEnabled())
        window.play_button.click()
        self.assertEqual(self.playback.play_calls, play_calls_before_navigation)

    def test_active_playback_can_pause_and_stop_outside_the_reader_view(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=self.controller.state.active_book_id,
                segment_id=self.controller.state.active_segment_id,
                generation=1,
                sequence=1,
            )
        )

        window.feature_navigation.setCurrentIndex(2)
        self.application.processEvents()

        self.assertTrue(window.play_button.isEnabled())
        self.assertEqual(window.play_button.text(), "Tạm dừng")
        self.assertTrue(window.stop_button.isEnabled())
        self.assertFalse(window.previous_button.isEnabled())
        self.assertFalse(window.next_button.isEnabled())
        window.play_button.click()
        self.assertEqual(self.playback.commands[-1], "pause")

    def test_apple_books_selection_does_not_change_the_visible_feature(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.library_view.paste_button.click()

        self.controller.read_external_selection("Nội dung đang chọn trong Apple Books.")
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "pasteTextView",
        )
        self.assertEqual(
            self.playback.selection_calls[-1][0],
            "Nội dung đang chọn trong Apple Books.",
        )

    def test_apple_books_playback_snapshots_do_not_write_book_progress(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        stored = self.repository.get_book(self.controller.state.active_book_id)
        active = stored.book
        target = active.chapters[-1].segments[-1]
        self.controller.select_segment(target.id)
        with closing(sqlite3.connect(self.paths.database)) as connection:
            connection.execute(
                "UPDATE progress SET updated_at = ? WHERE book_id = ?",
                ("2000-01-01 00:00:00", active.id),
            )
            connection.commit()

        def progress_row():
            with closing(sqlite3.connect(self.paths.database)) as connection:
                return connection.execute(
                    "SELECT book_id, segment_id, playback_rate, voice_id, "
                    "updated_at FROM progress WHERE book_id = ?",
                    (active.id,),
                ).fetchone()

        progress_before = progress_row()
        position_calls_before = list(self.playback.position_calls)
        preference_calls_before = list(self.playback.preference_calls)
        chapter_events = []
        segment_events = []
        reader = window.library_view.book_reader_view
        reader.chapterActivated.connect(chapter_events.append)
        reader.segmentActivated.connect(segment_events.append)
        window.feature_navigation.setCurrentIndex(2)

        self.controller.read_external_selection(
            "Nội dung đang chọn trong Apple Books."
        )
        for sequence, state, is_selection in (
            (1, PlaybackState.LOADING, True),
            (2, PlaybackState.PLAYING, True),
            (3, PlaybackState.IDLE, False),
        ):
            self.playback.emit(
                PlaybackSnapshot(
                    state=state,
                    book_id=active.id,
                    segment_id=target.id,
                    is_selection=is_selection,
                    generation=7,
                    sequence=sequence,
                )
            )
            self.application.processEvents()

        self.assertEqual(progress_row(), progress_before)
        self.assertEqual(self.playback.position_calls, position_calls_before)
        self.assertEqual(self.playback.preference_calls, preference_calls_before)
        self.assertEqual(chapter_events, [])
        self.assertEqual(segment_events, [])

    def test_selection_playback_disables_book_navigation_controls(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=self.controller.state.active_book_id,
                segment_id=self.controller.state.active_segment_id,
                is_selection=True,
                generation=1,
                sequence=1,
            )
        )
        self.application.processEvents()

        self.assertFalse(window.previous_button.isEnabled())
        self.assertFalse(window.next_button.isEnabled())
        self.assertTrue(window.stop_button.isEnabled())

    def test_import_renders_library_chapters_selectable_text_and_controls(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        source = make_epub(self.sources)

        window.import_path(source)
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "libraryView",
        )
        self.assertEqual(
            window.library_view.surface_stack.currentWidget().objectName(),
            "bookReaderView",
        )
        self.assertEqual(window.library_view.library_list.count(), 1)
        reader = window.library_view.book_reader_view
        self.assertGreater(reader.chapter_list.count(), 0)
        self.assertIn("Nội dung", reader.reader_text.toPlainText())
        active_book_title = reader.findChild(
            QLabel,
            "activeBookTitle",
        )
        self.assertIsNotNone(active_book_title)
        self.assertEqual(active_book_title.text(), "Sách thử nghiệm")
        self.assertTrue(active_book_title.accessibleName())
        self.assertEqual(
            window.reading_location_label.text(),
            "Chương 1/2 · Đoạn 1/2",
        )
        self.assertTrue(window.play_button.isEnabled())
        self.assertTrue(window.toolbar_open_button.isVisible())
        self.assertTrue(window.toolbar_paste_button.isVisible())
        self.assertFalse(window.library_view.open_button.isVisible())
        self.assertFalse(window.library_view.paste_button.isVisible())
        for control in (
            window.play_button,
            window.previous_button,
            window.next_button,
            reader.reader_text,
        ):
            self.assertTrue(control.accessibleName())

    def test_startup_with_an_active_book_opens_the_book_reader_view(self) -> None:
        self.controller.import_book(make_epub(self.sources))

        window = self.make_window(FakeModelSetup(ready=True))

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "libraryView",
        )
        self.assertEqual(
            window.library_view.surface_stack.currentWidget().objectName(),
            "bookReaderView",
        )

    def test_choosing_a_library_book_opens_the_book_reader_view(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(
            make_epub(self.sources, name="first.epub", title="Sách thứ nhất")
        )
        window.import_path(
            make_epub(self.sources, name="second.epub", title="Sách thứ hai")
        )
        window.feature_navigation.setCurrentIndex(0)
        active_book_id = self.controller.state.active_book_id
        inactive_item = next(
            window.library_view.library_list.item(index)
            for index in range(window.library_view.library_list.count())
            if window.library_view.library_list.item(index).data(Qt.ItemDataRole.UserRole)
            != active_book_id
        )

        QTest.mouseClick(
            window.library_view.library_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=window.library_view.library_list.visualItemRect(
                inactive_item
            ).center(),
        )
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "libraryView",
        )
        self.assertEqual(
            window.library_view.surface_stack.currentWidget().objectName(),
            "bookReaderView",
        )

    def test_clicking_the_active_library_book_reopens_the_reader_view(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        window.feature_navigation.setCurrentIndex(0)
        active_item = window.library_view.library_list.currentItem()
        self.assertIsNotNone(active_item)

        QTest.mouseClick(
            window.library_view.library_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=window.library_view.library_list.visualItemRect(active_item).center(),
        )
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "libraryView",
        )
        self.assertEqual(
            window.library_view.surface_stack.currentWidget().objectName(),
            "bookReaderView",
        )

    def test_pressing_enter_on_the_active_library_book_reopens_reader(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        window.feature_navigation.setCurrentIndex(0)
        window.library_view.library_list.setFocus()

        QTest.keyClick(
            window.library_view.library_list,
            Qt.Key.Key_Return,
        )
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "libraryView",
        )
        self.assertEqual(
            window.library_view.surface_stack.currentWidget().objectName(),
            "bookReaderView",
        )

    def test_reader_back_action_returns_to_the_imported_book_library(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))

        window.library_view.book_reader_view.back_button.click()
        self.application.processEvents()

        self.assertEqual(
            window.feature_stack.currentWidget().objectName(),
            "libraryView",
        )
        self.assertEqual(
            window.library_view.surface_stack.currentWidget().objectName(),
            "libraryShelfView",
        )
        self.assertFalse(window.play_button.isEnabled())

    def test_selected_text_is_sent_to_read_selection_command(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        reader = window.library_view.book_reader_view
        cursor = reader.reader_text.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(8, QTextCursor.MoveMode.KeepAnchor)
        reader.reader_text.setTextCursor(cursor)
        self.application.processEvents()

        self.assertTrue(reader.read_selection_button.isEnabled())
        selected = cursor.selectedText()
        reader.read_selection_button.click()

        self.assertEqual(self.playback.selection_calls[-1][0], selected)

    def test_reader_renders_numbered_epub_image_without_polluting_selection(self) -> None:
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1><p>Đoạn trước hình.</p>
        <img src="images/diagram.png" alt="Sơ đồ đọc sách"/>
        <p>Đoạn sau hình.</p>
        </body></html>"""
        window = self.make_window(FakeModelSetup(ready=True))
        window.resize(1180, 760)
        window.import_path(
            make_epub(
                self.sources,
                spine=("chapter-1",),
                chapter_overrides={"chapter-1": chapter},
                image_entries={
                    "images/diagram.png": (make_png(1200, 800), "image/png"),
                },
            )
        )
        reader = window.library_view.book_reader_view
        document = reader.reader_text.document()

        self.assertIn("Hình 1", document.toPlainText())
        self.assertNotIn("Không thể hiển thị", document.toPlainText())
        image_formats = []
        block = document.begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    image_formats.append(fragment.charFormat().toImageFormat())
                iterator += 1
            block = block.next()
        self.assertEqual(len(image_formats), 1)
        self.assertLessEqual(image_formats[0].width(), 600)
        self.assertEqual(
            image_formats[0].property(QTextFormat.Property.ImageAltText),
            "Sơ đồ đọc sách",
        )
        accessibility = QAccessible.queryAccessibleInterface(reader.reader_text)
        self.assertIsNotNone(accessibility)
        self.assertIn(
            "Hình 1: Sơ đồ đọc sách",
            accessibility.text(QAccessible.Text.Description),
        )
        self.assertEqual(len(reader.segment_blocks), 3)

        segment_events = []
        reader.segmentActivated.connect(segment_events.append)
        selected_cursor = QTextCursor(document)
        selected_cursor.setPosition(0)
        selected_cursor.setPosition(8, QTextCursor.MoveMode.KeepAnchor)
        reader.reader_text.setTextCursor(selected_cursor)
        selected_text = reader.reader_text.textCursor().selectedText()
        playback_commands_before = list(self.playback.commands)
        position_calls_before = list(self.playback.position_calls)
        segment_events.clear()
        window.resize(900, 600)
        self.application.processEvents()
        self.application.processEvents()
        splitter = reader.findChild(QSplitter)
        self.assertIsNotNone(splitter)
        splitter.setSizes([360, 540])
        self.application.processEvents()
        self.application.processEvents()
        self.assertEqual(segment_events, [])
        self.assertTrue(reader.reader_text.textCursor().hasSelection())
        self.assertEqual(
            reader.reader_text.textCursor().selectedText(),
            selected_text,
        )
        self.assertEqual(self.playback.commands, playback_commands_before)
        self.assertEqual(self.playback.position_calls, position_calls_before)
        document = reader.reader_text.document()
        image_width = None
        block = document.begin()
        while block.isValid() and image_width is None:
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    image_width = fragment.charFormat().toImageFormat().width()
                    break
                iterator += 1
            block = block.next()
        content_width = (
            reader.reader_text.viewport().width()
            - (2 * round(document.documentMargin()))
            - 4
        )
        self.assertIsNotNone(image_width)
        self.assertLessEqual(image_width, content_width)

        cursor = QTextCursor(document)
        cursor.select(QTextCursor.SelectionType.Document)
        reader.reader_text.setTextCursor(cursor)
        reader.read_selection_button.click()

        self.assertNotIn("\ufffc", self.playback.selection_calls[-1][0])

    def test_playback_snapshot_highlights_and_scrolls_to_active_paragraph(self) -> None:
        window = self.make_window(FakeModelSetup(ready=True))
        window.import_path(make_epub(self.sources))
        stored = self.repository.get_book(self.controller.state.active_book_id)
        target = stored.book.chapters[1].segments[0]

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=stored.book.id,
                segment_id=target.id,
                generation=2,
                sequence=1,
            )
        )
        self.application.processEvents()

        block = window.library_view.book_reader_view.segment_blocks[target.id]
        self.assertNotEqual(block.blockFormat().background().style().value, 0)
        self.assertEqual(window.play_button.text(), "Tạm dừng")
        self.assertEqual(
            window.reading_location_label.text(),
            "Chương 2/2 · Đoạn 1/2",
        )

    def test_accepts_only_local_pdf_and_epub_drop_paths(self) -> None:
        epub = make_epub(self.sources)
        text = self.sources / "notes.txt"
        text.write_text("Không phải sách", encoding="utf-8")

        self.assertTrue(ReaderWindow.accepts_path(epub))
        self.assertTrue(ReaderWindow.accepts_path(self.sources / "BOOK.PDF"))
        self.assertFalse(ReaderWindow.accepts_path(text))


if __name__ == "__main__":
    unittest.main()


class HeadingHierarchyTests(unittest.TestCase):
    """One heading per view, and status text that does not impersonate it.

    A rendered audit found the Read books tab opening with two bold lines
    stacked - its title and its status - so neither read as the heading. Every
    other view in the app leads with exactly one.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.controller = ReaderController(
            self.repository,
            self.service,
            FakePlayback(self.repository),
            dispatch=lambda action: action(),
        )
        self.window = ReaderWindow(
            self.controller,
            FakeModelSetup(ready=True),
            apple_books=_FakeAppleBooks(root=root),
        )

    def tearDown(self) -> None:
        self.window.close()
        self.application.processEvents()
        self.repository.close()
        self.temporary_directory.cleanup()

    def test_the_read_books_status_does_not_compete_with_its_title(self) -> None:
        view = self.window.external_reading_view
        title = view.title_label.font()
        status = view.status_label.font()
        self.assertTrue(title.bold(), "the title must still be the heading")
        self.assertFalse(status.bold(), "status text is dressed as a heading")
        self.assertLess(status.pointSize(), title.pointSize())

    def test_every_view_leads_with_a_heading_larger_than_its_body(self) -> None:
        for view, body in (
            (self.window.transfer_notes_view, self.window.transfer_notes_view.description),
            (
                self.window.external_reading_view,
                self.window.external_reading_view.description_label,
            ),
        ):
            with self.subTest(view=view.objectName()):
                heading = view.title_label.font()
                self.assertTrue(heading.bold())
                self.assertGreater(heading.pointSize(), body.font().pointSize())

    def test_the_tabs_sit_at_the_left_not_adrift_in_the_middle(self) -> None:
        """macOS centres a tab bar inside whatever width it is given.

        Handed the full window it floated in the middle, detached from the
        content it switches. Given only the width it needs, it stays under the
        app title. Measured, because the macOS style paints nothing offscreen -
        only the geometry is observable from here.
        """

        self.window.resize(1180, 620)
        self.window.show()
        self.application.processEvents()
        bar = self.window.feature_navigation
        self.assertLess(bar.geometry().x(), 40, "tab bar drifted right")
        self.assertLess(
            bar.width(),
            self.window.width() // 2,
            "tab bar was handed the whole window and will centre inside it",
        )

    def test_the_tab_bar_draws_no_frame_of_its_own(self) -> None:
        """It sits above an unframed stack; its base joined nothing."""

        self.assertFalse(self.window.feature_navigation.drawBase())
