from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.integrations.apple_books_writer import (
    AppleBooksBusy,
    BackupMissing,
    NothingToCopy,
    back_up,
    copy_annotations,
    prune_backups,
    restore,
)

# A cut-down shape of the real table, keeping one ZFUTUREPROOFING column because
# carrying those across untouched is the whole reason this clones rows.
_COLUMNS = (
    "Z_PK INTEGER PRIMARY KEY",
    "Z_ENT INTEGER",
    "Z_OPT INTEGER",
    "ZANNOTATIONDELETED INTEGER",
    "ZANNOTATIONTYPE INTEGER",
    "ZANNOTATIONASSETID TEXT",
    "ZANNOTATIONUUID TEXT",
    "ZPLSTORAGEUUID TEXT",
    "ZANNOTATIONLOCATION TEXT",
    "ZANNOTATIONSELECTEDTEXT TEXT",
    "ZANNOTATIONNOTE TEXT",
    "ZANNOTATIONCREATIONDATE TIMESTAMP",
    "ZANNOTATIONMODIFICATIONDATE TIMESTAMP",
    "ZFUTUREPROOFING11 TEXT",
)


def _database(root: Path, *, count: int = 3) -> Path:
    path = root / "AEAnnotation_v1.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(f"CREATE TABLE ZAEANNOTATION ({', '.join(_COLUMNS)})")
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER, Z_NAME TEXT, Z_MAX INTEGER)"
    )
    connection.execute(
        "INSERT INTO Z_PRIMARYKEY VALUES (1, 'AEAnnotation', ?)", (count,)
    )
    for number in range(1, count + 1):
        connection.execute(
            "INSERT INTO ZAEANNOTATION VALUES"
            " (?, 1, 1, 0, 2, 'SRC', ?, ?, ?, ?, ?, 700.0, 700.0, 'carry-me')",
            (
                number,
                f"uuid-{number}",
                f"storage-{number}",
                f"epubcfi(/6/26!/4/{number})",
                f"doan {number}",
                f"ghi chu {number}",
            ),
        )
    connection.commit()
    connection.close()
    return path


def _annotations(path: Path, asset: str) -> list[tuple]:
    connection = sqlite3.connect(path)
    try:
        return connection.execute(
            "SELECT Z_PK, ZANNOTATIONUUID, ZPLSTORAGEUUID, ZANNOTATIONLOCATION,"
            " ZANNOTATIONNOTE, ZFUTUREPROOFING11, ZANNOTATIONCREATIONDATE"
            " FROM ZAEANNOTATION WHERE ZANNOTATIONASSETID = ?"
            " AND ZANNOTATIONDELETED = 0 ORDER BY Z_PK",
            (asset,),
        ).fetchall()
    finally:
        connection.close()


def _bookkeeping(path: Path) -> tuple[int, int]:
    connection = sqlite3.connect(path)
    try:
        declared = connection.execute(
            "SELECT Z_MAX FROM Z_PRIMARYKEY WHERE Z_NAME = 'AEAnnotation'"
        ).fetchone()[0]
        highest = connection.execute(
            "SELECT MAX(Z_PK) FROM ZAEANNOTATION"
        ).fetchone()[0]
        return int(declared), int(highest)
    finally:
        connection.close()


def _quiet() -> bool:
    return False


class BackupTests(unittest.TestCase):
    def test_a_backup_captures_the_database_and_its_sidecars(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            database.with_name(database.name + "-wal").write_bytes(b"log")
            saved = back_up(database, root / "backup")
            self.assertTrue((saved / database.name).is_file())
            self.assertTrue((saved / (database.name + "-wal")).is_file())

    def test_restoring_undoes_a_write_completely(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            before = _annotations(database, "SRC")
            saved = back_up(database, root / "backup")

            copy_annotations(
                database, "SRC", "DST", backup=saved, books_is_running=_quiet
            )
            self.assertEqual(len(_annotations(database, "DST")), 3)

            restore(database, saved)

            self.assertEqual(_annotations(database, "DST"), [])
            self.assertEqual(_annotations(database, "SRC"), before)


class RefusalTests(unittest.TestCase):
    def test_nothing_is_written_without_a_backup(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            with self.assertRaises(BackupMissing):
                copy_annotations(
                    database, "SRC", "DST", backup=None, books_is_running=_quiet
                )
            self.assertEqual(_annotations(database, "DST"), [])

    def test_nothing_is_written_while_apple_books_is_running(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            with self.assertRaises(AppleBooksBusy):
                copy_annotations(
                    database, "SRC", "DST", backup=saved, books_is_running=lambda: True
                )
            self.assertEqual(_annotations(database, "DST"), [])

    def test_a_book_with_nothing_to_copy_says_so_and_writes_nothing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            with self.assertRaises(NothingToCopy):
                copy_annotations(
                    database, "EMPTY", "DST", backup=saved, books_is_running=_quiet
                )
            self.assertEqual(_bookkeeping(database), (3, 3))


class CopyTests(unittest.TestCase):
    def _copied(self, root: Path, **kwargs) -> tuple[Path, int]:
        database = _database(root)
        saved = back_up(database, root / "backup")
        written = copy_annotations(
            database, "SRC", "DST", backup=saved, books_is_running=_quiet, **kwargs
        )
        return database, written

    def test_the_position_is_carried_across_unchanged(self) -> None:
        """The CFI is what decides which sentence the note lands on."""
        with TemporaryDirectory() as directory:
            database, written = self._copied(Path(directory))
            self.assertEqual(written, 3)
            source = _annotations(database, "SRC")
            target = _annotations(database, "DST")
            self.assertEqual([row[3] for row in target], [row[3] for row in source])
            self.assertEqual([row[4] for row in target], [row[4] for row in source])

    def test_undocumented_columns_are_carried_rather_than_guessed(self) -> None:
        with TemporaryDirectory() as directory:
            database, _ = self._copied(Path(directory))
            self.assertEqual(
                [row[5] for row in _annotations(database, "DST")],
                ["carry-me"] * 3,
            )

    def test_the_source_book_is_left_exactly_as_it_was(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            before = _annotations(database, "SRC")
            saved = back_up(database, root / "backup")
            copy_annotations(
                database, "SRC", "DST", backup=saved, books_is_running=_quiet
            )
            self.assertEqual(_annotations(database, "SRC"), before)

    def test_every_copy_gets_its_own_identity(self) -> None:
        """A shared uuid would make iCloud treat the copy as an edit of the original."""
        with TemporaryDirectory() as directory:
            database, _ = self._copied(Path(directory))
            rows = _annotations(database, "SRC") + _annotations(database, "DST")
            self.assertEqual(len({row[0] for row in rows}), 6)
            self.assertEqual(len({row[1] for row in rows}), 6)
            self.assertEqual(len({row[2] for row in rows}), 6)

    def test_the_copy_is_stamped_now_not_when_the_original_was_made(self) -> None:
        with TemporaryDirectory() as directory:
            database, _ = self._copied(Path(directory))
            self.assertTrue(
                all(row[6] > 700.0 for row in _annotations(database, "DST"))
            )

    def test_apple_books_can_still_allocate_after_us(self) -> None:
        """Leaving Z_MAX behind makes Apple Books collide on its next annotation."""
        with TemporaryDirectory() as directory:
            database, _ = self._copied(Path(directory))
            declared, highest = _bookkeeping(database)
            self.assertGreaterEqual(declared, highest)

    def test_a_pilot_writes_only_what_it_was_asked_for(self) -> None:
        with TemporaryDirectory() as directory:
            database, written = self._copied(Path(directory), limit=1)
            self.assertEqual(written, 1)
            self.assertEqual(len(_annotations(database, "DST")), 1)
            declared, highest = _bookkeeping(database)
            self.assertGreaterEqual(declared, highest)

    def test_the_same_book_twice_is_refused_before_anything_opens(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            with self.assertRaises(ValueError):
                copy_annotations(
                    database, "SRC", "SRC", backup=saved, books_is_running=_quiet
                )
            self.assertEqual(_bookkeeping(database), (3, 3))

    def test_a_failure_part_way_through_leaves_no_half_written_book(self) -> None:
        """The second clone collides, so the first one must not survive either."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            # Z_MAX says 3, so the clones take 4 then 5 - and 5 is already taken.
            connection = sqlite3.connect(database)
            connection.execute(
                "INSERT INTO ZAEANNOTATION VALUES"
                " (5, 1, 1, 0, 2, 'DST', 'squatter', 'squatter-storage',"
                " 'epubcfi(/6/26!/4/9)', 'co san', NULL, 700.0, 700.0, 'carry-me')"
            )
            connection.commit()
            connection.close()
            saved = back_up(database, root / "backup")

            with self.assertRaises(sqlite3.IntegrityError):
                copy_annotations(
                    database, "SRC", "DST", backup=saved, books_is_running=_quiet
                )

            surviving = _annotations(database, "DST")
            self.assertEqual([row[1] for row in surviving], ["squatter"])
            self.assertEqual(
                _bookkeeping(database)[0], 3, "Z_MAX moved despite the rollback"
            )


if __name__ == "__main__":
    unittest.main()


class RepeatTests(unittest.TestCase):
    """Pressing copy twice must not duplicate the book's notes.

    This is not hypothetical: it happened on a real library on 2026-08-28,
    leaving four duplicated annotations that had to be cleaned up by hand.
    """

    def _copy(self, database: Path, backup: Path, **kwargs) -> int:
        return copy_annotations(
            database, "SRC", "DST", backup=backup, books_is_running=_quiet, **kwargs
        )

    def test_copying_twice_copies_nothing_the_second_time(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")

            self.assertEqual(self._copy(database, saved), 3)
            with self.assertRaises(NothingToCopy):
                self._copy(database, saved)
            self.assertEqual(len(_annotations(database, "DST")), 3)

    def test_only_the_notes_that_are_missing_are_copied(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")

            self.assertEqual(self._copy(database, saved, limit=1), 1)
            # The other two are still missing, so a full run brings exactly them.
            self.assertEqual(self._copy(database, saved), 2)

            positions = [row[3] for row in _annotations(database, "DST")]
            self.assertEqual(len(positions), len(set(positions)), positions)

    def test_a_note_the_reader_already_had_is_not_overwritten_or_repeated(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            connection = sqlite3.connect(database)
            connection.execute(
                "INSERT INTO ZAEANNOTATION VALUES"
                " (9, 1, 1, 0, 2, 'DST', 'mine', 'mine-storage',"
                " 'epubcfi(/6/26!/4/2)', 'cua toi', NULL, 700.0, 700.0, 'carry-me')"
            )
            connection.commit()
            connection.close()
            saved = back_up(database, root / "backup")

            # Source row 2 sits at that same position; it must be left alone.
            self.assertEqual(self._copy(database, saved), 2)

            rows = _annotations(database, "DST")
            self.assertEqual(len(rows), 3)
            mine = [row for row in rows if row[1] == "mine"]
            self.assertEqual(len(mine), 1, "the reader's own note was disturbed")


class OnlyLocationsTests(unittest.TestCase):
    """The last gate before somebody else's data is written.

    The plan decides which positions mean the same thing in the target book;
    this is how that decision reaches the write. Nothing else in the writer
    knows why a position might be unsafe, and it must not try to guess.
    """

    def _copy(self, database: Path, backup: Path, **kwargs) -> int:
        return copy_annotations(
            database, "SRC", "DST", backup=backup, books_is_running=_quiet, **kwargs
        )

    def test_only_the_named_positions_are_written(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            wanted = "epubcfi(/6/26!/4/2)"

            self.assertEqual(self._copy(database, saved, only_locations={wanted}), 1)

            rows = _annotations(database, "DST")
            self.assertEqual([row[3] for row in rows], [wanted])

    def test_an_empty_set_writes_nothing_rather_than_everything(self) -> None:
        """The dangerous reading of "no positions were vouched for"."""

        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")

            with self.assertRaises(NothingToCopy):
                self._copy(database, saved, only_locations=set())

            self.assertEqual(_annotations(database, "DST"), [])
            self.assertEqual(_bookkeeping(database), (3, 3))

    def test_omitting_it_copies_everything_as_before(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            self.assertEqual(self._copy(database, saved), 3)

    def test_a_position_that_is_not_in_the_source_is_simply_absent(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            with self.assertRaises(NothingToCopy):
                self._copy(database, saved, only_locations={"epubcfi(/6/99!/4/1)"})

    def test_it_narrows_the_copy_and_never_widens_it(self) -> None:
        """Naming a position already on the target must not resurrect it."""

        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            everything = {f"epubcfi(/6/26!/4/{n})" for n in range(1, 4)}

            self.assertEqual(self._copy(database, saved, only_locations=everything), 3)
            with self.assertRaises(NothingToCopy):
                self._copy(database, saved, only_locations=everything)
            self.assertEqual(len(_annotations(database, "DST")), 3)

    def test_a_frozenset_works_as_well_as_a_set(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = _database(root)
            saved = back_up(database, root / "backup")
            wanted = frozenset({"epubcfi(/6/26!/4/1)", "epubcfi(/6/26!/4/3)"})
            self.assertEqual(self._copy(database, saved, only_locations=wanted), 2)


class PruneBackupsTests(unittest.TestCase):
    """Backups are snapshots of someone's whole annotation database.

    Keeping a few is the point of taking them; keeping every one forever hoards
    the person's data on their own disk with nothing ever removing it.
    """

    def _saved(self, root: Path, names: tuple[str, ...]) -> Path:
        store = root / "backups"
        for name in names:
            (store / name).mkdir(parents=True)
            (store / name / "AEAnnotation_v1.sqlite").write_bytes(b"snapshot")
        return store

    def test_the_newest_are_kept_and_the_rest_go(self) -> None:
        with TemporaryDirectory() as directory:
            store = self._saved(
                Path(directory),
                tuple(f"2026-08-2{n}-120000" for n in range(1, 9)),
            )
            self.assertEqual(prune_backups(store, keep=3), 5)
            self.assertEqual(
                sorted(item.name for item in store.iterdir()),
                ["2026-08-26-120000", "2026-08-27-120000", "2026-08-28-120000"],
            )

    def test_age_is_read_from_the_name_not_the_filesystem(self) -> None:
        """A sync client or backup tool rewrites mtimes; the stamp is ours."""

        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = self._saved(root, ("2026-01-01-000000", "2026-08-28-120000"))
            # Make the *older* one look freshly touched.
            os.utime(store / "2026-01-01-000000", (2_000_000_000, 2_000_000_000))
            prune_backups(store, keep=1)
            self.assertEqual(
                [item.name for item in store.iterdir()], ["2026-08-28-120000"]
            )

    def test_fewer_than_the_limit_are_left_alone(self) -> None:
        with TemporaryDirectory() as directory:
            store = self._saved(Path(directory), ("2026-08-28-120000",))
            self.assertEqual(prune_backups(store, keep=5), 0)
            self.assertEqual(len(list(store.iterdir())), 1)

    def test_a_store_that_does_not_exist_yet_is_not_an_error(self) -> None:
        with TemporaryDirectory() as directory:
            self.assertEqual(prune_backups(Path(directory) / "never-made"), 0)

    def test_keeping_none_is_refused(self) -> None:
        """Pruning to zero would delete the backup for the copy just made."""

        with TemporaryDirectory() as directory:
            store = self._saved(Path(directory), ("2026-08-28-120000",))
            with self.assertRaises(ValueError):
                prune_backups(store, keep=0)
            self.assertEqual(len(list(store.iterdir())), 1)

    def test_loose_files_beside_the_backups_are_left_alone(self) -> None:
        with TemporaryDirectory() as directory:
            store = self._saved(
                Path(directory), ("2026-08-01-120000", "2026-08-28-120000")
            )
            (store / "README.txt").write_text("không phải bản sao lưu")
            prune_backups(store, keep=1)
            self.assertTrue((store / "README.txt").is_file())

    def test_a_store_it_cannot_read_is_left_alone_not_raised_over(self) -> None:
        """This runs after the copy has committed, inside a Qt slot.

        Qt swallows an exception raised there, so the person would see no result
        at all for a write that actually succeeded.
        """

        with TemporaryDirectory() as directory:
            store = self._saved(Path(directory), ("2026-08-28-120000",))
            os.chmod(store, 0o000)
            try:
                self.assertEqual(prune_backups(store, keep=1), 0)
            finally:
                # Restore before the temporary directory is torn down, or its
                # own cleanup cannot remove what it made.
                os.chmod(store, 0o700)
