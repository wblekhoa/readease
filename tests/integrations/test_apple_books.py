from __future__ import annotations

import os
from pathlib import Path
import shutil
import sqlite3
import zipfile
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.integrations.apple_books import (
    AppleBooksLibrary,
    AppleBooksUnavailable,
    AmbiguousAsset,
    AppleBooksNotPermitted,
    AppleBooksUnreadable,
    SameBook,
    select_book,
    UnknownAsset,
    build_transfer_plan,
)


def _make_library(root: Path, books: tuple[tuple[str, str, str, float], ...]) -> Path:
    path = root / "BKLibrary-1.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE ZBKLIBRARYASSET ("
        "ZASSETID TEXT, ZTITLE TEXT, ZEPUBID TEXT, ZREADINGPROGRESS REAL,"
        " ZPATH TEXT)"
    )
    connection.executemany(
        "INSERT INTO ZBKLIBRARYASSET VALUES (?, ?, ?, ?, ?)",
        # Most cases do not care where the book file is; those rows say nowhere,
        # which is also what a library row looks like before the file lands.
        [tuple(book) + ("",) * (5 - len(book)) for book in books],
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


def _make_annotations_with_colour(
    root: Path,
    rows: tuple[tuple[str, int, str, str | None, str | None, int, int], ...],
) -> Path:
    """The same fixture, on a schema that DOES carry ZANNOTATIONSTYLE.

    Every other fixture here omits the column on purpose - it is the older
    Books schema, and it is what proves the reader survives its absence.
    """

    path = root / "AEAnnotation_v2.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE ZAEANNOTATION ("
        "ZANNOTATIONASSETID TEXT, ZANNOTATIONTYPE INTEGER,"
        "ZANNOTATIONLOCATION TEXT, ZANNOTATIONSELECTEDTEXT TEXT,"
        "ZANNOTATIONNOTE TEXT, ZANNOTATIONDELETED INTEGER,"
        "ZANNOTATIONSTYLE INTEGER)"
    )
    connection.executemany(
        "INSERT INTO ZAEANNOTATION VALUES (?, ?, ?, ?, ?, ?, ?)", rows
    )
    connection.commit()
    connection.close()
    return path


def _make_book(
    root: Path,
    name: str,
    *,
    chapters: int = 20,
    differs_at: int | None = None,
) -> Path:
    """A minimal EPUB with enough spine items for the CFIs used here.

    `differs_at` alters exactly one chapter, which is how two copies of a book
    come to share an edition id while a position inside them stops meaning the
    same thing.
    """

    path = root / name
    manifest, spine = [], []
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        for index in range(chapters):
            item = f"id{200 + index}"
            href = f"text/part{index:04d}.html"
            extra = "<img src=\"x.png\"/>" if index == differs_at else ""
            archive.writestr(
                f"OEBPS/{href}",
                '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
                f"{extra}<p>Chương {index}.</p></body></html>",
            )
            manifest.append(
                f'<item id="{item}" href="{href}" media-type="application/xhtml+xml"/>'
            )
            spine.append(f'<itemref idref="{item}"/>')
        archive.writestr(
            "OEBPS/content.opf",
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" '
            'version="3.0" unique-identifier="uid"><metadata/>'
            f'<manifest>{"".join(manifest)}</manifest>'
            f'<spine>{"".join(spine)}</spine></package>',
        )
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
    ("NOEDITION2", "Cũng không rõ", None, 0.05),
)
ROWS = (
    ("SRC", 2, "epubcfi(/6/26[id220]!/4/64/4/1,:0,:119)", "đoạn được bôi", "ghi chú", 0),
    ("SRC", 2, "epubcfi(/6/38[id206]!/4/188/4/1,:75,:153)", "đoạn hai", None, 0),
    ("SRC", 3, "epubcfi(/6/26[id220]!/4/2[ch05],/4,/5)", None, None, 0),
    ("SRC", 2, "epubcfi(/6/26[id220]!/4/12/1:0)", "đã xoá", None, 1),
    ("DST", 3, "epubcfi(/6/38[id206]!/4/16/1,:201,:202)", None, None, 0),
)


def _paired_library(
    root: Path,
    rows=None,
    *,
    differs_at: int | None = None,
) -> AppleBooksLibrary:
    """SRC and DST as two real book files, identical unless `differs_at` says.

    The plan compares the documents themselves, so a library whose rows point at
    no file can only ever return "needs-review".
    """

    source = _make_book(root, "src.epub")
    target = _make_book(root, "dst.epub", differs_at=differs_at)
    books = tuple(
        book + (str(source if book[0] == "SRC" else target),)
        if book[0] in ("SRC", "DST")
        else book
        for book in BOOKS
    )
    return AppleBooksLibrary(
        library_database=_make_library(root, books),
        annotation_database=_make_annotations(root, rows or ROWS),
    )


class AppleBooksReaderTests(unittest.TestCase):
    def test_reads_books_and_live_annotations_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            self.assertEqual(len(library.books()), 5)
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
            plan = build_transfer_plan(_paired_library(Path(directory)), "SRC", "DST")
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
            plan = build_transfer_plan(library, "NOEDITION", "NOEDITION2")
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


class RemainingEdgeTests(unittest.TestCase):
    """The cases an adversarial pass listed as low severity but real."""

    @staticmethod
    def _library(root: Path, books, rows=()):
        return AppleBooksLibrary(
            library_database=_make_library(root, books),
            annotation_database=_make_annotations(root, rows or ROWS),
        )

    def test_moving_a_book_onto_itself_is_refused(self) -> None:
        with TemporaryDirectory() as directory:
            library = self._library(Path(directory), BOOKS)
            with self.assertRaises(SameBook):
                build_transfer_plan(library, "SRC", "SRC")

    def test_a_duplicated_asset_id_is_reported_not_silently_halved(self) -> None:
        """Two rows for one id could mean two editions; picking the first guesses."""
        with TemporaryDirectory() as directory:
            books = BOOKS + (("SRC", "Bản một", "urn:uuid:different", 0.9),)
            library = self._library(Path(directory), books)
            with self.assertRaises(AmbiguousAsset):
                library.book("SRC")

    def test_a_book_outside_the_library_simply_has_no_annotations(self) -> None:
        """The SQL filter is what stops another book's rows from appearing."""
        with TemporaryDirectory() as directory:
            library = self._library(Path(directory), BOOKS)
            self.assertEqual(library.annotations("GHOST"), ())

    def test_a_plan_refuses_a_book_outside_the_library(self) -> None:
        with TemporaryDirectory() as directory:
            library = self._library(Path(directory), BOOKS)
            with self.assertRaises(UnknownAsset):
                build_transfer_plan(library, "SRC", "GHOST")

    def test_one_plan_reads_each_database_once(self) -> None:
        """Every extra copy is another window with the person's notes on disk."""
        with TemporaryDirectory() as directory:
            library = self._library(Path(directory), BOOKS)
            copies: list[str] = []
            original = AppleBooksLibrary._rows

            def spy(self, database, query, parameters=()):
                copies.append(Path(database).name)
                return original(self, database, query, parameters)

            AppleBooksLibrary._rows = spy
            self.addCleanup(setattr, AppleBooksLibrary, "_rows", original)
            build_transfer_plan(library, "SRC", "DST")

            self.assertEqual(len(copies), 2, copies)
            self.assertEqual(len(set(copies)), 2, "each database exactly once")


class AlreadyCarriedTests(unittest.TestCase):
    """The plan must know what is already on the other side.

    The writer skips those, so a plan that does not mark them promises work that
    will not happen.
    """

    @staticmethod
    def _library(root: Path, rows):
        return _paired_library(root, rows)

    def test_a_note_at_the_same_position_on_the_target_is_marked(self) -> None:
        carried = "epubcfi(/6/26[id220]!/4/64/4/1,:0,:119)"
        rows = ROWS + (("DST", 2, carried, "đoạn được bôi", "ghi chú", 0),)
        with TemporaryDirectory() as directory:
            plan = build_transfer_plan(self._library(Path(directory), rows), "SRC", "DST")
            verdicts = {
                item.annotation.location: item.verdict for item in plan.items
            }
            self.assertEqual(verdicts[carried], "already-there")
            self.assertEqual(len(plan.copyable), len(plan.items) - 1)

    def test_a_deleted_note_on_the_target_does_not_block_the_copy(self) -> None:
        """Someone deleted it in Apple Books; copying it again is the point."""

        carried = "epubcfi(/6/26[id220]!/4/64/4/1,:0,:119)"
        rows = ROWS + (("DST", 2, carried, "đoạn được bôi", None, 1),)
        with TemporaryDirectory() as directory:
            plan = build_transfer_plan(self._library(Path(directory), rows), "SRC", "DST")
            self.assertEqual(len(plan.copyable), len(plan.items))

    def test_nothing_is_marked_when_the_target_is_empty(self) -> None:
        with TemporaryDirectory() as directory:
            plan = build_transfer_plan(self._library(Path(directory), ROWS), "SRC", "DST")
            self.assertEqual(len(plan.copyable), len(plan.items))
            self.assertTrue(plan.items)

    def test_the_target_is_not_matched_by_position_across_books(self) -> None:
        """DST's own note sits at a CFI that SRC does not use; nothing to mark."""

        with TemporaryDirectory() as directory:
            plan = build_transfer_plan(self._library(Path(directory), ROWS), "SRC", "DST")
            self.assertNotIn("already-there", {item.verdict for item in plan.items})

    def test_both_books_come_out_of_one_read(self) -> None:
        with TemporaryDirectory() as directory:
            library = self._library(Path(directory), ROWS)
            copies: list[str] = []
            original = AppleBooksLibrary._rows

            def spy(self, database, query, parameters=()):
                copies.append(Path(database).name)
                return original(self, database, query, parameters)

            AppleBooksLibrary._rows = spy
            self.addCleanup(setattr, AppleBooksLibrary, "_rows", original)
            build_transfer_plan(library, "SRC", "DST")

            self.assertEqual(len(copies), 2, copies)
            self.assertEqual(len(set(copies)), 2, "each database exactly once")


class ChapterDiffersTests(unittest.TestCase):
    """The failure this whole check exists for.

    A real library held two files with the same ZEPUBID, the same 28-item spine
    and the same chapter filenames, where one chapter carried four extra images.
    Notes copied into it listed correctly in the sidebar and highlighted nothing
    on the page. A shared edition id had been treated as proof they matched.
    """

    # ROWS puts two annotations in spine 12 and one in spine 18.
    SPINE_OF_TWO = 12
    SPINE_OF_ONE = 18

    def test_a_shared_edition_id_is_not_enough_to_copy(self) -> None:
        with TemporaryDirectory() as directory:
            library = _paired_library(Path(directory), differs_at=self.SPINE_OF_ONE)
            plan = build_transfer_plan(library, "SRC", "DST")
            self.assertTrue(plan.same_edition, "the edition ids do still match")
            self.assertEqual(len(plan.copyable), 2, "copied into a differing chapter")
            self.assertEqual(
                [item.verdict for item in plan.items].count("needs-review"), 1
            )

    def test_notes_in_chapters_that_match_are_still_offered(self) -> None:
        """One bad chapter must not condemn the whole book."""

        with TemporaryDirectory() as directory:
            library = _paired_library(Path(directory), differs_at=self.SPINE_OF_ONE)
            plan = build_transfer_plan(library, "SRC", "DST")
            spines = {
                item.annotation.location.split("!")[0]
                for item in plan.copyable
            }
            self.assertEqual(spines, {"epubcfi(/6/26[id220]"})

    def test_a_differing_chapter_with_the_notes_in_it_leaves_nothing_to_copy(self) -> None:
        with TemporaryDirectory() as directory:
            library = _paired_library(Path(directory), differs_at=self.SPINE_OF_TWO)
            plan = build_transfer_plan(library, "SRC", "DST")
            self.assertEqual(len(plan.copyable), 1)

    def test_a_book_file_that_is_missing_vouches_for_nothing(self) -> None:
        """No file, no evidence - and no evidence means no copy."""

        with TemporaryDirectory() as directory:
            root = Path(directory)
            library = AppleBooksLibrary(
                library_database=_make_library(root, BOOKS),
                annotation_database=_make_annotations(root, ROWS),
            )
            plan = build_transfer_plan(library, "SRC", "DST")
            self.assertEqual(plan.copyable, ())
            self.assertTrue(all(i.verdict == "needs-review" for i in plan.items))

    def test_an_unreadable_book_file_vouches_for_nothing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            broken = root / "broken.epub"
            broken.write_bytes(b"not an epub at all")
            books = tuple(
                book + (str(broken),) if book[0] in ("SRC", "DST") else book
                for book in BOOKS
            )
            library = AppleBooksLibrary(
                library_database=_make_library(root, books),
                annotation_database=_make_annotations(root, ROWS),
            )
            self.assertEqual(build_transfer_plan(library, "SRC", "DST").copyable, ())


class HighlightColourTests(unittest.TestCase):
    """The colour Apple Books drew the highlight in.

    1 green, 2 blue, 3 yellow, 4 pink, 5 purple; 0 is not a colour. The map
    is not this project's invention - two independent readers of the same
    database agree on it - but the numbers still have to arrive intact.
    """

    def test_each_highlight_carries_the_colour_books_drew_it_in(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _make_annotations_with_colour(root, (
                ("BOOK", 2, "cfi-1", "lục", None, 0, 1),
                ("BOOK", 2, "cfi-2", "lam", None, 0, 2),
                ("BOOK", 2, "cfi-3", "vàng", None, 0, 3),
                ("BOOK", 2, "cfi-4", "hồng", None, 0, 4),
                ("BOOK", 2, "cfi-5", "tím", None, 0, 5),
            ))
            library = AppleBooksLibrary(annotation_database=database)
            styles = {
                annotation.selected_text: annotation.style
                for annotation in library.annotations("BOOK")
            }
            self.assertEqual(
                styles,
                {"lục": 1, "lam": 2, "vàng": 3, "hồng": 4, "tím": 5},
            )

    def test_a_schema_without_the_colour_still_reads_every_highlight(self) -> None:
        # Books' schema follows whatever version wrote it. A missing column
        # must cost the colour, not the annotations.
        with TemporaryDirectory() as directory:
            database = _make_annotations(Path(directory), (
                ("BOOK", 2, "cfi-1", "không màu", None, 0),
            ))
            library = AppleBooksLibrary(annotation_database=database)
            found = library.annotations("BOOK")
            self.assertEqual([a.selected_text for a in found], ["không màu"])
            self.assertEqual([a.style for a in found], [0])
