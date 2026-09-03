from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from vieneu_reader.config import AppPaths
from vieneu_reader.domain.models import stable_id
from vieneu_reader.storage.errors import RepositoryError
from vieneu_reader.storage.repository import (
    LibraryRepository,
    Progress,
    SCHEMA_VERSION,
)

from tests.domain.book_fixture import sample_book


class LibraryRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.paths = AppPaths.create(Path(self.temp_dir.name) / "app-data")
        self.repository = LibraryRepository(self.paths.database)

    def tearDown(self):
        self.repository.close()
        self.temp_dir.cleanup()

    def test_app_paths_create_private_owned_directories(self):
        self.assertTrue(self.paths.books.is_dir())
        self.assertTrue(self.paths.cache.is_dir())
        self.assertTrue(self.paths.models.is_dir())
        self.assertEqual(self.paths.root.stat().st_mode & 0o077, 0)

    def test_repository_creates_schema_version_one(self):
        self.assertEqual(self.repository.schema_version(), 1)
        self.assertEqual(self.repository.count_books(), 0)
        self.assertEqual(self.paths.database.stat().st_mode & 0o077, 0)

    def test_future_schema_is_rejected_before_current_tables_are_created(self):
        database = self.paths.root / "future.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            with connection:
                connection.execute(
                    "CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO app_meta(key, value) VALUES('schema_version', '999')"
                )

        # Kho từ bản mới hơn nay có câu riêng (xem
        # UpgradingOverAnOlderInstallTests). Điều test này canh không đổi:
        # từ chối TRƯỚC khi tạo bất kỳ bảng nào của bản hiện tại.
        with self.assertRaisesRegex(RuntimeError, "mới hơn"):
            LibraryRepository(database)

        with closing(sqlite3.connect(database)) as connection:
            table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertNotIn("books", table_names)
        self.assertNotIn("progress", table_names)
        self.assertEqual(journal_mode, "delete")

    def test_book_round_trip_preserves_unicode_domain_and_managed_path(self):
        book = sample_book("tiếng Việt")
        managed_path = self.paths.books / f"{book.id}.epub"
        managed_path.write_bytes(b"managed copy")

        self.repository.add_book(book, managed_path)
        stored = self.repository.get_book(book.id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.book, book)
        self.assertEqual(stored.managed_path, managed_path)
        self.assertEqual(self.repository.count_books(), 1)

    def test_partial_meta_without_version_is_rejected_without_bootstrap(self):
        database = self.paths.root / "partial-meta.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            with connection:
                connection.execute(
                    "CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )

        with self.assertRaisesRegex(RuntimeError, "schema"):
            LibraryRepository(database)

        with closing(sqlite3.connect(database)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(tables, {"app_meta"})
        self.assertEqual(journal_mode, "delete")

    def test_unknown_user_table_without_meta_is_rejected_without_bootstrap(self):
        database = self.paths.root / "unknown.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            with connection:
                connection.execute("CREATE TABLE unknown_owner (value TEXT)")

        with self.assertRaisesRegex(RuntimeError, "schema"):
            LibraryRepository(database)

        with closing(sqlite3.connect(database)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertEqual(tables, {"unknown_owner"})

    def test_progress_is_independent_per_book_and_updates_in_place(self):
        first = sample_book("first")
        second = sample_book("second")
        for book in (first, second):
            path = self.paths.books / f"{book.id}.epub"
            path.write_bytes(book.id.encode("ascii"))
            self.repository.add_book(book, path)

        first_progress = Progress(first.id, first.chapters[0].segments[0].id, 1.0, "Adam")
        second_progress = Progress(second.id, second.chapters[0].segments[1].id, 1.2, "Trúc Ly")
        self.repository.save_progress(first_progress)
        self.repository.save_progress(second_progress)
        updated = Progress(first.id, first.chapters[0].segments[1].id, 0.9, "Mai Anh")
        self.repository.save_progress(updated)

        self.assertEqual(self.repository.load_progress(first.id), updated)
        self.assertEqual(self.repository.load_progress(second.id), second_progress)

    def test_active_book_round_trip_tracks_the_last_opened_book(self):
        first = sample_book("first")
        second = sample_book("second")
        for book in (first, second):
            path = self.paths.books / f"{book.id}.epub"
            path.write_bytes(book.id.encode("ascii"))
            self.repository.add_book(book, path)

        self.assertIsNone(self.repository.load_active_book_id())
        self.repository.save_active_book_id(first.id)
        self.repository.save_active_book_id(second.id)

        self.assertEqual(self.repository.load_active_book_id(), second.id)

    def test_preference_update_preserves_the_newest_saved_segment(self):
        book = sample_book("preferences")
        path = self.paths.books / f"{book.id}.epub"
        path.write_bytes(b"managed")
        self.repository.add_book(book, path)
        newest = Progress(book.id, book.chapters[0].segments[1].id, 1.0, "Adam")
        self.repository.save_progress(newest)

        self.repository.save_preferences(
            Progress(book.id, book.chapters[0].segments[0].id, 1.4, "Trúc Ly")
        )

        stored = self.repository.load_progress(book.id)
        self.assertEqual(stored.segment_id, newest.segment_id)
        self.assertEqual(stored.playback_rate, 1.4)
        self.assertEqual(stored.voice_id, "Trúc Ly")

    def test_sqlite_read_failure_is_mapped_to_repository_error(self):
        self.repository._connection.close()

        with self.assertRaises(RepositoryError) as raised:
            self.repository.list_books()

        self.assertIsInstance(raised.exception.__cause__, sqlite3.Error)

    def test_malformed_document_payload_is_mapped_to_repository_error(self):
        book = sample_book("malformed-document")
        managed = self.paths.books / f"{book.id}.epub"
        managed.write_bytes(b"managed")
        self.repository.add_book(book, managed)
        with self.repository._connection:
            self.repository._connection.execute(
                "UPDATE books SET document_json = '{' WHERE id = ?",
                (book.id,),
            )

        with self.assertRaises(RepositoryError) as raised:
            self.repository.get_book(book.id)

        self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_overflowing_document_ordinal_is_mapped_to_repository_error(self):
        book = sample_book("overflowing-document")
        managed = self.paths.books / f"{book.id}.epub"
        managed.write_bytes(b"managed")
        self.repository.add_book(book, managed)
        with self.repository._connection:
            self.repository._connection.execute(
                "UPDATE books SET document_json = "
                "replace(document_json, '\"ordinal\":0', '\"ordinal\":1e400') "
                "WHERE id = ?",
                (book.id,),
            )

        with self.assertRaises(RepositoryError) as raised:
            self.repository.get_book(book.id)

        self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_structurally_valid_document_cannot_disagree_with_database_identity(self):
        book = sample_book("identity-mismatch")
        managed = self.paths.books / f"{book.id}.epub"
        managed.write_bytes(b"managed")
        self.repository.add_book(book, managed)
        row = self.repository._connection.execute(
            "SELECT document_json FROM books WHERE id = ?",
            (book.id,),
        ).fetchone()
        document = json.loads(row["document_json"])
        different_hash = stable_id("different-persisted-source")
        document["source_hash"] = different_hash
        document["id"] = stable_id(different_hash, "epub")
        with self.repository._connection:
            self.repository._connection.execute(
                "UPDATE books SET document_json = ? WHERE id = ?",
                (json.dumps(document), book.id),
            )

        with self.assertRaises(RepositoryError):
            self.repository.get_book(book.id)

    def test_null_segment_text_is_rejected_as_repository_corruption(self):
        book = sample_book("null-segment-text")
        managed = self.paths.books / f"{book.id}.epub"
        managed.write_bytes(b"managed")
        self.repository.add_book(book, managed)
        row = self.repository._connection.execute(
            "SELECT document_json FROM books WHERE id = ?",
            (book.id,),
        ).fetchone()
        document = json.loads(row["document_json"])
        document["chapters"][0]["segments"][0]["text"] = None
        with self.repository._connection:
            self.repository._connection.execute(
                "UPDATE books SET document_json = ? WHERE id = ?",
                (json.dumps(document), book.id),
            )

        with self.assertRaises(RepositoryError):
            self.repository.get_book(book.id)

    def test_invalid_progress_number_is_mapped_to_repository_error(self):
        book = sample_book("malformed-progress")
        managed = self.paths.books / f"{book.id}.epub"
        managed.write_bytes(b"managed")
        self.repository.add_book(book, managed)
        with self.repository._connection:
            self.repository._connection.execute(
                "INSERT INTO progress(book_id, segment_id, playback_rate, voice_id) "
                "VALUES (?, ?, ?, ?)",
                (book.id, book.chapters[0].segments[0].id, "oops", "Adam"),
            )

        with self.assertRaises(RepositoryError) as raised:
            self.repository.load_progress(book.id)

        self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_invalid_progress_identity_is_mapped_to_repository_error(self):
        book = sample_book("malformed-progress-identity")
        managed = self.paths.books / f"{book.id}.epub"
        managed.write_bytes(b"managed")
        self.repository.add_book(book, managed)
        with self.repository._connection:
            self.repository._connection.execute(
                "INSERT INTO progress(book_id, segment_id, playback_rate, voice_id) "
                "VALUES (?, ?, ?, ?)",
                (book.id, "not-a-segment-id", 1.0, "Adam"),
            )

        with self.assertRaises(RepositoryError):
            self.repository.load_progress(book.id)

    def test_non_sqlite_database_is_mapped_during_repository_construction(self):
        database = self.paths.root / "corrupt.sqlite3"
        database.write_bytes(b"this is not a sqlite database")

        with self.assertRaises(RepositoryError) as raised:
            LibraryRepository(database)

        self.assertIsInstance(raised.exception.__cause__, sqlite3.Error)

    def test_constraint_failure_rolls_back_before_repository_error(self):
        existing = sample_book("repository-conflict")
        managed = self.paths.books / f"{existing.id}.epub"
        managed.write_bytes(b"existing")
        self.repository.add_book(existing, managed)
        conflicting = replace(existing, id=stable_id("different-id"))
        conflicting_path = self.paths.books / f"{conflicting.id}.epub"

        with self.assertRaises(RepositoryError) as raised:
            self.repository.add_book(conflicting, conflicting_path)

        self.assertIsInstance(raised.exception.__cause__, sqlite3.IntegrityError)
        self.assertEqual(self.repository.count_books(), 1)

    def test_non_sqlite_repository_bug_is_not_masked(self):
        book = sample_book("repository-programming-error")
        managed = self.paths.books / f"{book.id}.epub"
        managed.write_bytes(b"managed")
        self.repository.add_book(book, managed)

        with patch(
            "vieneu_reader.storage.repository._document_from_payload",
            side_effect=RuntimeError("programming bug"),
        ):
            with self.assertRaisesRegex(RuntimeError, "programming bug"):
                self.repository.list_books()


def _book_with_structure():
    from vieneu_reader.domain.models import BookDocument, Chapter, Segment

    source_hash = stable_id("source", "structure")
    book_id = stable_id(source_hash, "epub")
    chapter_id = stable_id(book_id, "chapter", "0")

    def segment(ordinal, text, kind="paragraph", joint="block"):
        return Segment(
            id=stable_id(chapter_id, "segment", str(ordinal)),
            chapter_id=chapter_id,
            ordinal=ordinal,
            text=text,
            kind=kind,
            joint=joint,
        )

    return BookDocument(
        id=book_id,
        title="Sách cấu trúc",
        source_format="epub",
        source_hash=source_hash,
        chapters=(
            Chapter(
                chapter_id,
                "Chương",
                0,
                (
                    segment(0, "Chương một", kind="heading"),
                    segment(1, "Mở đầu chưa trọn,"),
                    segment(2, "nên vẫn cùng một câu.", joint="split"),
                    segment(3, "Câu mới hẳn hoi."),
                ),
            ),
        ),
    )


class SegmentStructureStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.paths = AppPaths.create(Path(self.temp_dir.name) / "app-data")
        self.repository = LibraryRepository(self.paths.database)

    def tearDown(self):
        self.repository.close()
        self.temp_dir.cleanup()

    def _store(self, book):
        managed_path = self.paths.books / f"{book.id}.epub"
        managed_path.write_bytes(b"managed copy")
        self.repository.add_book(book, managed_path)

    def _rewrite_payload(self, book_id, mutate):
        row = self.repository._connection.execute(
            "SELECT document_json FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        document = json.loads(row["document_json"])
        mutate(document)
        with self.repository._connection:
            self.repository._connection.execute(
                "UPDATE books SET document_json = ? WHERE id = ?",
                (json.dumps(document, ensure_ascii=False), book_id),
            )

    def test_round_trip_preserves_kind_and_joint(self):
        book = _book_with_structure()
        self._store(book)

        stored = self.repository.get_book(book.id)

        self.assertEqual(stored.book, book)
        segments = stored.book.chapters[0].segments
        self.assertEqual(segments[0].kind, "heading")
        self.assertEqual(segments[2].joint, "split")

    def test_books_stored_before_structure_infer_their_joints(self):
        book = _book_with_structure()
        self._store(book)

        def strip_structure(document):
            for chapter in document["chapters"]:
                for segment in chapter["segments"]:
                    del segment["kind"]
                    del segment["joint"]

        self._rewrite_payload(book.id, strip_structure)
        stored = self.repository.get_book(book.id)

        segments = stored.book.chapters[0].segments
        self.assertEqual({segment.kind for segment in segments}, {"paragraph"})
        self.assertEqual(
            [segment.joint for segment in segments],
            # The heading and the open comma both leave their sentence
            # unfinished, so the following segments read as continuations —
            # a deliberately conservative guess that keeps those pauses
            # short; only the finished sentence starts a fresh block.
            ["block", "split", "split", "block"],
        )

    def test_invalid_kind_or_joint_is_repository_corruption(self):
        for field, value in (("kind", "banner"), ("joint", "sideways")):
            with self.subTest(field=field):
                book = _book_with_structure()
                repository = LibraryRepository(
                    self.paths.root / f"invalid-{field}.sqlite3"
                )
                try:
                    managed_path = self.paths.books / f"{book.id}-{field}.epub"
                    managed_path.write_bytes(b"managed copy")
                    repository.add_book(book, managed_path)
                    row = repository._connection.execute(
                        "SELECT document_json FROM books WHERE id = ?",
                        (book.id,),
                    ).fetchone()
                    document = json.loads(row["document_json"])
                    document["chapters"][0]["segments"][1][field] = value
                    with repository._connection:
                        repository._connection.execute(
                            "UPDATE books SET document_json = ? WHERE id = ?",
                            (json.dumps(document, ensure_ascii=False), book.id),
                        )
                    with self.assertRaises(RepositoryError):
                        repository.get_book(book.id)
                finally:
                    repository.close()


if __name__ == "__main__":
    unittest.main()


class UpgradingOverAnOlderInstallTests(unittest.TestCase):
    """Dragging a new build over the old one is how this app updates now.

    The store it finds is the person's whole library, and it usually predates
    the code. These are the four things that decide whether that is an
    upgrade or a bad afternoon.
    """

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database = Path(self.temp_dir.name) / "library.sqlite3"

    def _v1_store_with_a_book(self) -> str:
        """A real store, written by today's build, then stamped older."""
        with closing(LibraryRepository(self.database)) as repository:
            book = sample_book()
            repository.add_book(book, self.database.parent / "b.epub")
            return book.id

    def _stamp(self, version: int) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "UPDATE app_meta SET value = ? WHERE key = 'schema_version'",
                (str(version),),
            )
            connection.commit()

    def test_an_older_library_is_carried_forward_with_its_books_intact(self):
        book_id = self._v1_store_with_a_book()
        self._stamp(1)
        ran: list[int] = []

        def to_v2(connection):
            ran.append(2)
            connection.execute("CREATE TABLE upgraded_marker (id INTEGER)")

        with patch("vieneu_reader.storage.repository.SCHEMA_VERSION", 2), \
             patch.dict("vieneu_reader.storage.repository._MIGRATIONS", {2: to_v2}):
            with closing(LibraryRepository(self.database)) as repository:
                self.assertEqual(ran, [2])
                # The point of the whole exercise: the library survived.
                self.assertIsNotNone(repository.get_book(book_id))
                self.assertEqual(repository.schema_version(), 2)

    def test_a_gap_of_two_versions_runs_both_steps_in_order(self):
        self._v1_store_with_a_book()
        self._stamp(1)
        ran: list[int] = []
        steps = {
            2: lambda connection: ran.append(2),
            3: lambda connection: ran.append(3),
        }
        with patch("vieneu_reader.storage.repository.SCHEMA_VERSION", 3), \
             patch.dict("vieneu_reader.storage.repository._MIGRATIONS", steps):
            with closing(LibraryRepository(self.database)) as repository:
                self.assertEqual(ran, [2, 3], "one step at a time, never a leap")
                self.assertEqual(repository.schema_version(), 3)

    def test_a_library_from_a_newer_build_is_refused_by_name_not_migrated(self):
        # The person has a newer ReadEase somewhere. Touching their store from
        # here could only damage it, and "unsupported" would send them hunting
        # for a corrupt file instead of the newer app.
        self._v1_store_with_a_book()
        self._stamp(SCHEMA_VERSION + 5)
        # RuntimeError, not RepositoryError: the same path the older
        # "Unsupported ReadEase database schema" check already takes out of
        # this constructor. Changing that type is a wider job than this one.
        with self.assertRaises(RuntimeError) as caught:
            LibraryRepository(self.database)
        self.assertIn("mới hơn", str(caught.exception))

    def test_a_failed_step_leaves_the_library_exactly_as_it_was(self):
        book_id = self._v1_store_with_a_book()
        self._stamp(1)

        def explodes(connection):
            connection.execute("CREATE TABLE half (id INTEGER)")
            raise sqlite3.OperationalError("nửa chừng thì hỏng")

        with patch("vieneu_reader.storage.repository.SCHEMA_VERSION", 2), \
             patch.dict("vieneu_reader.storage.repository._MIGRATIONS", {2: explodes}):
            with self.assertRaises(RuntimeError):
                LibraryRepository(self.database)

        # Still openable by the build the person already has, still at v1,
        # and without the table the half-run step created. Half a migration
        # is worse than none.
        with closing(sqlite3.connect(self.database)) as connection:
            connection.row_factory = sqlite3.Row
            version = connection.execute(
                "SELECT value FROM app_meta WHERE key = 'schema_version'"
            ).fetchone()["value"]
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertEqual(int(version), 1)
        self.assertNotIn("half", tables)
        with closing(LibraryRepository(self.database)) as repository:
            self.assertIsNotNone(repository.get_book(book_id))

