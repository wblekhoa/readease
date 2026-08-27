from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from vieneu_reader.config import AppPaths
from vieneu_reader.domain.segmenter import MAX_PASTED_TEXT_CHARS
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.playback.coordinator import PlaybackSnapshot, PlaybackState
from vieneu_reader.storage.errors import RepositoryError
from vieneu_reader.storage.repository import LibraryRepository, Progress
from vieneu_reader.ui.controller import ExternalReadingState, ReaderController

from tests.importers.epub_fixture import make_epub, make_png


class FakePlayback:
    def __init__(self, repository=None):
        self.repository = repository
        self.listeners = []
        self.play_calls = []
        self.selection_calls = []
        self.rate_calls = []
        self.activation_calls = []
        self.play_projections = []
        self.activation_projections = []
        self.position_calls = []
        self.preference_calls = []
        self.commands = []

    def add_listener(self, listener):
        self.listeners.append(listener)

    def play(
        self,
        book,
        segment_id,
        voice_id,
        *,
        rate,
        settings,
        speech_text_by_segment=None,
    ):
        self.play_calls.append((book, segment_id, voice_id, rate, settings))
        self.play_projections.append(dict(speech_text_by_segment or {}))

    def play_selection(self, text, voice_id, *, rate, settings):
        self.selection_calls.append((text, voice_id, rate, settings))

    def set_rate(self, rate):
        self.rate_calls.append(rate)

    def pause(self):
        self.commands.append("pause")

    def resume(self):
        self.commands.append("resume")

    def stop(self):
        self.commands.append("stop")

    def next(self):
        self.commands.append("next")

    def previous(self):
        self.commands.append("previous")

    def activate_book(
        self,
        book,
        segment_id,
        voice_id,
        *,
        rate,
        speech_text_by_segment=None,
    ):
        self.activation_calls.append((book.id, segment_id, voice_id, rate))
        self.activation_projections.append(dict(speech_text_by_segment or {}))

    def save_position(self, book, segment_id, voice_id, *, rate):
        self.position_calls.append((book.id, segment_id, voice_id, rate))
        if self.repository is not None:
            self.repository.save_progress(
                Progress(book.id, segment_id, rate, voice_id)
            )

    def save_preferences(self, book, segment_id, voice_id, *, rate):
        self.preference_calls.append((book.id, segment_id, voice_id, rate))
        if self.repository is not None:
            self.repository.save_preferences(
                Progress(book.id, segment_id, rate, voice_id)
            )

    def emit(self, snapshot):
        for listener in tuple(self.listeners):
            listener(snapshot)


class ReaderControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.playback = FakePlayback(self.repository)
        self.sources = root / "sources"
        self.sources.mkdir()

    def tearDown(self):
        self.repository.close()
        self.temp_dir.cleanup()

    def make_controller(self):
        return ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=lambda action: action(),
        )

    def test_empty_library_invites_opening_a_book_or_pasting_text(self):
        controller = self.make_controller()

        self.assertEqual(controller.state.library, ())
        self.assertIsNone(controller.state.active_book_id)
        self.assertTrue(controller.state.can_open_book)
        self.assertFalse(controller.state.can_play)
        self.assertEqual(controller.state.status, "Mở sách hoặc dán nội dung để bắt đầu.")
        self.assertEqual(controller.state.reading_location, "")

    def test_pasted_text_is_readable_without_a_book_and_uses_preferences(self):
        controller = self.make_controller()
        controller.set_voice("Trúc Ly")
        controller.set_rate(1.25)

        controller.read_pasted_text("  Xin chào.\n\nĐây là nội dung được dán.  ")

        text, voice_id, rate, _settings = self.playback.selection_calls[-1]
        self.assertEqual(text, "Xin chào.\n\nĐây là nội dung được dán.")
        self.assertEqual((voice_id, rate), ("Trúc Ly", 1.25))
        self.assertEqual(self.repository.list_books(), ())

    def test_external_selection_uses_transient_playback_and_active_preferences(self):
        controller = self.make_controller()
        controller.set_voice("Trúc Ly")
        controller.set_rate(1.25)

        command = getattr(controller, "read_external_selection", None)
        self.assertIsNotNone(command, "external-selection command must exist")
        command("  Nội dung từ Apple Books.  ")

        text, voice_id, rate, _settings = self.playback.selection_calls[-1]
        self.assertEqual(text, "Nội dung từ Apple Books.")
        self.assertEqual((voice_id, rate), ("Trúc Ly", 1.25))
        self.assertEqual(self.repository.list_books(), ())

    def test_external_ready_signal_updates_only_the_companion_state(self):
        controller = self.make_controller()
        original_status = controller.state.status

        self.assertEqual(
            controller.state.external_reading_state,
            ExternalReadingState.STARTING,
        )

        controller.external_selection_failed("ready")

        self.assertEqual(
            controller.state.external_reading_state,
            ExternalReadingState.READY,
        )
        self.assertEqual(controller.state.status, original_status)
        self.assertIsNone(controller.state.error)

    def test_external_permission_and_success_have_distinct_states(self):
        controller = self.make_controller()

        controller.external_selection_failed("permission_required")

        self.assertEqual(
            controller.state.external_reading_state,
            ExternalReadingState.PERMISSION_REQUIRED,
        )

        controller.read_external_selection("Nội dung đã chọn.")

        self.assertEqual(
            controller.state.external_reading_state,
            ExternalReadingState.RECEIVED,
        )
        self.assertFalse(controller.state.can_open_accessibility_settings)

    def test_rejected_external_playback_does_not_report_received(self):
        controller = self.make_controller()
        controller.external_selection_failed("ready")

        with patch.object(
            self.playback,
            "play_selection",
            side_effect=RuntimeError("playback rejected"),
        ):
            with self.assertRaisesRegex(RuntimeError, "playback rejected"):
                controller.read_external_selection("Không được nhận nhầm.")

        self.assertEqual(
            controller.state.external_reading_state,
            ExternalReadingState.READY,
        )

    def test_valid_transient_reads_enter_session_history_newest_first(self):
        controller = self.make_controller()

        controller.read_pasted_text("Nội dung dán.")
        controller.read_selection("Nội dung chọn trong sách.")
        controller.read_external_selection("Nội dung từ Apple Books.")

        self.assertEqual(
            [item.source for item in controller.state.session_history],
            ["apple_books", "book_selection", "paste"],
        )
        self.assertEqual(
            [item.source_label for item in controller.state.session_history],
            ["Apple Books", "Trong sách", "Dán nội dung"],
        )
        self.assertEqual(
            [item.preview for item in controller.state.session_history],
            [
                "Nội dung từ Apple Books.",
                "Nội dung chọn trong sách.",
                "Nội dung dán.",
            ],
        )

    def test_session_history_keeps_only_ten_latest_items(self):
        controller = self.make_controller()

        for number in range(11):
            controller.read_pasted_text(f"Nội dung {number}.")

        self.assertEqual(len(controller.state.session_history), 10)
        self.assertEqual(controller.state.session_history[0].preview, "Nội dung 10.")
        self.assertEqual(controller.state.session_history[-1].preview, "Nội dung 1.")

    def test_duplicate_transient_text_moves_existing_item_to_front(self):
        controller = self.make_controller()
        controller.read_pasted_text("Nội dung giống nhau.")
        original_id = controller.state.session_history[0].id
        controller.read_external_selection("Nội dung khác.")

        controller.read_selection("  Nội dung giống nhau.  ")

        self.assertEqual(len(controller.state.session_history), 2)
        self.assertEqual(controller.state.session_history[0].id, original_id)
        self.assertEqual(controller.state.session_history[0].source, "book_selection")

    def test_replay_uses_exact_prepared_text_and_current_preferences(self):
        controller = self.make_controller()
        controller.read_pasted_text("  Dòng một.\n\nDòng hai.  ")
        item_id = controller.state.session_history[0].id
        controller.set_voice("Trúc Ly")
        controller.set_rate(1.5)
        calls_before_replay = len(self.playback.selection_calls)

        controller.replay_session_reading(item_id)

        self.assertEqual(len(self.playback.selection_calls), calls_before_replay + 1)
        text, voice_id, rate, _settings = self.playback.selection_calls[-1]
        self.assertEqual(text, "Dòng một.\n\nDòng hai.")
        self.assertEqual((voice_id, rate), ("Trúc Ly", 1.5))
        self.assertEqual(len(controller.state.session_history), 1)
        self.assertEqual(controller.state.session_history[0].id, item_id)

    def test_invalid_or_rejected_text_never_enters_session_history(self):
        controller = self.make_controller()

        controller.read_pasted_text("   ")
        controller.read_external_selection("a" * (MAX_PASTED_TEXT_CHARS + 1))

        self.assertEqual(controller.state.session_history, ())

    def test_session_history_is_recorded_only_after_playback_accepts(self):
        controller = self.make_controller()

        with patch.object(
            self.playback,
            "play_selection",
            side_effect=RuntimeError("playback rejected"),
        ):
            with self.assertRaisesRegex(RuntimeError, "playback rejected"):
                controller.read_pasted_text("Không được ghi khi playback từ chối.")

        self.assertEqual(controller.state.session_history, ())

    def test_session_history_preview_is_single_line_and_bounded(self):
        controller = self.make_controller()

        controller.read_pasted_text("Một\n\n" + "nội dung rất dài " * 10)

        preview = controller.state.session_history[0].preview
        self.assertNotIn("\n", preview)
        self.assertLessEqual(len(preview), 72)
        self.assertTrue(preview.endswith("…"))

    def test_session_history_can_be_cleared(self):
        controller = self.make_controller()
        controller.read_pasted_text("Chỉ nằm trong phiên này.")

        controller.clear_session_history()

        self.assertEqual(controller.state.session_history, ())

    def test_fresh_controller_starts_with_empty_session_history(self):
        fresh_controller = self.make_controller()

        self.assertEqual(fresh_controller.state.session_history, ())

    def test_external_selection_failure_is_safe_and_does_not_start_playback(self):
        controller = self.make_controller()

        command = getattr(controller, "external_selection_failed", None)
        self.assertIsNotNone(command, "external-selection failure route must exist")
        command("permission_required")

        self.assertEqual(self.playback.selection_calls, [])
        self.assertIn("Trợ năng", controller.state.error)
        self.assertNotIn("permission_required", controller.state.error)
        self.assertTrue(controller.state.can_open_accessibility_settings)

    def test_non_permission_external_selection_failure_hides_settings_action(self):
        controller = self.make_controller()

        controller.external_selection_failed("no_selection")

        self.assertFalse(controller.state.can_open_accessibility_settings)

    def test_successful_external_selection_clears_settings_action(self):
        controller = self.make_controller()
        controller.external_selection_failed("permission_required")

        controller.read_external_selection("Nội dung đã chọn.")

        self.assertFalse(controller.state.can_open_accessibility_settings)

    def test_oversized_external_selection_fails_closed(self):
        controller = self.make_controller()

        command = getattr(controller, "read_external_selection", None)
        self.assertIsNotNone(command, "external-selection command must exist")
        command("a" * (MAX_PASTED_TEXT_CHARS + 1))

        self.assertEqual(self.playback.selection_calls, [])
        self.assertIn("100.000", controller.state.error)

    def test_blank_pasted_text_is_rejected_without_starting_playback(self):
        controller = self.make_controller()

        controller.read_pasted_text(" \n\t ")

        self.assertEqual(self.playback.selection_calls, [])
        self.assertEqual(controller.state.error, "Hãy dán nội dung trước khi bấm đọc.")

    def test_oversized_pasted_text_is_rejected_without_starting_playback(self):
        controller = self.make_controller()

        controller.read_pasted_text("a" * (MAX_PASTED_TEXT_CHARS + 1))

        self.assertEqual(self.playback.selection_calls, [])
        self.assertEqual(
            controller.state.error,
            "Nội dung dán vượt quá giới hạn 100.000 ký tự.",
        )

    def test_changing_voice_stops_pasted_text_playback_without_a_book(self):
        controller = self.make_controller()
        controller.read_pasted_text("Nội dung đang được đọc.")
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                is_selection=True,
                generation=1,
                sequence=1,
            )
        )

        controller.set_voice("Trúc Ly")

        self.assertEqual(self.playback.commands[-1], "stop")
        self.assertEqual(controller.state.voice_id, "Trúc Ly")

    def test_reading_location_tracks_chapter_and_segment_navigation(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))

        self.assertEqual(controller.state.reading_location, "Chương 1/2 · Đoạn 1/2")

        stored = self.repository.get_book(controller.state.active_book_id)
        target = stored.book.chapters[-1].segments[-1]
        controller.select_segment(target.id)

        self.assertEqual(controller.state.reading_location, "Chương 2/2 · Đoạn 2/2")

    def test_import_opens_book_and_duplicate_focuses_the_same_item(self):
        controller = self.make_controller()
        source = make_epub(self.sources, spine=("chapter-2", "chapter-1"))

        controller.import_book(source)
        first_state = controller.state
        controller.import_book(source)

        self.assertEqual(len(controller.state.library), 1)
        self.assertEqual(controller.state.active_book_id, first_state.active_book_id)
        self.assertEqual([chapter.title for chapter in controller.state.chapters], ["Hai", "Một"])
        self.assertTrue(controller.state.segments)
        self.assertTrue(controller.state.can_play)
        self.assertEqual(controller.state.status, "Sách đã có trong thư viện; đã mở lại.")

    def test_epub_figures_are_transient_and_add_one_stable_spoken_cue(self):
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1><p>Đoạn trước hình.</p>
        <div><img src="images/diagram.png" alt="Sơ đồ đọc sách"/></div>
        <p>Đoạn sau hình.</p>
        </body></html>"""
        source = make_epub(
            self.sources,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
            image_entries={
                "images/diagram.png": (make_png(320, 200), "image/png"),
            },
        )
        result = self.service.import_book(source)
        payload_before = self.repository._connection.execute(
            "SELECT document_json FROM books WHERE id = ?",
            (result.book.id,),
        ).fetchone()["document_json"]

        controller = self.make_controller()

        payload_after = self.repository._connection.execute(
            "SELECT document_json FROM books WHERE id = ?",
            (result.book.id,),
        ).fetchone()["document_json"]
        self.assertEqual(payload_after, payload_before)
        self.assertEqual(len(controller.state.figures), 1)
        figure = controller.state.figures[0]
        self.assertEqual(figure.number, 1)
        self.assertEqual(figure.image_bytes, make_png(320, 200))
        source_segment = next(
            segment
            for segment in result.book.chapters[0].segments
            if segment.id == figure.anchor_segment_id
        )
        projected = self.playback.activation_projections[-1]
        self.assertEqual(
            projected[source_segment.id],
            f"{source_segment.text} Mời bạn xem Hình 1.",
        )
        self.assertNotIn("Mời bạn xem", source_segment.text)

        controller.select_segment(source_segment.id)
        controller.play_current()

        self.assertEqual(self.playback.play_projections[-1], projected)

    def test_reselecting_active_book_is_a_true_noop_during_playback(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))
        active = controller.state.active_book_id
        segment = controller.state.active_segment_id
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=active,
                segment_id=segment,
                generation=1,
                sequence=1,
            )
        )
        commands_before = list(self.playback.commands)

        controller.select_book(active)

        self.assertEqual(controller.state.playback_state, PlaybackState.PLAYING)
        self.assertEqual(self.playback.commands, commands_before)

    def test_switching_book_activates_the_new_playback_context(self):
        controller = self.make_controller()
        first = make_epub(self.sources, name="first.epub", title="Sách một")
        second = make_epub(self.sources, name="second.epub", title="Sách hai")
        controller.import_book(first)
        controller.import_book(second)

        active = controller.state
        self.assertEqual(self.playback.activation_calls[-1], (
            active.active_book_id,
            active.active_segment_id,
            active.voice_id,
            active.rate,
        ))

    def test_new_controller_restores_saved_segment_voice_and_rate(self):
        controller = self.make_controller()
        source = make_epub(self.sources)
        controller.import_book(source)
        stored = self.repository.get_book(controller.state.active_book_id)
        target = stored.book.chapters[1].segments[0]
        self.repository.save_progress(
            Progress(stored.book.id, target.id, 1.3, "Trúc Ly")
        )

        restored = ReaderController(
            self.repository,
            self.service,
            FakePlayback(),
            dispatch=lambda action: action(),
        )

        self.assertEqual(restored.state.active_book_id, stored.book.id)
        self.assertEqual(restored.state.active_segment_id, target.id)
        self.assertEqual(restored.state.active_chapter_id, stored.book.chapters[1].id)
        self.assertEqual(restored.state.voice_id, "Trúc Ly")
        self.assertEqual(restored.state.rate, 1.3)

    def test_new_controller_reopens_the_last_active_book(self):
        controller = self.make_controller()
        first = make_epub(self.sources, name="first.epub", title="Sách một")
        second = make_epub(self.sources, name="second.epub", title="Sách hai")
        controller.import_book(first)
        first_id = controller.state.active_book_id
        controller.import_book(second)
        second_id = controller.state.active_book_id
        controller.select_book(first_id)

        restored = self.make_controller()

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(restored.state.active_book_id, first_id)

    def test_play_current_and_selection_use_active_preferences(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))
        controller.set_voice("Trúc Ly")
        controller.set_rate(1.2)

        controller.play_current()
        controller.read_selection("  Chỉ đọc phần này.  ")

        self.assertEqual(self.playback.play_calls[0][1], controller.state.active_segment_id)
        self.assertEqual(self.playback.play_calls[0][2:4], ("Trúc Ly", 1.2))
        self.assertEqual(self.playback.selection_calls[0][0:3], (
            "Chỉ đọc phần này.",
            "Trúc Ly",
            1.2,
        ))

    def test_playback_snapshot_moves_highlight_and_maps_status(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))
        stored = self.repository.get_book(controller.state.active_book_id)
        target = stored.book.chapters[1].segments[0]

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=stored.book.id,
                segment_id=target.id,
                rate=1.0,
            )
        )

        self.assertEqual(controller.state.active_segment_id, target.id)
        self.assertEqual(controller.state.active_chapter_id, stored.book.chapters[1].id)

    def test_selection_snapshot_is_exposed_without_moving_book_location(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))
        location = controller.state.reading_location

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=controller.state.active_book_id,
                segment_id=controller.state.active_segment_id,
                is_selection=True,
                generation=1,
                sequence=1,
            )
        )

        self.assertTrue(controller.state.is_selection_playback)
        self.assertEqual(controller.state.reading_location, location)
        self.assertEqual(controller.state.status, "Đang đọc")

    def test_long_selection_snapshot_exposes_readable_part_progress(self):
        controller = self.make_controller()

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                is_selection=True,
                selection_part_index=2,
                selection_part_count=7,
                generation=1,
                sequence=1,
            )
        )

        self.assertEqual(controller.state.status, "Đang đọc đoạn 2/7")

    def test_corrupt_book_shows_safe_error_and_does_not_change_library(self):
        controller = self.make_controller()
        source = self.sources / "broken.epub"
        source.write_bytes(b"broken")

        controller.import_book(source)

        self.assertEqual(controller.state.library, ())
        self.assertIn("EPUB", controller.state.error)
        self.assertFalse(controller.state.can_play)

    def test_storage_failure_shows_safe_error_and_preserves_source(self):
        controller = self.make_controller()
        source = make_epub(self.sources)

        with patch.object(
            self.repository,
            "add_book",
            side_effect=sqlite3.OperationalError("database or disk is full"),
        ):
            controller.import_book(source)

        self.assertTrue(source.is_file())
        self.assertEqual(controller.state.library, ())
        self.assertIn("thư viện", controller.state.error)
        self.assertEqual(controller.state.status, "Không thể mở sách.")
        self.assertEqual(list(self.paths.books.glob("*.epub")), [])

    def test_unknown_xml_encoding_shows_safe_error(self):
        controller = self.make_controller()
        chapter = '''<?xml version="1.0" encoding="x-unknown"?>
        <html xmlns="http://www.w3.org/1999/xhtml"><body><p>Nội dung.</p></body></html>
        '''
        source = make_epub(
            self.sources,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
        )

        controller.import_book(source)

        self.assertIn("XML", controller.state.error)
        self.assertEqual(controller.state.library, ())
        self.assertEqual(list(self.paths.books.glob("*.epub")), [])

    def test_post_commit_refresh_failure_shows_restart_recovery(self):
        controller = self.make_controller()
        source = make_epub(self.sources)
        real_add_book = self.repository.add_book

        def add_then_close(book, managed_path):
            real_add_book(book, managed_path)
            self.repository._connection.close()

        with patch.object(self.repository, "add_book", side_effect=add_then_close):
            controller.import_book(source)

        verifier = LibraryRepository(self.paths.database)
        try:
            self.assertEqual(verifier.count_books(), 1)
            self.assertEqual(len(list(self.paths.books.glob("*.epub"))), 1)
        finally:
            verifier.close()
        self.assertEqual(controller.state.library, ())
        self.assertIn("đã được thêm", controller.state.error)
        self.assertEqual(
            controller.state.status,
            "Đã thêm sách nhưng chưa thể tải lại.",
        )

    def test_bootstrap_handles_malformed_persisted_document(self):
        result = self.service.import_book(make_epub(self.sources))
        with self.repository._connection:
            self.repository._connection.execute(
                "UPDATE books SET document_json = '{' WHERE id = ?",
                (result.book.id,),
            )

        controller = self.make_controller()

        self.assertEqual(controller.state.library, ())
        self.assertIn("thư viện", controller.state.error)
        self.assertEqual(controller.state.status, "Không thể tải thư viện cục bộ.")

    def test_bootstrap_handles_invalid_persisted_progress(self):
        result = self.service.import_book(make_epub(self.sources))
        segment_id = result.book.chapters[0].segments[0].id
        with self.repository._connection:
            self.repository._connection.execute(
                "INSERT INTO progress(book_id, segment_id, playback_rate, voice_id) "
                "VALUES (?, ?, ?, ?)",
                (result.book.id, segment_id, "oops", "Adam"),
            )

        controller = self.make_controller()

        self.assertEqual(controller.state.library[0].id, result.book.id)
        self.assertIsNone(controller.state.active_book_id)
        self.assertIn("thư viện", controller.state.error)
        self.assertEqual(controller.state.status, "Không thể tải thư viện cục bộ.")

    def test_select_book_storage_failure_is_reported_without_sqlite_coupling(self):
        controller = self.make_controller()
        first = make_epub(self.sources, name="first.epub", title="Một")
        second = make_epub(self.sources, name="second.epub", title="Hai")
        controller.import_book(first)
        first_book_id = controller.state.active_book_id
        stored_second = self.service.import_book(second)

        with patch.object(
            self.repository,
            "get_book",
            side_effect=RepositoryError("read failed"),
        ):
            controller.select_book(stored_second.book.id)

        self.assertIn("thư viện", controller.state.error)
        self.assertEqual(controller.state.active_book_id, first_book_id)

    def test_transport_commands_delegate_to_playback(self):
        controller = self.make_controller()

        controller.previous()
        controller.next()
        controller.pause()
        controller.resume()
        controller.stop()

        self.assertEqual(
            self.playback.commands,
            ["previous", "next", "pause", "resume", "stop"],
        )

    def test_manual_segment_selection_stops_audio_and_restores_after_restart(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))
        stored = self.repository.get_book(controller.state.active_book_id)
        target = stored.book.chapters[1].segments[0]

        controller.select_segment(target.id)

        self.assertEqual(self.playback.commands[-1], "stop")
        self.assertEqual(self.playback.position_calls[-1][1], target.id)
        restored = ReaderController(
            self.repository,
            self.service,
            FakePlayback(),
            dispatch=lambda action: action(),
        )
        self.assertEqual(restored.state.active_segment_id, target.id)

    def test_selecting_active_chapter_returns_to_its_first_segment(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))
        stored = self.repository.get_book(controller.state.active_book_id)
        chapter = stored.book.chapters[0]
        controller.select_segment(chapter.segments[1].id)

        controller.select_chapter(chapter.id)

        self.assertEqual(controller.state.active_segment_id, chapter.segments[0].id)

    def test_voice_change_stops_audio_and_persists_preference(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))

        controller.set_voice("Trúc Ly")

        self.assertEqual(self.playback.commands[-1], "stop")
        self.assertEqual(self.playback.preference_calls[-1][2], "Trúc Ly")
        restored = ReaderController(
            self.repository,
            self.service,
            FakePlayback(),
            dispatch=lambda action: action(),
        )
        self.assertEqual(restored.state.voice_id, "Trúc Ly")

    def test_rate_change_persists_preference(self):
        controller = self.make_controller()
        controller.import_book(make_epub(self.sources))

        controller.set_rate(1.4)

        self.assertEqual(self.playback.preference_calls[-1][3], 1.4)
        restored = ReaderController(
            self.repository,
            self.service,
            FakePlayback(),
            dispatch=lambda action: action(),
        )
        self.assertEqual(restored.state.rate, 1.4)

    def test_playback_callback_uses_injected_dispatch_boundary(self):
        queued = []
        controller = ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=queued.append,
        )
        before = controller.state

        self.playback.emit(PlaybackSnapshot(state=PlaybackState.LOADING))

        self.assertEqual(controller.state, before)
        self.assertEqual(len(queued), 1)
        queued.pop()()
        self.assertEqual(controller.state.playback_state, PlaybackState.LOADING)

    def test_delayed_snapshot_from_an_old_generation_is_ignored(self):
        queued = []
        controller = ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=queued.append,
        )
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                generation=1,
                sequence=1,
            )
        )
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.IDLE,
                generation=2,
                sequence=2,
            )
        )

        queued.pop(1)()
        queued.pop(0)()

        self.assertEqual(controller.state.playback_state, PlaybackState.IDLE)

    def test_queued_stop_snapshot_does_not_revert_manual_segment_selection(self):
        queued = []
        controller = ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=queued.append,
        )
        controller.import_book(make_epub(self.sources))
        stored = self.repository.get_book(controller.state.active_book_id)
        old_segment = stored.book.chapters[0].segments[0]
        target = stored.book.chapters[1].segments[0]

        controller.select_segment(target.id)
        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.IDLE,
                book_id=stored.book.id,
                segment_id=old_segment.id,
                generation=1,
                sequence=1,
            )
        )
        queued.pop()()

        self.assertEqual(controller.state.active_segment_id, target.id)

    def test_queued_snapshot_from_previous_book_cannot_overwrite_new_preferences(self):
        queued = []
        controller = ReaderController(
            self.repository,
            self.service,
            self.playback,
            dispatch=queued.append,
        )
        controller.import_book(make_epub(self.sources, name="first.epub", title="Một"))
        first_book = controller.state.active_book_id
        first_segment = controller.state.active_segment_id
        controller.import_book(make_epub(self.sources, name="second.epub", title="Hai"))
        second_book = controller.state.active_book_id
        self.assertNotEqual(first_book, second_book)
        self.assertEqual(controller.state.rate, 1.0)

        self.playback.emit(
            PlaybackSnapshot(
                state=PlaybackState.PLAYING,
                book_id=first_book,
                segment_id=first_segment,
                rate=1.4,
                is_selection=True,
                generation=1,
                sequence=1,
            )
        )
        queued.pop()()

        self.assertEqual(controller.state.active_book_id, second_book)
        self.assertEqual(controller.state.rate, 1.0)


if __name__ == "__main__":
    unittest.main()
