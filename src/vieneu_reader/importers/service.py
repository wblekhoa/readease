"""Atomic managed-library import orchestration."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
from threading import RLock
from typing import BinaryIO, Callable, Mapping

from vieneu_reader.config import AppPaths
from vieneu_reader.domain.models import BookDocument, stable_id
from vieneu_reader.domain.presentation import BookPresentation, FigureRef
from vieneu_reader.storage.errors import RepositoryError
from vieneu_reader.storage.repository import LibraryRepository

from .epub import import_epub
from .epub_presentation import load_epub_assets, load_epub_presentation
from .errors import CorruptBookError, LibraryStorageError, UnsupportedBookError
from .pdf import import_pdf


BookParser = Callable[[Path], BookDocument]
MAX_MANAGED_SOURCE_BYTES = 200 * 1024 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024
_IMPORT_TEMP_NAME = re.compile(r"^\.import-[a-z0-9_]{8}(\.[a-z0-9]+)$")


def _copy_bounded(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    max_bytes: int,
) -> int:
    copied = 0
    while chunk := source.read(_COPY_CHUNK_BYTES):
        copied += len(chunk)
        if copied > max_bytes:
            raise CorruptBookError("Tệp sách vượt giới hạn dung lượng 200 MiB.")
        destination.write(chunk)
    return copied


@dataclass(frozen=True, slots=True)
class ImportResult:
    book: BookDocument
    managed_path: Path
    was_existing: bool


class LibraryService:
    _process_import_lock = RLock()

    def __init__(
        self,
        paths: AppPaths,
        repository: LibraryRepository,
        parsers: Mapping[str, BookParser] | None = None,
    ):
        self._paths = paths
        self._repository = repository
        self._parsers = {
            suffix.lower(): parser
            for suffix, parser in (
                parsers or {".epub": import_epub, ".pdf": import_pdf}
            ).items()
        }
        self._import_lock = RLock()
        self._presentation_cache: dict[str, BookPresentation] = {}

    def presentation_for(
        self,
        book: BookDocument,
        managed_path: Path,
    ) -> BookPresentation:
        """Return a verified session-only EPUB overlay, or a safe empty one."""

        if book.source_format != "epub":
            return BookPresentation.empty(book.id, book.source_hash)
        cached = self._presentation_cache.get(book.id)
        if cached is not None and cached.source_hash == book.source_hash:
            return cached
        try:
            presentation = load_epub_presentation(Path(managed_path), book)
        except (CorruptBookError, OSError):
            return BookPresentation.empty(book.id, book.source_hash)
        self._presentation_cache[book.id] = presentation
        return presentation

    def assets_for(
        self,
        book: BookDocument,
        managed_path: Path,
        figures: tuple[FigureRef, ...],
    ) -> dict[str, bytes]:
        """Load only the current chapter's figure bytes; text remains usable on error."""

        if book.source_format != "epub" or not figures:
            return {}
        try:
            return load_epub_assets(
                Path(managed_path),
                tuple(figure.asset_path for figure in figures),
                expected_hash=book.source_hash,
            )
        except (CorruptBookError, OSError):
            return {}

    def import_book(self, source: Path) -> ImportResult:
        with self._import_lock:
            try:
                with self._import_guard():
                    return self._import_book_locked(source)
            except OSError as error:
                raise LibraryStorageError(
                    "Không thể khóa thư viện cục bộ để nhập sách."
                ) from error

    def _remove_owned_managed_copy(
        self,
        book: BookDocument,
        managed_path: Path,
        identity: tuple[int, int] | None,
    ) -> None:
        if identity is None:
            return
        try:
            current = managed_path.stat()
        except OSError:
            return
        if (current.st_dev, current.st_ino) != identity:
            return
        try:
            stored = self._repository.get_book(book.id)
        except Exception:
            return
        if stored is not None and stored.managed_path == managed_path:
            return
        try:
            managed_path.unlink()
        except OSError:
            return

    @contextmanager
    def _import_guard(self):
        lock_path = self._paths.root / ".import.lock"
        with self._process_import_lock:
            flags = os.O_CREAT | os.O_RDWR
            flags |= getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(lock_path, flags, 0o600)
            try:
                os.fchmod(descriptor, 0o600)
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            except BaseException:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
            try:
                yield
            except BaseException as primary_error:
                close_error = self._close_import_lock(descriptor)
                if close_error is not None:
                    primary_error.add_note(
                        "Không thể đóng tệp khóa import sau lỗi chính."
                    )
                raise
            else:
                # The body may already have committed both the row and file.
                # Closing is the release operation; a close report cannot make
                # that committed result safe to present as a failed import.
                self._close_import_lock(descriptor)

    @staticmethod
    def _close_import_lock(descriptor: int) -> OSError | None:
        try:
            os.close(descriptor)
        except OSError as error:
            return error
        return None

    def _scavenge_import_scratch(self) -> None:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        flags |= getattr(os, "O_CLOEXEC", 0)
        try:
            books_descriptor = os.open(self._paths.books, flags)
            try:
                with os.scandir(books_descriptor) as entries:
                    for entry in entries:
                        match = _IMPORT_TEMP_NAME.fullmatch(entry.name)
                        if match is None or match.group(1).lower() not in self._parsers:
                            continue
                        metadata = entry.stat(follow_symlinks=False)
                        if (
                            not stat.S_ISREG(metadata.st_mode)
                            or metadata.st_uid != os.getuid()
                        ):
                            continue
                        try:
                            os.unlink(entry.name, dir_fd=books_descriptor)
                        except FileNotFoundError:
                            continue
            finally:
                os.close(books_descriptor)
        except OSError as error:
            raise LibraryStorageError(
                "Không thể dọn dẹp bản sao nhập tạm trong thư viện."
            ) from error

    @staticmethod
    def _try_remove_temporary_copy(temporary_path: Path) -> OSError | None:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            return None
        except OSError as error:
            return error
        return None

    def _finalize_book(
        self,
        book: BookDocument,
        temporary_path: Path,
        suffix: str,
    ) -> ImportResult:
        existing = self._repository.get_book(book.id)
        if existing is not None:
            return ImportResult(existing.book, existing.managed_path, True)

        managed_path = self._paths.books / f"{book.id}{suffix}"
        orphan_hash = self._owned_regular_file_hash(managed_path)
        if orphan_hash is not None:
            expected_id = stable_id(book.source_hash, book.source_format)
            if (
                orphan_hash != book.source_hash
                or book.id != expected_id
                or suffix != f".{book.source_format}"
            ):
                raise CorruptBookError(
                    "Thư viện có bản sao chưa hoàn tất; cần sửa thư viện trước khi nhập lại."
                )
            self._repository.add_book(book, managed_path)
            return ImportResult(book, managed_path, False)
        moved_to_library = False
        managed_identity: tuple[int, int] | None = None
        try:
            temporary_stat = temporary_path.stat()
            managed_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
            temporary_path.replace(managed_path)
            moved_to_library = True
            self._repository.add_book(book, managed_path)
            return ImportResult(book, managed_path, False)
        except Exception:
            if moved_to_library:
                self._remove_owned_managed_copy(
                    book,
                    managed_path,
                    managed_identity,
                )
            raise

    @staticmethod
    def _owned_regular_file_hash(path: Path) -> str | None:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            return None
        except OSError as error:
            raise CorruptBookError(
                "Thư viện có bản sao chưa hoàn tất; cần sửa thư viện trước khi nhập lại."
            ) from error
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or metadata.st_size > MAX_MANAGED_SOURCE_BYTES
            ):
                raise CorruptBookError(
                    "Thư viện có bản sao chưa hoàn tất; cần sửa thư viện trước khi nhập lại."
                )
            digest = sha256()
            while chunk := os.read(descriptor, _COPY_CHUNK_BYTES):
                digest.update(chunk)
            return digest.hexdigest()
        finally:
            os.close(descriptor)

    def _import_book_locked(self, source: Path) -> ImportResult:
        source_path = Path(source)
        suffix = source_path.suffix.lower()
        parser = self._parsers.get(suffix)
        if parser is None:
            raise UnsupportedBookError("Vui lòng chọn tệp PDF hoặc EPUB.")
        if not source_path.is_file():
            raise CorruptBookError("Không tìm thấy tệp sách đã chọn.")
        try:
            source_size = source_path.stat().st_size
        except OSError as error:
            raise CorruptBookError("Không thể kiểm tra tệp sách đã chọn.") from error
        if source_size > MAX_MANAGED_SOURCE_BYTES:
            raise CorruptBookError("Tệp sách vượt giới hạn dung lượng 200 MiB.")

        self._scavenge_import_scratch()

        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".import-",
                suffix=suffix,
                dir=self._paths.books,
            )
        except OSError as error:
            raise CorruptBookError("Không thể chuẩn bị thư viện để sao chép sách.") from error
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            try:
                with (
                    source_path.open("rb") as source_file,
                    temporary_path.open("wb") as target,
                ):
                    _copy_bounded(
                        source_file,
                        target,
                        max_bytes=MAX_MANAGED_SOURCE_BYTES,
                    )
                    target.flush()
                    os.fsync(target.fileno())
                book = parser(temporary_path)
                if book.title == temporary_path.stem:
                    book = replace(book, title=source_path.stem)
                result = self._finalize_book(book, temporary_path, suffix)
            except (RepositoryError, sqlite3.Error) as error:
                raise LibraryStorageError(
                    "Không thể cập nhật thư viện cục bộ; sách chưa được thêm."
                ) from error
            except OSError as error:
                raise CorruptBookError(
                    "Không thể sao chép sách vào thư viện cục bộ."
                ) from error
        except BaseException as primary_error:
            cleanup_error = self._try_remove_temporary_copy(temporary_path)
            if cleanup_error is not None:
                primary_error.add_note(
                    "Không thể dọn dẹp bản sao nhập tạm; lần nhập sau sẽ thử lại."
                )
            raise
        else:
            cleanup_error = self._try_remove_temporary_copy(temporary_path)
            if cleanup_error is not None:
                raise LibraryStorageError(
                    "Không thể dọn dẹp bản sao nhập tạm; lần nhập sau sẽ thử lại."
                ) from cleanup_error
            return result
