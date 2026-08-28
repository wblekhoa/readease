from __future__ import annotations

import os
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.integrations.apple_books import (
    AppleBooksLibrary,
    AppleBooksUnavailable,
    AppleBooksNotPermitted,
    AppleBooksUnreadable,
    UnknownAsset,
    build_transfer_plan,
)


def _make_library(root: Path, books: tuple[tuple[str, str, str, float], ...]) -> Path:
    path = root / "BKLibrary-1.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE ZBKLIBRARYASSET ("
        "ZASSETID TEXT, ZTITLE TEXT, ZEPUBID TEXT, ZREADINGPROGRESS REAL)"
    )
    connection.executemany(
        "INSERT INTO ZBKLIBRARYASSET VALUES (?, ?, ?, ?)", books
    )
    connection.commit()
    connection.close()
    return path


def _make_annotations(
    root: Path,
    rows: tuple[tuple[str, int, str, str | None, str | None, int], ...],
) -> Path:
    path = root / "AEAnnotation_v1.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE ZAEANNOTATION ("
        "ZANNOTATIONASSETID TEXT, ZANNOTATIONTYPE INTEGER,"
        "ZANNOTATIONLOCATION TEXT, ZANNOTATIONSELECTEDTEXT TEXT,"
        "ZANNOTATIONNOTE TEXT, ZANNOTATIONDELETED INTEGER)"
    )
    connection.executemany(
        "INSERT INTO ZAEANNOTATION VALUES (?, ?, ?, ?, ?, ?)", rows
    )
    connection.commit()
    connection.close()
    return path


SAME_EPUB = "urn:uuid:8b873e3e"
BOOKS = (
    # Titles and edition ids vary independently on purpose: SRC and DST share an
    # edition under different titles, and TWIN shares SRC's title under a different
    # edition. A verdict computed from the title instead of the edition fails both.
    ("SRC", "Bản một", SAME_EPUB, 0.30),
    ("DST", "Bản hai", SAME_EPUB, 0.60),
    ("TWIN", "Bản một", "urn:uuid:different", 0.10),
    ("NOEDITION", "Không rõ bản", None, 0.05),
)
ROWS = (
    ("SRC", 2, "epubcfi(/6/26[id220]!/4/64/4/1,:0,:119)", "đoạn được bôi", "ghi chú", 0),
    ("SRC", 2, "epubcfi(/6/38[id206]!/4/188/4/1,:75,:153)", "đoạn hai", None, 0),
    ("SRC", 3, "epubcfi(/6/26[id220]!/4/2[ch05],/4,/5)", None, None, 0),
    ("SRC", 2, "epubcfi(/6/26[id220]!/4/12/1:0)", "đã xoá", None, 1),
    ("DST", 3, "epubcfi(/6/38[id206]!/4/16/1,:201,:202)", None, None, 0),
)


class AppleBooksReaderTests(unittest.TestCase):
    def test_reads_books_and_live_annotations_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            self.assertEqual(len(library.books()), 4)
            # The deleted row must not appear.
            self.assertEqual(len(library.annotations("SRC")), 3)
            self.assertEqual(len(library.annotations("DST")), 1)

    def test_a_missing_database_is_named_not_guessed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=root / "absent.sqlite",
                annotation_database=root / "absent2.sqlite",
            )
            with self.assertRaises(AppleBooksUnavailable):
                library.books()

    def test_unknown_asset_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            with self.assertRaises(UnknownAsset):
                build_transfer_plan(library, "SRC", "NOPE")

    def test_plan_marks_a_same_edition_transfer(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            plan = build_transfer_plan(library, "SRC", "DST")
            self.assertEqual(len(plan.items), 3)
            self.assertTrue(all(item.verdict == "same-edition" for item in plan.items))
            self.assertTrue(plan.same_edition)

    def test_a_shared_title_is_not_a_shared_edition(self) -> None:
        """TWIN carries SRC's title under a different edition id."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            source = library.book("SRC")
            twin = library.book("TWIN")
            self.assertEqual(source.title, twin.title)
            self.assertNotEqual(source.edition_id, twin.edition_id)
            self.assertFalse(build_transfer_plan(library, "SRC", "TWIN").same_edition)

    def test_an_unknown_edition_never_counts_as_the_same_edition(self) -> None:
        """A NULL edition id must fall to the cautious side, not match everything."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            self.assertEqual(library.book("NOEDITION").edition_id, "")
            plan = build_transfer_plan(library, "NOEDITION", "NOEDITION")
            self.assertFalse(plan.same_edition)

    def test_each_annotation_field_comes_from_its_own_column(self) -> None:
        """Swapping the note and highlight columns would show private text as a quote."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            annotated = next(a for a in library.annotations("SRC") if a.has_note)
            self.assertEqual(annotated.selected_text, "đoạn được bôi")
            self.assertEqual(annotated.note, "ghi chú")
            self.assertEqual(annotated.kind, 2)
            self.assertTrue(annotated.location.startswith("epubcfi(/6/26[id220]"))

    def test_the_persons_words_stay_out_of_the_default_repr(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            rendered = repr(build_transfer_plan(library, "SRC", "DST"))
            self.assertNotIn("ghi chú", rendered)
            self.assertNotIn("đoạn được bôi", rendered)

    def test_plan_flags_a_different_edition_for_review(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            plan = build_transfer_plan(library, "SRC", "TWIN")
            self.assertFalse(plan.same_edition)
            self.assertTrue(all(item.verdict == "needs-review" for item in plan.items))


class WriteAheadLogTests(unittest.TestCase):
    """Books runs while ReadEase reads, so its newest rows live in the -wal file.

    Copying the .sqlite alone reports a stale library: during development that
    silently hid an entire book the person could see in Books at that moment.
    """

    def _wal_database(self, root: Path) -> Path:
        path = root / "AEAnnotation_v1.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            "CREATE TABLE ZAEANNOTATION ("
            "ZANNOTATIONASSETID TEXT, ZANNOTATIONTYPE INTEGER,"
            "ZANNOTATIONLOCATION TEXT, ZANNOTATIONSELECTEDTEXT TEXT,"
            "ZANNOTATIONNOTE TEXT, ZANNOTATIONDELETED INTEGER)"
        )
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        # This row exists only in the write-ahead log, exactly like a note the
        # person just made while Books is still open.
        connection.execute(
            "INSERT INTO ZAEANNOTATION VALUES ('SRC', 2, 'epubcfi(/6/2)', 'x', NULL, 0)"
        )
        connection.commit()
        # SQLite checkpoints on the last connection close, so the log only stays
        # uncheckpointed while this connection lives.
        self.addCleanup(connection.close)
        return path

    def test_the_sidecar_carries_rows_the_main_file_does_not_have_yet(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._wal_database(root)
            self.assertTrue(
                source.with_name(source.name + "-wal").is_file(),
                "fixture must leave an uncheckpointed write-ahead log",
            )

            without = root / "without"
            without.mkdir()
            shutil.copy2(source, without / source.name)
            self.assertEqual(
                len(AppleBooksLibrary(annotation_database=without / source.name)
                    .annotations("SRC")),
                0,
                "the main file alone is stale - this is the bug being pinned",
            )

            self.assertEqual(
                len(AppleBooksLibrary(annotation_database=source).annotations("SRC")),
                1,
                "the reader must copy the sidecars and see the new row",
            )



class HostileFilesystemTests(unittest.TestCase):
    """The databases live in a TCC-protected container that Books writes to live.

    Every one of these was a crash before an adversarial review found it: a raw
    PermissionError where the module promises a named failure, a FileNotFoundError
    when Books removed its log mid-scan, and a symlink that read empty in silence.
    """

    @staticmethod
    def _wal_database(root: Path, case: unittest.TestCase) -> Path:
        path = root / "AEAnnotation_v1.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            "CREATE TABLE ZAEANNOTATION ("
            "ZANNOTATIONASSETID TEXT, ZANNOTATIONTYPE INTEGER,"
            "ZANNOTATIONLOCATION TEXT, ZANNOTATIONSELECTEDTEXT TEXT,"
            "ZANNOTATIONNOTE TEXT, ZANNOTATIONDELETED INTEGER)"
        )
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute(
            "INSERT INTO ZAEANNOTATION VALUES ('S', 2, 'cfi', 'x', NULL, 0)"
        )
        connection.commit()
        case.addCleanup(connection.close)
        return path

    def test_a_refused_folder_is_told_apart_from_a_missing_one(self) -> None:
        """Only the person can fix a refusal, so it must not read as "not found"."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._wal_database(root, self)
            os.chmod(path, 0)
            try:
                library = AppleBooksLibrary(annotation_database=path)
                with self.assertRaises(AppleBooksNotPermitted):
                    library.annotations("S")
            finally:
                # Restore inside the scope: the temp directory is gone by the time
                # addCleanup would run, and the sqlite connection still needs it.
                os.chmod(path, 0o600)

    def test_a_log_removed_mid_scan_is_not_a_crash(self) -> None:
        """SQLite deletes the -wal on a clean close, i.e. the person quits Books."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._wal_database(root, self)
            sidecar = path.with_name(path.name + "-wal")
            original = shutil.copy2

            def vanishing(source, destination, *args, **kwargs):
                if str(source).endswith("-wal"):
                    sidecar.unlink(missing_ok=True)
                return original(source, destination, *args, **kwargs)

            shutil.copy2 = vanishing
            self.addCleanup(setattr, shutil, "copy2", original)
            AppleBooksLibrary(annotation_database=path).annotations("S")

    def test_a_symlinked_database_reads_the_same_as_the_real_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._wal_database(root, self)
            link = root / "link.sqlite"
            link.symlink_to(path)
            self.assertEqual(
                len(AppleBooksLibrary(annotation_database=link).annotations("S")),
                len(AppleBooksLibrary(annotation_database=path).annotations("S")),
            )
            self.assertEqual(
                len(AppleBooksLibrary(annotation_database=link).annotations("S")), 1
            )


if __name__ == "__main__":
    unittest.main()


class ReadScopeTests(unittest.TestCase):
    """PRIVACY.md promises the annotations of the book you pick - only those."""

    def test_only_the_chosen_books_annotations_are_read_into_memory(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rows = tuple(
                (asset, 2, "cfi", f"secret of {asset}", None, 0)
                for asset in ("PICKED", "OTHER_1", "OTHER_2")
            )
            library = AppleBooksLibrary(
                annotation_database=_make_annotations(root, rows)
            )
            fetched: list[list[tuple]] = []
            original = AppleBooksLibrary._rows

            def spy(self, database, query, parameters=()):
                result = original(self, database, query, parameters)
                fetched.append(result)
                return result

            AppleBooksLibrary._rows = spy
            self.addCleanup(setattr, AppleBooksLibrary, "_rows", original)
            library.annotations("PICKED")

            self.assertEqual(
                [row[0] for row in fetched[0]],
                ["PICKED"],
                "another book's note text must never reach memory",
            )

    def test_constructing_the_library_touches_no_disk(self) -> None:
        """Someone who never opens the tab must never have their Books folder read."""
        visited: list[str] = []
        original = os.scandir

        def spy(path="."):
            visited.append(str(path))
            return original(path)

        os.scandir = spy
        self.addCleanup(setattr, os, "scandir", original)
        AppleBooksLibrary()

        self.assertEqual([path for path in visited if "iBooksX" in path], [])
