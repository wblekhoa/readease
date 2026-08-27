from dataclasses import replace
import fcntl
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import sqlite3
import stat
from tempfile import TemporaryDirectory
from threading import Event, Lock, Thread
import unittest
from unittest.mock import patch

from vieneu_reader.config import AppPaths
from vieneu_reader.domain.models import stable_id
from vieneu_reader.importers.errors import (
    CorruptBookError,
    LibraryStorageError,
    UnsupportedBookError,
)
from vieneu_reader.importers.service import LibraryService, _copy_bounded
from vieneu_reader.storage.repository import LibraryRepository

from tests.domain.book_fixture import sample_book
from tests.importers.epub_fixture import make_epub, make_png
from tests.importers.pdf_fixture import make_pdf


def _make_pdf(path: Path) -> Path:
    return make_pdf(
        path,
        pages=(((50, 720, "Noi dung PDF co lop van ban de doc thanh tieng."),),),
    )


def _sample_book_for_payload(seed: str, payload: bytes):
    source_hash = sha256(payload).hexdigest()
    book_id = stable_id(source_hash, "epub")
    base = sample_book(seed)
    chapters = []
    for chapter_index, chapter in enumerate(base.chapters):
        chapter_id = stable_id(book_id, "chapter", str(chapter_index))
        segments = tuple(
            replace(
                segment,
                id=stable_id(chapter_id, "segment", str(segment_index)),
                chapter_id=chapter_id,
                ordinal=segment_index,
            )
            for segment_index, segment in enumerate(chapter.segments)
        )
        chapters.append(
            replace(
                chapter,
                id=chapter_id,
                ordinal=chapter_index,
                segments=segments,
            )
        )
    return replace(
        base,
        id=book_id,
        source_hash=source_hash,
        chapters=tuple(chapters),
    )


class LibraryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.paths = AppPaths.create(root / "app-data")
        self.repository = LibraryRepository(self.paths.database)
        self.service = LibraryService(self.paths, self.repository)
        self.sources = root / "sources"
        self.sources.mkdir()

    def tearDown(self):
        self.repository.close()
        self.temp_dir.cleanup()

    def test_import_copies_source_into_managed_library(self):
        source = make_epub(self.sources)

        result = self.service.import_book(source)

        self.assertFalse(result.was_existing)
        self.assertTrue(source.is_file())
        self.assertTrue(result.managed_path.is_file())
        self.assertEqual(result.managed_path.parent, self.paths.books)
        self.assertEqual(result.managed_path.name, f"{result.book.id}.epub")
        self.assertEqual(self.repository.count_books(), 1)

    def test_import_pdf_uses_the_same_managed_library_pipeline(self):
        source = _make_pdf(self.sources / "sach.pdf")

        result = self.service.import_book(source)

        self.assertFalse(result.was_existing)
        self.assertEqual(result.book.source_format, "pdf")
        self.assertEqual(result.book.title, "sach")
        self.assertEqual(result.managed_path.suffix, ".pdf")
        self.assertTrue(result.managed_path.is_file())
        self.assertEqual(self.repository.count_books(), 1)

    def test_pdf_presentation_is_empty_without_reading_the_pdf_as_an_archive(self):
        result = self.service.import_book(_make_pdf(self.sources / "sach.pdf"))

        presentation = self.service.presentation_for(
            result.book,
            result.managed_path,
        )

        self.assertEqual(presentation.book_id, result.book.id)
        self.assertEqual(presentation.chapters, ())

    def test_epub_presentation_and_assets_use_the_managed_copy(self):
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1><p>Nội dung.</p>
        <img src="images/diagram.png" alt="Sơ đồ"/>
        </body></html>"""
        payload = make_png(320, 200)
        result = self.service.import_book(
            make_epub(
                self.sources,
                spine=("chapter-1",),
                chapter_overrides={"chapter-1": chapter},
                image_entries={"images/diagram.png": (payload, "image/png")},
            )
        )

        presentation = self.service.presentation_for(
            result.book,
            result.managed_path,
        )
        figure = presentation.chapters[0].figures[0]
        assets = self.service.assets_for(
            result.book,
            result.managed_path,
            (figure,),
        )

        self.assertEqual(assets, {figure.asset_path: payload})
        self.assertFalse((self.paths.books / "diagram.png").exists())

    def test_changed_managed_epub_fails_closed_to_text_only_presentation(self):
        result = self.service.import_book(make_epub(self.sources))
        result.managed_path.write_bytes(b"changed after import")

        presentation = self.service.presentation_for(
            result.book,
            result.managed_path,
        )

        self.assertEqual(presentation.chapters, ())

    def test_duplicate_import_focuses_existing_managed_book(self):
        source = make_epub(self.sources)

        first = self.service.import_book(source)
        second = self.service.import_book(source)

        self.assertTrue(second.was_existing)
        self.assertEqual(second.book, first.book)
        self.assertEqual(second.managed_path, first.managed_path)
        self.assertEqual(self.repository.count_books(), 1)
        self.assertEqual(list(self.paths.books.glob("*.epub")), [first.managed_path])

    def test_corrupt_import_leaves_source_and_library_unchanged(self):
        source = self.sources / "broken.epub"
        source.write_bytes(b"not an epub")

        with self.assertRaises(CorruptBookError):
            self.service.import_book(source)

        self.assertTrue(source.is_file())
        self.assertEqual(self.repository.count_books(), 0)
        self.assertEqual(list(self.paths.books.iterdir()), [])

    def test_unsupported_extension_is_rejected_without_copying(self):
        source = self.sources / "notes.txt"
        source.write_text("Nội dung", encoding="utf-8")

        with self.assertRaisesRegex(UnsupportedBookError, "PDF hoặc EPUB"):
            self.service.import_book(source)

        self.assertEqual(list(self.paths.books.iterdir()), [])

    def test_oversized_source_is_rejected_before_managed_copy(self):
        source = make_epub(self.sources)

        with patch(
            "vieneu_reader.importers.service.MAX_MANAGED_SOURCE_BYTES",
            8,
            create=True,
        ):
            with self.assertRaisesRegex(CorruptBookError, "dung lượng"):
                self.service.import_book(source)

        self.assertTrue(source.is_file())
        self.assertEqual(self.repository.count_books(), 0)
        self.assertEqual(list(self.paths.books.iterdir()), [])

    def test_copy_io_failure_is_mapped_to_safe_import_error(self):
        source = make_epub(self.sources)

        with patch(
            "vieneu_reader.importers.service._copy_bounded",
            side_effect=OSError("disk full"),
        ):
            with self.assertRaisesRegex(CorruptBookError, "sao chép"):
                self.service.import_book(source)

        self.assertTrue(source.is_file())
        self.assertEqual(list(self.paths.books.iterdir()), [])

    def test_bounded_copy_rejects_a_stream_that_grows_past_its_limit(self):
        source = BytesIO(b"12345")
        destination = BytesIO()

        with self.assertRaisesRegex(CorruptBookError, "dung lượng"):
            _copy_bounded(source, destination, max_bytes=4)

        self.assertLessEqual(len(destination.getvalue()), 4)

    def test_database_failure_removes_only_the_new_managed_copy(self):
        existing = sample_book("source-hash-conflict")
        existing_path = self.paths.books / f"{existing.id}.epub"
        existing_path.write_bytes(b"existing managed book")
        self.repository.add_book(existing, existing_path)
        conflicting = replace(existing, id=stable_id("different-book-id"))
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: conflicting},
        )
        source = self.sources / "conflict.epub"
        source.write_bytes(b"new source remains owned by caller")

        with self.assertRaisesRegex(LibraryStorageError, "thư viện"):
            service.import_book(source)

        conflicting_path = self.paths.books / f"{conflicting.id}.epub"
        self.assertTrue(source.is_file())
        self.assertTrue(existing_path.is_file())
        self.assertFalse(conflicting_path.exists())
        self.assertEqual(self.repository.count_books(), 1)

    def test_retry_adopts_matching_managed_copy_left_before_database_commit(self):
        payload = b"managed content committed before process death"
        source = self.sources / "recover.epub"
        source.write_bytes(payload)
        book = _sample_book_for_payload("orphan-recovery", payload)
        managed_path = self.paths.books / f"{book.id}.epub"
        managed_path.write_bytes(payload)
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: book},
        )

        result = service.import_book(source)

        self.assertFalse(result.was_existing)
        self.assertEqual(result.managed_path, managed_path)
        self.assertEqual(managed_path.read_bytes(), payload)
        self.assertEqual(self.repository.get_book(book.id).book, book)
        self.assertEqual(list(self.paths.books.glob(".import-*")), [])

    def test_retry_preserves_and_rejects_mismatched_managed_orphan(self):
        payload = b"expected managed content"
        source = self.sources / "mismatch.epub"
        source.write_bytes(payload)
        book = _sample_book_for_payload("orphan-mismatch", payload)
        managed_path = self.paths.books / f"{book.id}.epub"
        managed_path.write_bytes(b"different existing content")
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: book},
        )

        with self.assertRaisesRegex(CorruptBookError, "chưa hoàn tất"):
            service.import_book(source)

        self.assertEqual(managed_path.read_bytes(), b"different existing content")
        self.assertEqual(self.repository.count_books(), 0)
        self.assertEqual(list(self.paths.books.glob(".import-*")), [])

    def test_retry_never_adopts_symlinked_managed_orphan(self):
        payload = b"matching content behind a symlink"
        source = self.sources / "symlink-source.epub"
        external = self.sources / "external.epub"
        source.write_bytes(payload)
        external.write_bytes(payload)
        book = _sample_book_for_payload("orphan-symlink", payload)
        managed_path = self.paths.books / f"{book.id}.epub"
        managed_path.symlink_to(external)
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: book},
        )

        with self.assertRaisesRegex(CorruptBookError, "chưa hoàn tất"):
            service.import_book(source)

        self.assertTrue(managed_path.is_symlink())
        self.assertEqual(external.read_bytes(), payload)
        self.assertEqual(self.repository.count_books(), 0)

    def test_retry_never_adopts_managed_orphan_owned_by_another_user(self):
        payload = b"matching content with untrusted ownership"
        source = self.sources / "owner-source.epub"
        source.write_bytes(payload)
        book = _sample_book_for_payload("orphan-owner", payload)
        managed_path = self.paths.books / f"{book.id}.epub"
        managed_path.write_bytes(payload)
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: book},
        )

        with patch(
            "vieneu_reader.importers.service.os.getuid",
            return_value=os.getuid() + 1,
        ):
            with self.assertRaisesRegex(CorruptBookError, "chưa hoàn tất"):
                service.import_book(source)

        self.assertEqual(managed_path.read_bytes(), payload)
        self.assertEqual(self.repository.count_books(), 0)

    def test_retry_rejects_managed_fifo_without_blocking(self):
        payload = b"content matching the parser identity"
        source = self.sources / "fifo-source.epub"
        source.write_bytes(payload)
        book = _sample_book_for_payload("orphan-fifo", payload)
        managed_path = self.paths.books / f"{book.id}.epub"
        os.mkfifo(managed_path, mode=0o600)
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: book},
        )

        with self.assertRaisesRegex(CorruptBookError, "chưa hoàn tất"):
            service.import_book(source)

        self.assertTrue(stat.S_ISFIFO(managed_path.lstat().st_mode))
        self.assertEqual(self.repository.count_books(), 0)

    def test_concurrent_duplicate_imports_are_serialized_without_overlap(self):
        book = sample_book("concurrent-import")
        first_started = Event()
        second_started = Event()
        release_first = Event()
        call_lock = Lock()
        call_count = 0

        def blocking_parser(_path):
            nonlocal call_count
            with call_lock:
                call_count += 1
                call = call_count
            if call == 1:
                first_started.set()
                if not release_first.wait(timeout=2):
                    raise RuntimeError("test timed out releasing first parser")
            else:
                second_started.set()
            return book

        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": blocking_parser},
        )
        source = self.sources / "concurrent.epub"
        source.write_bytes(b"same source")
        results = []
        errors = []

        def run_import():
            try:
                results.append(service.import_book(source))
            except Exception as error:
                errors.append(error)

        first = Thread(target=run_import)
        second = Thread(target=run_import)
        first.start()
        self.assertTrue(first_started.wait(timeout=1))
        second.start()
        overlapped = second_started.wait(timeout=0.1)
        release_first.set()
        first.join(timeout=2)
        second.join(timeout=2)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertFalse(overlapped)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(result.was_existing for result in results), 1)
        stored = self.repository.get_book(book.id)
        self.assertIsNotNone(stored)
        self.assertTrue(stored.managed_path.is_file())

    def test_losing_insert_never_removes_a_copy_referenced_by_database(self):
        book = sample_book("committed-winner")
        source = self.sources / "winner.epub"
        source.write_bytes(b"same managed content")
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: book},
        )
        real_add_book = self.repository.add_book

        def committed_elsewhere_then_failed(candidate, managed_path):
            real_add_book(candidate, managed_path)
            raise sqlite3.IntegrityError("simulated losing concurrent insert")

        with patch.object(
            self.repository,
            "add_book",
            side_effect=committed_elsewhere_then_failed,
        ):
            with self.assertRaisesRegex(LibraryStorageError, "thư viện"):
                service.import_book(source)

        stored = self.repository.get_book(book.id)
        self.assertIsNotNone(stored)
        self.assertTrue(stored.managed_path.is_file())

    def test_sqlite_operational_failure_is_mapped_and_cleaned_up(self):
        book = sample_book("sqlite-operational-error")
        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: book},
        )
        source = self.sources / "sqlite-error.epub"
        source.write_bytes(b"caller-owned source")

        with patch.object(
            self.repository,
            "add_book",
            side_effect=sqlite3.OperationalError("database or disk is full"),
        ):
            with self.assertRaisesRegex(LibraryStorageError, "thư viện"):
                service.import_book(source)

        self.assertTrue(source.is_file())
        self.assertEqual(self.repository.count_books(), 0)
        self.assertEqual(list(self.paths.books.glob("*.epub")), [])

    def test_cleanup_failure_after_duplicate_is_safe_and_recovered_next_import(self):
        source = make_epub(self.sources)
        self.service.import_book(source)
        real_unlink = Path.unlink

        def fail_scratch_unlink(path, *args, **kwargs):
            if path.name.startswith(".import-"):
                raise OSError("simulated cleanup failure")
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", new=fail_scratch_unlink):
            with self.assertRaisesRegex(LibraryStorageError, "dọn dẹp"):
                self.service.import_book(source)

        self.assertEqual(len(list(self.paths.books.glob(".import-*"))), 1)
        result = self.service.import_book(source)
        self.assertTrue(result.was_existing)
        self.assertEqual(list(self.paths.books.glob(".import-*")), [])

    def test_cleanup_failure_never_overrides_primary_import_error(self):
        source = self.sources / "parser-error.epub"
        source.write_bytes(b"caller-owned source")

        def corrupt_parser(_path):
            raise CorruptBookError("lỗi parser chính")

        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": corrupt_parser},
        )
        real_unlink = Path.unlink

        def fail_scratch_unlink(path, *args, **kwargs):
            if path.name.startswith(".import-"):
                raise OSError("simulated cleanup failure")
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", new=fail_scratch_unlink):
            with self.assertRaisesRegex(CorruptBookError, "parser chính"):
                service.import_book(source)

        self.assertEqual(len(list(self.paths.books.glob(".import-*"))), 1)
        recovery = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": lambda _path: sample_book("cleanup-recovery")},
        )
        recovery.import_book(source)
        self.assertEqual(list(self.paths.books.glob(".import-*")), [])

    def test_lock_close_failure_never_overrides_primary_import_error(self):
        source = self.sources / "lock-release-error.epub"
        source.write_bytes(b"caller-owned source")

        def corrupt_parser(_path):
            raise CorruptBookError("lỗi parser chính")

        service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": corrupt_parser},
        )
        real_close = os.close

        def close_then_report(descriptor):
            real_close(descriptor)
            return OSError("simulated close report after descriptor release")

        with patch.object(
            service,
            "_close_import_lock",
            side_effect=close_then_report,
        ):
            with self.assertRaisesRegex(CorruptBookError, "parser chính"):
                service.import_book(source)

    def test_successful_import_releases_flock_by_closing_without_explicit_unlock(self):
        source = make_epub(self.sources, name="close-release.epub")
        real_flock = fcntl.flock

        def reject_explicit_unlock(descriptor, operation):
            if operation == fcntl.LOCK_UN:
                raise OSError("explicit unlock must not define commit success")
            return real_flock(descriptor, operation)

        with patch(
            "vieneu_reader.importers.service.fcntl.flock",
            side_effect=reject_explicit_unlock,
        ):
            result = self.service.import_book(source)

        self.assertFalse(result.was_existing)
        self.assertEqual(self.repository.count_books(), 1)
        self.assertTrue(result.managed_path.is_file())

    def test_lock_close_report_after_commit_preserves_successful_result(self):
        source = make_epub(self.sources, name="close-report.epub")
        real_close = os.close

        def close_then_report(descriptor):
            real_close(descriptor)
            return OSError("simulated close report after descriptor release")

        with patch.object(
            self.service,
            "_close_import_lock",
            side_effect=close_then_report,
        ):
            result = self.service.import_book(source)

        self.assertFalse(result.was_existing)
        self.assertEqual(self.repository.count_books(), 1)
        self.assertTrue(result.managed_path.is_file())

    def test_scavenger_removes_only_owned_regular_import_scratch(self):
        stale = self.paths.books / ".import-abcdefgh.epub"
        unrelated = self.paths.books / ".import-note.txt"
        directory = self.paths.books / ".import-ijklmnop.epub"
        external = self.sources / "outside.epub"
        symlink = self.paths.books / ".import-qrstuvwx.epub"
        stale.write_bytes(b"stale scratch")
        unrelated.write_bytes(b"unrelated")
        directory.mkdir()
        external.write_bytes(b"outside")
        symlink.symlink_to(external)
        source = make_epub(self.sources, name="scavenge.epub")

        self.service.import_book(source)

        self.assertFalse(stale.exists())
        self.assertTrue(unrelated.is_file())
        self.assertTrue(directory.is_dir())
        self.assertTrue(symlink.is_symlink())
        self.assertTrue(external.is_file())

    def test_full_import_lifecycle_is_serialized_across_service_instances(self):
        book = sample_book("cross-service-lifecycle")
        first_started = Event()
        second_started = Event()
        release_first = Event()

        def first_parser(_path):
            first_started.set()
            if not release_first.wait(timeout=2):
                raise RuntimeError("test timed out releasing first parser")
            return book

        def second_parser(_path):
            second_started.set()
            return book

        first_service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": first_parser},
        )
        second_service = LibraryService(
            self.paths,
            self.repository,
            parsers={".epub": second_parser},
        )
        source = self.sources / "cross-service.epub"
        source.write_bytes(b"same source")
        results = []
        errors = []

        def run_import(service):
            try:
                results.append(service.import_book(source))
            except Exception as error:
                errors.append(error)

        first = Thread(target=run_import, args=(first_service,))
        second = Thread(target=run_import, args=(second_service,))
        first.start()
        self.assertTrue(first_started.wait(timeout=1))
        second.start()
        overlapped = second_started.wait(timeout=0.1)
        release_first.set()
        first.join(timeout=3)
        second.join(timeout=3)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertFalse(overlapped)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(result.was_existing for result in results), 1)
        stored = self.repository.get_book(book.id)
        self.assertIsNotNone(stored)
        self.assertTrue(stored.managed_path.is_file())


if __name__ == "__main__":
    unittest.main()
