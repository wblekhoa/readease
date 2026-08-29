"""UI-independent orchestration from services to immutable reader view state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Mapping, Protocol

from vieneu_reader.domain.models import BookDocument, Chapter, Segment
from vieneu_reader.domain.presentation import BookPresentation, FigureRef
from vieneu_reader.domain.segmenter import prepare_pasted_text
from vieneu_reader.importers.errors import BookImportError
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.playback.coordinator import PlaybackSnapshot, PlaybackState
from vieneu_reader.playback.preferences import (
    DEFAULT_RATE,
    DEFAULT_VOICE_ID,
    VoicePreferenceStore,
)
from vieneu_reader.speech.contracts import SynthesisSettings
from vieneu_reader.storage.errors import RepositoryError
from vieneu_reader.storage.repository import LibraryRepository


@dataclass(frozen=True, slots=True)
class LibraryItem:
    id: str
    title: str
    source_format: str


@dataclass(frozen=True, slots=True)
class ChapterItem:
    id: str
    title: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class SegmentItem:
    id: str
    chapter_id: str
    ordinal: int
    text: str


@dataclass(frozen=True, slots=True)
class FigureItem:
    id: str
    number: int
    anchor_segment_id: str
    placement: str
    alt_text: str | None
    alt_is_generic: bool
    media_type: str
    width: int | None
    height: int | None
    image_bytes: bytes | None


@dataclass(frozen=True, slots=True)
class SessionReadingItem:
    id: str
    source: str
    source_label: str
    preview: str


class ExternalReadingState(str, Enum):
    """Transient lifecycle of the explicit Apple Books shortcut."""

    STARTING = "starting"
    READY = "ready"
    RECEIVED = "received"
    PERMISSION_REQUIRED = "permission_required"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class _StoredSessionReading:
    item: SessionReadingItem
    text: str


@dataclass(frozen=True, slots=True)
class ReaderViewState:
    library: tuple[LibraryItem, ...] = ()
    active_book_id: str | None = None
    chapters: tuple[ChapterItem, ...] = ()
    active_chapter_id: str | None = None
    segments: tuple[SegmentItem, ...] = ()
    figures: tuple[FigureItem, ...] = ()
    active_segment_id: str | None = None
    voice_id: str = DEFAULT_VOICE_ID
    rate: float = DEFAULT_RATE
    playback_state: PlaybackState = PlaybackState.IDLE
    is_selection_playback: bool = False
    status: str = "Mở sách hoặc dán nội dung để bắt đầu."
    error: str | None = None
    external_reading_state: ExternalReadingState = ExternalReadingState.STARTING
    can_open_accessibility_settings: bool = False
    can_open_book: bool = True
    can_play: bool = False
    session_history: tuple[SessionReadingItem, ...] = ()

    @property
    def reading_location(self) -> str:
        """Return a concise one-based chapter and paragraph position."""

        if self.active_chapter_id is None or self.active_segment_id is None:
            return ""
        chapter_position = next(
            (
                index
                for index, chapter in enumerate(self.chapters, start=1)
                if chapter.id == self.active_chapter_id
            ),
            None,
        )
        segment_position = next(
            (
                index
                for index, segment in enumerate(self.segments, start=1)
                if segment.id == self.active_segment_id
            ),
            None,
        )
        if chapter_position is None or segment_position is None:
            return ""
        return (
            f"Chương {chapter_position}/{len(self.chapters)} · "
            f"Đoạn {segment_position}/{len(self.segments)}"
        )


class PlaybackPort(Protocol):
    def add_listener(self, listener) -> None: ...
    def play(
        self,
        book,
        segment_id,
        voice_id,
        *,
        rate,
        settings,
        speech_text_by_segment: Mapping[str, str] | None = None,
    ) -> None: ...
    def play_selection(self, text, voice_id, *, rate, settings) -> None: ...
    def set_rate(self, rate) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    def next(self) -> None: ...
    def previous(self) -> None: ...
    def activate_book(
        self,
        book,
        segment_id,
        voice_id,
        *,
        rate,
        speech_text_by_segment: Mapping[str, str] | None = None,
    ) -> None: ...
    def save_position(self, book, segment_id, voice_id, *, rate) -> None: ...
    def save_preferences(self, book, segment_id, voice_id, *, rate) -> None: ...


class ReaderController:
    _SESSION_HISTORY_LIMIT = 10
    _SESSION_PREVIEW_LIMIT = 72
    _SESSION_SOURCE_LABELS = {
        "paste": "Dán nội dung",
        "book_selection": "Trong sách",
        "apple_books": "Apple Books",
    }

    def __init__(
        self,
        repository: LibraryRepository,
        library_service: LibraryService,
        playback: PlaybackPort,
        *,
        dispatch: Callable[[Callable[[], None]], None],
        voice_store: VoicePreferenceStore | None = None,
    ):
        self._repository = repository
        self._library_service = library_service
        self._playback = playback
        self._dispatch = dispatch
        self._book: BookDocument | None = None
        self._managed_path: Path | None = None
        self._presentation: BookPresentation | None = None
        self._chapter_content_cache: dict[
            str,
            tuple[tuple[SegmentItem, ...], tuple[FigureItem, ...]],
        ] = {}
        self._speech_text_by_segment: dict[str, str] = {}
        self._session_history_entries: list[_StoredSessionReading] = []
        self._status_before_external_failure: str | None = None
        self._next_session_reading_id = 1
        self._settings = SynthesisSettings()
        self._voice_store = voice_store
        self._state = (
            ReaderViewState()
            if voice_store is None
            else ReaderViewState(
                voice_id=voice_store.load_voice(),
                rate=voice_store.load_rate(),
            )
        )
        self._listeners = []
        self._last_playback_order = (-1, -1)
        self._playback.add_listener(self._dispatch_playback)
        try:
            self._refresh_library()
            if self._state.library:
                active_book_id = self._repository.load_active_book_id()
                self._select_book(active_book_id or self._state.library[0].id)
        except RepositoryError:
            self._set_state(
                error="Không thể tải thư viện cục bộ. Hãy mở lại ứng dụng.",
                status="Không thể tải thư viện cục bộ.",
            )

    @property
    def state(self) -> ReaderViewState:
        return self._state

    def add_listener(self, listener) -> None:
        self._listeners.append(listener)
        listener(self._state)

    def _emit(self) -> None:
        for listener in tuple(self._listeners):
            listener(self._state)

    def _set_state(self, **changes) -> None:
        if "error" in changes and "can_open_accessibility_settings" not in changes:
            changes["can_open_accessibility_settings"] = False
        self._state = replace(self._state, **changes)
        self._emit()

    def _refresh_library(self) -> None:
        items = tuple(
            LibraryItem(
                id=stored.book.id,
                title=stored.book.title,
                source_format=stored.book.source_format,
            )
            for stored in self._repository.list_books()
        )
        self._set_state(library=items)

    def import_book(self, source: Path) -> None:
        result = None
        try:
            result = self._library_service.import_book(Path(source))
            self._refresh_library()
            self._select_book(result.book.id)
        except BookImportError as error:
            self._set_state(
                error=str(error),
                status="Không thể mở sách.",
            )
            return
        except RepositoryError:
            if result is not None and not result.was_existing:
                error = (
                    "Sách đã được thêm nhưng chưa thể tải lại. "
                    "Hãy mở lại ứng dụng."
                )
                status = "Đã thêm sách nhưng chưa thể tải lại."
            else:
                error = "Không thể tải thư viện cục bộ. Hãy mở lại ứng dụng."
                status = "Không thể tải thư viện cục bộ."
            self._set_state(error=error, status=status)
            return
        self._set_state(
            status=(
                "Sách đã có trong thư viện; đã mở lại."
                if result.was_existing
                else "Đã thêm sách vào thư viện."
            ),
            error=None,
        )

    def select_book(self, book_id: str) -> None:
        try:
            self._select_book(book_id)
        except RepositoryError:
            self._set_state(
                error="Không thể tải sách từ thư viện cục bộ. Hãy mở lại ứng dụng.",
                status="Không thể tải thư viện cục bộ.",
            )

    def _select_book(self, book_id: str) -> None:
        if self._book is not None and self._book.id == book_id:
            return
        stored = self._repository.get_book(book_id)
        if stored is None:
            self._set_state(error="Không tìm thấy sách trong thư viện.")
            return
        book = stored.book
        segments = tuple(
            segment for chapter in book.chapters for segment in chapter.segments
        )
        if not segments:
            self._set_state(error="Sách không có đoạn văn có thể đọc.", can_play=False)
            return
        progress = self._repository.load_progress(book.id)
        segment_id = progress.segment_id if progress else segments[0].id
        if all(segment.id != segment_id for segment in segments):
            segment_id = segments[0].id
        voice_id = progress.voice_id if progress else self._state.voice_id
        rate = progress.playback_rate if progress else self._state.rate
        presentation = self._library_service.presentation_for(book, stored.managed_path)
        speech_text_by_segment = self._speech_projection(book, presentation)
        self._repository.save_active_book_id(book.id)
        self._playback.activate_book(
            book,
            segment_id,
            voice_id,
            rate=rate,
            speech_text_by_segment=speech_text_by_segment,
        )
        self._book = book
        self._managed_path = stored.managed_path
        self._presentation = presentation
        self._chapter_content_cache = {}
        self._speech_text_by_segment = speech_text_by_segment
        chapter = self._chapter_for_segment(book, segment_id)
        segment_items, figure_items = self._chapter_content(chapter)
        self._state = replace(
            self._state,
            active_book_id=book.id,
            chapters=tuple(
                ChapterItem(chapter.id, chapter.title, chapter.ordinal)
                for chapter in book.chapters
            ),
            active_chapter_id=chapter.id,
            segments=segment_items,
            figures=figure_items,
            active_segment_id=segment_id,
            voice_id=voice_id,
            rate=rate,
            playback_state=PlaybackState.IDLE,
            status="Sẵn sàng đọc.",
            error=None,
            can_play=True,
        )
        self._emit()

    @staticmethod
    def _chapter_for_segment(book: BookDocument, segment_id: str) -> Chapter:
        for chapter in book.chapters:
            if any(segment.id == segment_id for segment in chapter.segments):
                return chapter
        return book.chapters[0]

    @staticmethod
    def _speech_projection(
        book: BookDocument,
        presentation: BookPresentation,
    ) -> dict[str, str]:
        before: dict[str, list[str]] = {}
        after: dict[str, list[str]] = {}
        for chapter in presentation.chapters:
            for figure in chapter.figures:
                cue = f"Mời bạn xem Hình {figure.number}."
                target = before if figure.placement == "before" else after
                target.setdefault(figure.anchor_segment_id, []).append(cue)
        projection: dict[str, str] = {}
        for chapter in book.chapters:
            for segment in chapter.segments:
                pieces = (*before.get(segment.id, ()), segment.text, *after.get(segment.id, ()))
                spoken = " ".join(pieces)
                if spoken != segment.text:
                    projection[segment.id] = spoken
        return projection

    def _chapter_content(
        self,
        chapter: Chapter,
    ) -> tuple[tuple[SegmentItem, ...], tuple[FigureItem, ...]]:
        cached = self._chapter_content_cache.get(chapter.id)
        if cached is not None:
            return cached
        segments = tuple(
            SegmentItem(segment.id, segment.chapter_id, segment.ordinal, segment.text)
            for segment in chapter.segments
        )
        figure_refs: tuple[FigureRef, ...] = ()
        if self._presentation is not None:
            chapter_presentation = self._presentation.chapter(chapter.id)
            if chapter_presentation is not None:
                figure_refs = chapter_presentation.figures
        assets = (
            self._library_service.assets_for(
                self._book,
                self._managed_path,
                figure_refs,
            )
            if self._book is not None and self._managed_path is not None
            else {}
        )
        figures = tuple(
            FigureItem(
                id=figure.id,
                number=figure.number,
                anchor_segment_id=figure.anchor_segment_id,
                placement=figure.placement,
                alt_text=figure.alt_text,
                alt_is_generic=figure.alt_is_generic,
                media_type=figure.media_type,
                width=figure.width,
                height=figure.height,
                image_bytes=assets.get(figure.asset_path),
            )
            for figure in figure_refs
        )
        content = (segments, figures)
        self._chapter_content_cache = {chapter.id: content}
        return content

    def select_chapter(self, chapter_id: str) -> None:
        if self._book is None:
            return
        chapter = next(
            (item for item in self._book.chapters if item.id == chapter_id),
            None,
        )
        if chapter is None or not chapter.segments:
            return
        if self._state.active_segment_id == chapter.segments[0].id:
            return
        self._playback.stop()
        segment_items, figure_items = self._chapter_content(chapter)
        self._set_state(
            active_chapter_id=chapter.id,
            segments=segment_items,
            figures=figure_items,
            active_segment_id=chapter.segments[0].id,
            error=None,
        )
        self._save_active_position()

    def select_segment(self, segment_id: str) -> None:
        if self._book is None:
            return
        chapter = self._chapter_for_segment(self._book, segment_id)
        if not any(segment.id == segment_id for segment in chapter.segments):
            return
        if self._state.active_segment_id == segment_id:
            return
        self._playback.stop()
        segment_items, figure_items = self._chapter_content(chapter)
        self._set_state(
            active_chapter_id=chapter.id,
            segments=segment_items,
            figures=figure_items,
            active_segment_id=segment_id,
            error=None,
        )
        self._save_active_position()

    def set_voice(self, voice_id: str) -> None:
        if not voice_id or voice_id == self._state.voice_id:
            return
        if (
            self._book is not None
            or self._state.playback_state is not PlaybackState.IDLE
        ):
            self._playback.stop()
        self._set_state(voice_id=voice_id)
        self._save_active_preferences()

    def reconcile_voice(self, available_voice_ids) -> None:
        """Keep the voice on screen and the voice actually read the same one.

        A voice remembered from an earlier run - or carried in a book's saved
        position - can be missing from the model now. The dropdown would fall
        back to its first entry while synthesis was still asked for the one
        that is gone, so the person would see one voice and hear an error.

        The stored preference is deliberately left alone: if the voice comes
        back, so does their choice.
        """

        available = tuple(available_voice_ids)
        if not available or self._state.voice_id in available:
            return
        self._set_state(
            voice_id=DEFAULT_VOICE_ID if DEFAULT_VOICE_ID in available else available[0]
        )

    def set_rate(self, rate: float) -> None:
        if not 0.5 <= rate <= 2.0:
            raise ValueError("playback rate must be between 0.5 and 2.0")
        self._playback.set_rate(rate)
        self._set_state(rate=rate)
        self._save_active_preferences()

    def _save_active_position(self) -> bool:
        if self._book is None or self._state.active_segment_id is None:
            return True
        try:
            self._playback.save_position(
                self._book,
                self._state.active_segment_id,
                self._state.voice_id,
                rate=self._state.rate,
            )
            return True
        except Exception:
            self._set_state(
                error="Không thể lưu vị trí đọc. Sách vẫn có thể mở lại.",
                status="Không thể lưu vị trí đọc.",
            )
            return False

    def _save_active_preferences(self) -> bool:
        if self._voice_store is not None:
            # Reading text from another app has no book to remember the choice,
            # so without this the voice picked there dies with the session.
            self._voice_store.save(self._state.voice_id, self._state.rate)
        if self._book is None or self._state.active_segment_id is None:
            return True
        try:
            self._playback.save_preferences(
                self._book,
                self._state.active_segment_id,
                self._state.voice_id,
                rate=self._state.rate,
            )
            return True
        except Exception:
            self._set_state(
                error="Không thể lưu tùy chọn đọc. Sách vẫn có thể mở lại.",
                status="Không thể lưu tùy chọn đọc.",
            )
            return False

    def play_current(self) -> None:
        if self._book is None or self._state.active_segment_id is None:
            self._set_state(error="Hãy mở một cuốn sách trước khi bấm đọc.")
            return
        self._playback.play(
            self._book,
            self._state.active_segment_id,
            self._state.voice_id,
            rate=self._state.rate,
            settings=self._settings,
            speech_text_by_segment=self._speech_text_by_segment,
        )

    def read_selection(self, text: str) -> None:
        self._read_text(
            text,
            empty_error="Hãy chọn một phần nội dung để đọc.",
            source="book_selection",
        )

    def read_pasted_text(self, text: str) -> None:
        try:
            prepared = prepare_pasted_text(text)
        except ValueError:
            self._set_state(
                error="Nội dung dán vượt quá giới hạn 100.000 ký tự."
            )
            return
        self._read_text(
            prepared,
            empty_error="Hãy dán nội dung trước khi bấm đọc.",
            source="paste",
        )

    def read_external_selection(self, text: str) -> None:
        self._set_state(error=None)
        try:
            prepared = prepare_pasted_text(text)
        except ValueError:
            self._set_state(
                error="Phần đã chọn vượt quá giới hạn 100.000 ký tự.",
                status="Không thể đọc phần đã chọn.",
                external_reading_state=ExternalReadingState.FAILED,
            )
            return
        self._read_text(
            prepared,
            empty_error="Không tìm thấy nội dung đang chọn trong Apple Books.",
            source="apple_books",
        )

    def external_selection_failed(self, reason: str) -> None:
        messages = {
            "permission_required": (
                "ReadEase cần quyền Trợ năng để gửi lệnh sao chép tới Apple "
                "Books. Hãy bật ReadEase trong Cài đặt hệ thống > Quyền riêng "
                "tư & Bảo mật > Trợ năng rồi thử lại."
            ),
            "no_selection": (
                "Không tìm thấy nội dung đang chọn. Hãy chọn chữ trong Apple "
                "Books rồi nhấn phím tắt đọc."
            ),
            "unsupported_source": (
                "Phím tắt đọc nhanh hiện chỉ hỗ trợ Apple Books."
            ),
            "shortcut_unavailable": (
                "Không đăng ký được phím tắt này; macOS hoặc ứng dụng khác "
                "đang dùng nó. Hãy chọn tổ hợp khác."
            ),
            "clipboard_restore_failed": (
                "ReadEase không thể xác nhận đã khôi phục clipboard nên đã "
                "dừng trước khi đọc."
            ),
            "unavailable": (
                "Phím tắt đọc từ Apple Books chưa sẵn sàng. Hãy mở lại ReadEase."
            ),
        }
        if reason == "ready":
            changes = {
                "external_reading_state": ExternalReadingState.READY,
                "can_open_accessibility_settings": False,
            }
            # The helper is registered again, so an earlier "this shortcut is
            # taken" banner would now be a lie. Anything the failure did not
            # write is left exactly as it was.
            if self._status_before_external_failure is not None:
                changes["error"] = None
                changes["status"] = self._status_before_external_failure
                self._status_before_external_failure = None
            self._set_state(**changes)
            return
        external_state = (
            ExternalReadingState.PERMISSION_REQUIRED
            if reason == "permission_required"
            else ExternalReadingState.FAILED
        )
        if self._status_before_external_failure is None:
            self._status_before_external_failure = self._state.status
        self._set_state(
            error=messages.get(reason, messages["unavailable"]),
            status="Không thể đọc phần đã chọn.",
            external_reading_state=external_state,
            can_open_accessibility_settings=reason == "permission_required",
        )

    def _read_text(
        self,
        text: str,
        *,
        empty_error: str,
        source: str,
        remember: bool = True,
    ) -> bool:
        try:
            prepared = prepare_pasted_text(text)
        except ValueError:
            changes = {
                "error": "Phần nội dung đã chọn vượt quá 100.000 ký tự."
            }
            if source == "apple_books":
                changes["external_reading_state"] = ExternalReadingState.FAILED
            self._set_state(**changes)
            return False
        if not prepared:
            changes = {"error": empty_error}
            if source == "apple_books":
                changes["external_reading_state"] = ExternalReadingState.FAILED
            self._set_state(**changes)
            return False
        self._playback.play_selection(
            prepared,
            self._state.voice_id,
            rate=self._state.rate,
            settings=self._settings,
        )
        if remember:
            self._remember_session_reading(prepared, source)
        if source == "apple_books":
            self._set_state(
                error=None,
                external_reading_state=ExternalReadingState.RECEIVED,
                can_open_accessibility_settings=False,
            )
        return True

    def _remember_session_reading(self, text: str, source: str) -> None:
        source_label = self._SESSION_SOURCE_LABELS[source]
        existing = next(
            (entry for entry in self._session_history_entries if entry.text == text),
            None,
        )
        if existing is None:
            item_id = f"session-reading-{self._next_session_reading_id}"
            self._next_session_reading_id += 1
        else:
            item_id = existing.item.id
        compact = " ".join(text.split())
        preview = compact
        if len(preview) > self._SESSION_PREVIEW_LIMIT:
            preview = preview[: self._SESSION_PREVIEW_LIMIT - 1].rstrip() + "…"
        stored = _StoredSessionReading(
            item=SessionReadingItem(
                id=item_id,
                source=source,
                source_label=source_label,
                preview=preview,
            ),
            text=text,
        )
        entries = [
            entry for entry in self._session_history_entries if entry.text != text
        ]
        self._session_history_entries = [stored, *entries][
            : self._SESSION_HISTORY_LIMIT
        ]
        self._set_state(
            session_history=tuple(
                entry.item for entry in self._session_history_entries
            )
        )

    def replay_session_reading(self, item_id: str) -> None:
        entry = next(
            (
                entry
                for entry in self._session_history_entries
                if entry.item.id == item_id
            ),
            None,
        )
        if entry is None:
            self._set_state(error="Nội dung này không còn trong lịch sử phiên.")
            return
        self._read_text(
            entry.text,
            empty_error="Nội dung này không còn trong lịch sử phiên.",
            source=entry.item.source,
            remember=False,
        )

    def clear_session_history(self) -> None:
        if not self._session_history_entries:
            return
        self._session_history_entries = []
        self._set_state(session_history=())

    def _dispatch_playback(self, snapshot: PlaybackSnapshot) -> None:
        self._dispatch(lambda snapshot=snapshot: self._on_playback(snapshot))

    def _on_playback(self, snapshot: PlaybackSnapshot) -> None:
        order = (snapshot.generation, snapshot.sequence)
        if order < self._last_playback_order:
            return
        if (
            self._book is not None
            and snapshot.book_id is not None
            and snapshot.book_id != self._book.id
        ):
            return
        self._last_playback_order = order
        status = {
            PlaybackState.IDLE: "Sẵn sàng đọc.",
            PlaybackState.LOADING: "Đang chuẩn bị giọng đọc…",
            PlaybackState.PLAYING: "Đang đọc",
            PlaybackState.PAUSED: "Đã tạm dừng",
            PlaybackState.ERROR: snapshot.error or "Không thể tiếp tục đọc.",
        }[snapshot.state]
        if (
            snapshot.is_selection
            and snapshot.selection_part_index is not None
            and snapshot.selection_part_count > 1
        ):
            part = (
                f"đoạn {snapshot.selection_part_index}/"
                f"{snapshot.selection_part_count}"
            )
            status = {
                PlaybackState.LOADING: f"Đang chuẩn bị {part}…",
                PlaybackState.PLAYING: f"Đang đọc {part}",
                PlaybackState.PAUSED: f"Đã tạm dừng · {part.capitalize()}",
                PlaybackState.ERROR: snapshot.error or "Không thể tiếp tục đọc.",
                PlaybackState.IDLE: "Sẵn sàng đọc.",
            }[snapshot.state]
        changes = {
            "playback_state": snapshot.state,
            "is_selection_playback": snapshot.is_selection,
            "rate": snapshot.rate,
            "status": status,
            "error": snapshot.error,
        }
        if (
            snapshot.state
            in {PlaybackState.LOADING, PlaybackState.PLAYING, PlaybackState.PAUSED}
            and not snapshot.is_selection
            and self._book is not None
            and snapshot.book_id == self._book.id
            and snapshot.segment_id is not None
        ):
            chapter = self._chapter_for_segment(self._book, snapshot.segment_id)
            segment_items, figure_items = self._chapter_content(chapter)
            changes.update(
                active_chapter_id=chapter.id,
                segments=segment_items,
                figures=figure_items,
                active_segment_id=snapshot.segment_id,
            )
        self._set_state(**changes)

    def previous(self) -> None:
        self._playback.previous()

    def next(self) -> None:
        self._playback.next()

    def pause(self) -> None:
        self._playback.pause()

    def resume(self) -> None:
        self._playback.resume()

    def stop(self) -> None:
        self._playback.stop()
