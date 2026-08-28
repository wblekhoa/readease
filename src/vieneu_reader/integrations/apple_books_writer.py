"""Copy annotations from one copy of a book to another, inside Apple Books.

This is the only part of ReadEase that writes to somebody else's database, and
Apple supports none of it, so every decision here is made in favour of being able
to undo.

The central choice is that a copied annotation is a **clone of the source row**
with five fields replaced, rather than a row built from scratch. Apple Books
stores six `ZFUTUREPROOFING*` columns whose meaning is not documented and which
every existing row on a real library uses; constructing a row would mean guessing
them, while cloning carries them across untouched.

What must change per copy:

* `Z_PK` - Core Data's primary key, taken from `Z_PRIMARYKEY.Z_MAX` and written
  back, because Apple Books allocates its next key from there and would collide
  with us otherwise.
* `ZANNOTATIONASSETID` - the book the annotation now belongs to.
* `ZANNOTATIONUUID` and `ZPLSTORAGEUUID` - identity, so iCloud treats the copy as
  a new annotation rather than a conflicting edit of the original.
* the creation and modification timestamps.

Everything else, including the EPUB CFI that decides which sentence the note
lands on, is carried verbatim. That only works because the two books share an
edition; `build_transfer_plan` is what establishes that, and this module refuses
to guess it for itself.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import subprocess
import uuid

_ENTITY = "AEAnnotation"
_SIDECARS = ("-wal", "-shm")
# Core Data timestamps count seconds from 2001-01-01 UTC, not from the epoch.
_APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


class AppleBooksBusy(RuntimeError):
    """Apple Books is running and would overwrite anything written now."""


class BackupMissing(RuntimeError):
    """No backup was taken, so a mistake could not be undone."""


class NothingToCopy(RuntimeError):
    """The source book has no annotations to copy."""


def apple_books_is_running() -> bool:
    """True when Apple Books holds the database open."""

    try:
        result = subprocess.run(
            ["/usr/bin/pgrep", "-x", "Books"],
            capture_output=True,
            check=False,
        )
    except OSError:
        # If we cannot tell, assume it is running: refusing to write costs a
        # retry, writing under Apple Books costs the annotations.
        return True
    return result.returncode == 0


def back_up(database: Path, destination: Path) -> Path:
    """Copy the database and its sidecars so the write can be undone."""

    source = Path(database).resolve()
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target / source.name)
    for suffix in _SIDECARS:
        sidecar = source.with_name(source.name + suffix)
        if sidecar.is_file():
            shutil.copy2(sidecar, target / sidecar.name)
    return target


def restore(database: Path, backup: Path) -> None:
    """Put a backup back, including its sidecars."""

    source = Path(database).resolve()
    saved = Path(backup) / source.name
    if not saved.is_file():
        raise BackupMissing(str(backup))
    shutil.copy2(saved, source)
    for suffix in _SIDECARS:
        sidecar = Path(backup) / (source.name + suffix)
        live = source.with_name(source.name + suffix)
        if sidecar.is_file():
            shutil.copy2(sidecar, live)
        elif live.is_file():
            live.unlink()


def _apple_timestamp(moment: datetime | None = None) -> float:
    return ((moment or datetime.now(timezone.utc)) - _APPLE_EPOCH).total_seconds()


def copy_annotations(
    database: Path,
    source_asset_id: str,
    target_asset_id: str,
    *,
    backup: Path | None,
    limit: int | None = None,
    books_is_running=apple_books_is_running,
    now: datetime | None = None,
) -> int:
    """Clone the source book's annotations onto the target book.

    Returns how many were written. `limit` exists so the first run can be a single
    annotation that a person checks in Apple Books before the rest follow.
    """

    if backup is None or not (Path(backup) / Path(database).resolve().name).is_file():
        raise BackupMissing(
            "Chưa có bản sao lưu, nên không thể hoàn tác nếu sai."
        )
    if books_is_running():
        raise AppleBooksBusy(
            "Apple Books đang mở. Hãy thoát Apple Books rồi thử lại."
        )
    if source_asset_id == target_asset_id:
        raise ValueError("source and target are the same book")

    path = Path(database).resolve()
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.execute("BEGIN IMMEDIATE")
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(ZAEANNOTATION)")
        ]
        rows = connection.execute(
            "SELECT * FROM ZAEANNOTATION WHERE ZANNOTATIONASSETID = ?"
            " AND ZANNOTATIONDELETED = 0 ORDER BY Z_PK",
            (source_asset_id,),
        ).fetchall()

        # Skip what is already there. Without this, copying twice duplicates
        # every annotation, which is what happens when someone presses the
        # button again after a first copy they were not sure had worked. The
        # position is the identity: two annotations at the same CFI in the same
        # book are the same annotation, whatever their row ids say.
        already_there = {
            location
            for (location,) in connection.execute(
                "SELECT ZANNOTATIONLOCATION FROM ZAEANNOTATION"
                " WHERE ZANNOTATIONASSETID = ? AND ZANNOTATIONDELETED = 0",
                (target_asset_id,),
            )
        }
        location_column = columns.index("ZANNOTATIONLOCATION")
        rows = [row for row in rows if row[location_column] not in already_there]

        if limit is not None:
            rows = rows[:limit]
        if not rows:
            connection.execute("ROLLBACK")
            raise NothingToCopy(source_asset_id)

        next_key = connection.execute(
            "SELECT Z_MAX FROM Z_PRIMARYKEY WHERE Z_NAME = ?", (_ENTITY,)
        ).fetchone()
        if next_key is None:
            connection.execute("ROLLBACK")
            raise RuntimeError("Apple Books bookkeeping row is missing")
        highest = int(next_key[0])

        stamp = _apple_timestamp(now)
        placeholders = ", ".join("?" for _ in columns)
        index = {name: position for position, name in enumerate(columns)}
        written = 0
        for row in rows:
            clone = list(row)
            highest += 1
            clone[index["Z_PK"]] = highest
            clone[index["ZANNOTATIONASSETID"]] = target_asset_id
            for column in ("ZANNOTATIONUUID", "ZPLSTORAGEUUID"):
                if column in index and clone[index[column]] is not None:
                    clone[index[column]] = str(uuid.uuid4()).upper()
            for column in (
                "ZANNOTATIONCREATIONDATE",
                "ZANNOTATIONMODIFICATIONDATE",
            ):
                if column in index:
                    clone[index[column]] = stamp
            connection.execute(
                f"INSERT INTO ZAEANNOTATION ({', '.join(columns)})"
                f" VALUES ({placeholders})",
                clone,
            )
            written += 1

        # Apple Books allocates its next key from here; leaving it behind would
        # make its own next annotation collide with one of ours.
        connection.execute(
            "UPDATE Z_PRIMARYKEY SET Z_MAX = ? WHERE Z_NAME = ?", (highest, _ENTITY)
        )
        connection.execute("COMMIT")
        return written
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        connection.close()
