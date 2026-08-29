"""SQLite owner for normalized books and resumable reading progress."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any

from vieneu_reader.domain.models import BookDocument, Chapter, Segment, stable_id
from vieneu_reader.domain.prosody import ends_sentence

from .errors import RepositoryCorruptionError, RepositoryError


SCHEMA_VERSION = 1


@contextmanager
def _database_errors():
    """Translate SQLite failures only after transaction contexts have exited."""

    try:
        yield
    except sqlite3.Error as error:
        raise RepositoryError(
            "Không thể truy cập dữ liệu thư viện cục bộ."
        ) from error


@dataclass(frozen=True, slots=True)
class StoredBook:
    book: BookDocument
    managed_path: Path


@dataclass(frozen=True, slots=True)
class Progress:
    book_id: str
    segment_id: str
    playback_rate: float
    voice_id: str


def _document_payload(book: BookDocument) -> str:
    data = {
        "id": book.id,
        "title": book.title,
        "source_format": book.source_format,
        "source_hash": book.source_hash,
        "chapters": [
            {
                "id": chapter.id,
                "title": chapter.title,
                "ordinal": chapter.ordinal,
                "segments": [
                    {
                        "id": segment.id,
                        "chapter_id": segment.chapter_id,
                        "ordinal": segment.ordinal,
                        "text": segment.text,
                        "kind": segment.kind,
                        "joint": segment.joint,
                    }
                    for segment in chapter.segments
                ],
            }
            for chapter in book.chapters
        ],
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_SEGMENT_KINDS = frozenset(
    {"paragraph", "heading", "list_item", "quote", "caption", "preformatted"}
)
_SEGMENT_JOINTS = frozenset({"block", "line", "split"})


def _segment_kind(raw_segment: Any) -> str:
    kind = raw_segment.get("kind", "paragraph")
    if kind not in _SEGMENT_KINDS:
        raise ValueError("segment kind is invalid")
    return kind


def _segment_joint(raw_segment: Any, previous_text: str | None) -> str:
    joint = raw_segment.get("joint")
    if joint is None:
        # Books stored before segments carried structure: a previous segment
        # that never closed its sentence means this one continues the same
        # source block, and a paragraph-sized pause there would land in the
        # middle of a sentence.
        if previous_text is None or ends_sentence(previous_text):
            return "block"
        return "split"
    if joint not in _SEGMENT_JOINTS:
        raise ValueError("segment joint is invalid")
    return joint


def _required_text(container: Any, key: str) -> str:
    value = container[key]
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{key} must be a non-empty text value")
    return value


def _required_ordinal(container: Any) -> int:
    value = container["ordinal"]
    if type(value) is not int or value < 0:
        raise ValueError("ordinal must be a non-negative integer")
    return value


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _document_from_payload(payload: str) -> BookDocument:
    try:
        data: dict[str, Any] = json.loads(payload)
        book_id = _required_text(data, "id")
        title = _required_text(data, "title")
        source_format = _required_text(data, "source_format")
        source_hash = _required_text(data, "source_hash")
        if source_format not in {"epub", "pdf"} or not _is_sha256(source_hash):
            raise ValueError("book source identity is invalid")
        if book_id != stable_id(source_hash, source_format):
            raise ValueError("book id does not match its source identity")

        raw_chapters = data["chapters"]
        if not isinstance(raw_chapters, list) or not raw_chapters:
            raise ValueError("book must contain chapters")
        chapters: list[Chapter] = []
        for chapter_index, raw_chapter in enumerate(raw_chapters):
            chapter_id = _required_text(raw_chapter, "id")
            chapter_title = _required_text(raw_chapter, "title")
            chapter_ordinal = _required_ordinal(raw_chapter)
            if (
                chapter_ordinal != chapter_index
                or chapter_id != stable_id(book_id, "chapter", str(chapter_index))
            ):
                raise ValueError("chapter identity or order is invalid")
            raw_segments = raw_chapter["segments"]
            if not isinstance(raw_segments, list) or not raw_segments:
                raise ValueError("chapter must contain segments")
            segments: list[Segment] = []
            for segment_index, raw_segment in enumerate(raw_segments):
                segment_id = _required_text(raw_segment, "id")
                segment_chapter_id = _required_text(raw_segment, "chapter_id")
                segment_text = _required_text(raw_segment, "text")
                segment_ordinal = _required_ordinal(raw_segment)
                if (
                    segment_ordinal != segment_index
                    or segment_chapter_id != chapter_id
                    or segment_id
                    != stable_id(chapter_id, "segment", str(segment_index))
                ):
                    raise ValueError("segment identity or order is invalid")
                segments.append(
                    Segment(
                        id=segment_id,
                        chapter_id=segment_chapter_id,
                        ordinal=segment_ordinal,
                        text=segment_text,
                        kind=_segment_kind(raw_segment),
                        joint=_segment_joint(
                            raw_segment,
                            segments[-1].text if segments else None,
                        ),
                    )
                )
            chapters.append(
                Chapter(
                    id=chapter_id,
                    title=chapter_title,
                    ordinal=chapter_ordinal,
                    segments=tuple(segments),
                )
            )
        return BookDocument(
            id=book_id,
            title=title,
            source_format=source_format,
            source_hash=source_hash,
            chapters=tuple(chapters),
        )
    except (KeyError, OverflowError, TypeError, ValueError) as error:
        raise RepositoryCorruptionError(
            "Dữ liệu sách trong thư viện cục bộ bị hỏng."
        ) from error


def _stored_book_from_row(row: sqlite3.Row) -> StoredBook:
    book = _document_from_payload(row["document_json"])
    try:
        row_id = _required_text(row, "id")
        row_title = _required_text(row, "title")
        row_source_format = _required_text(row, "source_format")
        row_source_hash = _required_text(row, "source_hash")
        managed_value = _required_text(row, "managed_path")
        managed_path = Path(managed_value)
        if not managed_path.is_absolute():
            raise ValueError("managed path must be absolute")
        if (
            book.id != row_id
            or book.title != row_title
            or book.source_format != row_source_format
            or book.source_hash != row_source_hash
        ):
            raise ValueError("book row identity does not match its document")
        return StoredBook(book=book, managed_path=managed_path)
    except (TypeError, ValueError) as error:
        raise RepositoryCorruptionError(
            "Dữ liệu sách trong thư viện cục bộ bị hỏng."
        ) from error


class LibraryRepository:
    def __init__(self, database: Path):
        self._database = Path(database)
        self._database.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._closed = False
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self._database, check_same_thread=False)
            self._connection = connection
            self._connection.row_factory = sqlite3.Row
            self._assert_existing_schema_compatible()
            self._configure()
            self._create_schema()
            self._database.chmod(0o600)
        except sqlite3.Error as error:
            if connection is not None:
                try:
                    connection.close()
                except sqlite3.Error:
                    pass
            self._closed = True
            raise RepositoryError(
                "Không thể mở dữ liệu thư viện cục bộ."
            ) from error
        except Exception:
            if connection is not None:
                connection.close()
            self._closed = True
            raise

    def _assert_existing_schema_compatible(self) -> None:
        tables = {
            row["name"]
            for row in self._connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }
        if not tables:
            return
        if "app_meta" not in tables:
            raise RuntimeError("Unsupported ReadEase database schema")
        try:
            row = self._connection.execute(
                "SELECT value FROM app_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                raise RuntimeError("Unsupported ReadEase database schema")
            version = int(row["value"])
        except RuntimeError:
            raise
        except (KeyError, TypeError, ValueError, sqlite3.Error) as error:
            raise RuntimeError("Unsupported ReadEase database schema") from error
        if version != SCHEMA_VERSION:
            raise RuntimeError("Unsupported ReadEase database schema")

    def _configure(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            row = self._connection.execute(
                "SELECT value FROM app_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is not None and int(row["value"]) != SCHEMA_VERSION:
                raise RuntimeError("Unsupported ReadEase database schema")

            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_format TEXT NOT NULL,
                    source_hash TEXT NOT NULL UNIQUE,
                    managed_path TEXT NOT NULL UNIQUE,
                    document_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS progress (
                    book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
                    segment_id TEXT NOT NULL,
                    playback_rate REAL NOT NULL,
                    voice_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            if row is None:
                self._connection.execute(
                    "INSERT INTO app_meta(key, value) VALUES('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )

    def schema_version(self) -> int:
        with _database_errors():
            with self._lock:
                row = self._connection.execute(
                    "SELECT value FROM app_meta WHERE key = 'schema_version'"
                ).fetchone()
            return int(row["value"])

    def count_books(self) -> int:
        with _database_errors():
            with self._lock:
                row = self._connection.execute(
                    "SELECT COUNT(*) AS count FROM books"
                ).fetchone()
            return int(row["count"])

    def add_book(self, book: BookDocument, managed_path: Path) -> None:
        with _database_errors(), self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO books(
                    id, title, source_format, source_hash, managed_path, document_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    book.id,
                    book.title,
                    book.source_format,
                    book.source_hash,
                    str(managed_path),
                    _document_payload(book),
                ),
            )

    def get_book(self, book_id: str) -> StoredBook | None:
        with _database_errors():
            with self._lock:
                row = self._connection.execute(
                    "SELECT id, title, source_format, source_hash, "
                    "document_json, managed_path FROM books WHERE id = ?",
                    (book_id,),
                ).fetchone()
            if row is None:
                return None
            return _stored_book_from_row(row)

    def list_books(self) -> tuple[StoredBook, ...]:
        with _database_errors():
            with self._lock:
                rows = self._connection.execute(
                    "SELECT id, title, source_format, source_hash, "
                    "document_json, managed_path FROM books "
                    "ORDER BY created_at DESC, id"
                ).fetchall()
            return tuple(_stored_book_from_row(row) for row in rows)

    def save_active_book_id(self, book_id: str) -> None:
        if not _is_sha256(book_id):
            raise RepositoryError("Không thể lưu cuốn sách đang mở.")
        with _database_errors(), self._lock, self._connection:
            row = self._connection.execute(
                "SELECT 1 FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if row is None:
                raise RepositoryError("Không thể lưu cuốn sách đang mở.")
            self._connection.execute(
                """
                INSERT INTO app_meta(key, value) VALUES('active_book_id', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (book_id,),
            )

    def load_active_book_id(self) -> str | None:
        with _database_errors(), self._lock:
            row = self._connection.execute(
                "SELECT value FROM app_meta WHERE key = 'active_book_id'"
            ).fetchone()
            if row is None:
                return None
            try:
                book_id = _required_text(row, "value")
            except (KeyError, TypeError, ValueError) as error:
                raise RepositoryCorruptionError(
                    "Dữ liệu cuốn sách đang mở trong thư viện cục bộ bị hỏng."
                ) from error
            if not _is_sha256(book_id):
                raise RepositoryCorruptionError(
                    "Dữ liệu cuốn sách đang mở trong thư viện cục bộ bị hỏng."
                )
            exists = self._connection.execute(
                "SELECT 1 FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if exists is None:
                raise RepositoryCorruptionError(
                    "Dữ liệu cuốn sách đang mở trong thư viện cục bộ bị hỏng."
                )
            return book_id

    def save_progress(self, progress: Progress) -> None:
        with _database_errors(), self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO progress(book_id, segment_id, playback_rate, voice_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(book_id) DO UPDATE SET
                    segment_id = excluded.segment_id,
                    playback_rate = excluded.playback_rate,
                    voice_id = excluded.voice_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    progress.book_id,
                    progress.segment_id,
                    progress.playback_rate,
                    progress.voice_id,
                ),
            )

    def save_preferences(self, preferences: Progress) -> None:
        """Update voice/rate without moving a newer persisted segment backward."""

        with _database_errors(), self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO progress(book_id, segment_id, playback_rate, voice_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(book_id) DO UPDATE SET
                    playback_rate = excluded.playback_rate,
                    voice_id = excluded.voice_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    preferences.book_id,
                    preferences.segment_id,
                    preferences.playback_rate,
                    preferences.voice_id,
                ),
            )

    def load_progress(self, book_id: str) -> Progress | None:
        with _database_errors():
            with self._lock:
                row = self._connection.execute(
                    """
                    SELECT book_id, segment_id, playback_rate, voice_id
                    FROM progress WHERE book_id = ?
                    """,
                    (book_id,),
                ).fetchone()
            if row is None:
                return None
            try:
                stored_book_id = _required_text(row, "book_id")
                segment_id = _required_text(row, "segment_id")
                voice_id = _required_text(row, "voice_id")
                playback_rate = float(row["playback_rate"])
                if (
                    stored_book_id != book_id
                    or not _is_sha256(segment_id)
                    or not 0.5 <= playback_rate <= 2.0
                ):
                    raise ValueError("stored progress identity or rate is invalid")
                return Progress(
                    book_id=stored_book_id,
                    segment_id=segment_id,
                    playback_rate=playback_rate,
                    voice_id=voice_id,
                )
            except (KeyError, TypeError, ValueError) as error:
                raise RepositoryCorruptionError(
                    "Dữ liệu tiến độ đọc trong thư viện cục bộ bị hỏng."
                ) from error

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True
