"""Offscreen end-to-end reader journey with real import/storage and fake speech."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from vieneu_reader.config import AppPaths
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.playback.coordinator import PlaybackSnapshot, PlaybackState
from vieneu_reader.storage.repository import LibraryRepository
from vieneu_reader.ui.controller import ReaderController
from vieneu_reader.ui.window import ReaderWindow

from tests.importers.epub_fixture import make_epub
from tests.importers.pdf_fixture import make_blank_pdf, make_text_pdf
from tests.ui.test_controller import FakePlayback
from tests.ui.test_window import FakeModelSetup


def _make_scan(path: Path) -> Path:
    return make_blank_pdf(path)


def main() -> int:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as directory:
        root = Path(directory)
        paths = AppPaths.create(root / "app-data")
        repository = LibraryRepository(paths.database)
        service = LibraryService(paths, repository)
        playback = FakePlayback(repository)
        controller = ReaderController(
            repository,
            service,
            playback,
            dispatch=lambda action: action(),
        )
        sources = root / "sources"
        sources.mkdir()
        window = ReaderWindow(controller, FakeModelSetup(ready=True))
        window.show()
        application.processEvents()
        feature_names = [
            window.feature_stack.widget(index).objectName()
            for index in range(window.feature_stack.count())
        ]
        if feature_names != [
            "libraryView",
            "pasteTextView",
            "externalReadingView",
        ]:
            raise AssertionError("three feature views are not mounted in stable order")
        if window.feature_stack.currentWidget().objectName() != "libraryView":
            raise AssertionError("empty startup did not open the library view")

        epub = make_epub(sources)
        pdf = make_text_pdf(sources)
        window.import_path(epub)
        window.import_path(pdf)
        application.processEvents()
        if window.library_view.library_list.count() != 2:
            raise AssertionError("EPUB and PDF did not enter the same library")
        if window.feature_stack.currentWidget().objectName() != "libraryView":
            raise AssertionError("successful import left the library feature")
        if (
            window.library_view.surface_stack.currentWidget().objectName()
            != "bookReaderView"
        ):
            raise AssertionError("successful import did not open the nested reader")

        active = repository.get_book(controller.state.active_book_id).book
        target = active.chapters[-1].segments[-1]
        controller.select_segment(target.id)
        progress_before_paste = repository.load_progress(active.id)
        window.show_paste_view()
        window.paste_text_view.text_edit.setPlainText(
            " ".join(["Nội dung dán được đọc tạm thời bằng ReadEase."] * 12)
        )
        window.paste_text_view.read_button.click()
        if not playback.selection_calls:
            raise AssertionError("pasted text did not reach the speech port")
        if repository.load_progress(active.id) != progress_before_paste:
            raise AssertionError("pasted text changed saved book progress")
        if window.feature_stack.currentWidget().objectName() != "pasteTextView":
            raise AssertionError("inline pasted-text reading changed feature view")
        window.feature_navigation.setCurrentIndex(2)
        if (
            window.feature_stack.currentWidget().objectName()
            != "externalReadingView"
        ):
            raise AssertionError("external reading feature is not independently visible")
        progress_before_external = repository.load_progress(active.id)
        controller.read_external_selection("Nội dung đang chọn trong Apple Books.")
        for sequence, state, is_selection in (
            (1, PlaybackState.LOADING, True),
            (2, PlaybackState.PLAYING, True),
            (3, PlaybackState.IDLE, False),
        ):
            playback.emit(
                PlaybackSnapshot(
                    state=state,
                    book_id=active.id,
                    segment_id=target.id,
                    is_selection=is_selection,
                    generation=3,
                    sequence=sequence,
                )
            )
            application.processEvents()
        if repository.load_progress(active.id) != progress_before_external:
            raise AssertionError("Apple Books selection changed saved book progress")
        window.feature_navigation.setCurrentIndex(0)
        reader = window.library_view.book_reader_view
        cursor = QTextCursor(reader.segment_blocks[target.id])
        selection_start = cursor.position()
        cursor.setPosition(selection_start)
        cursor.setPosition(
            min(selection_start + 12, len(reader.reader_text.toPlainText())),
            QTextCursor.MoveMode.KeepAnchor,
        )
        reader.reader_text.setTextCursor(cursor)
        reader.read_selection_button.click()
        window.play_button.click()
        if not playback.selection_calls or not playback.play_calls:
            raise AssertionError("selection or continuous playback did not reach its port")
        history = controller.state.session_history
        if [item.source for item in history] != [
            "book_selection",
            "apple_books",
            "paste",
        ]:
            raise AssertionError("three transient sources did not enter session history")
        external_item = next(item for item in history if item.source == "apple_books")
        external_action = next(
            action
            for action in window.session_history_menu.actions()
            if action.data() == external_item.id
        )
        calls_before_replay = len(playback.selection_calls)
        progress_before_replay = repository.load_progress(active.id)
        external_action.trigger()
        application.processEvents()
        if len(playback.selection_calls) != calls_before_replay + 1:
            raise AssertionError("session history action did not replay its item")
        if playback.selection_calls[-1][0] != "Nội dung đang chọn trong Apple Books.":
            raise AssertionError("session history replay changed the prepared text")
        if repository.load_progress(active.id) != progress_before_replay:
            raise AssertionError("session history replay changed saved book progress")

        count_before_scan = repository.count_books()
        window.import_path(_make_scan(sources / "scan.pdf"))
        if "OCR" not in (controller.state.error or ""):
            raise AssertionError("textless PDF did not show the OCR explanation")
        if repository.count_books() != count_before_scan:
            raise AssertionError("textless PDF changed the managed library")

        window.close()
        application.processEvents()
        restored_playback = FakePlayback(repository)
        restored = ReaderController(
            repository,
            service,
            restored_playback,
            dispatch=lambda action: action(),
        )
        if restored.state.active_segment_id != target.id:
            raise AssertionError("reader position did not restore after relaunch")
        if restored.state.session_history:
            raise AssertionError("session history survived app-controller relaunch")
        repository.close()
        print(
            "HEADLESS_READER_SMOKE PASS "
            "features=library,paste,external nested_reader=1 formats=epub,pdf "
            "paste=1 paste_progress_immutable=1 "
            "external_selection=1 external_progress_immutable=1 "
            "selection=1 continuous=1 session_history=1 replay=1 "
            "replay_progress_immutable=1 history_restart_clear=1 "
            "restore=1 scan_rejected=1"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
