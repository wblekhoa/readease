"""Paste and scan history kept on this Mac (RE-HIST-001…004).

A text the reader pasted and read, or a selection they scanned (with its
translation, when there was one), so it can be opened and read again after
the app quits. Owner's decision, 20/10: on by default and switchable off,
kept for a chosen number of days, text and translation only - never audio.

Its own file beside the library rather than a table in `reader.sqlite3`:
the library's schema moves one way and is backed up before a migrating
install, and none of that should hang on a list the reader can wipe in one
press. The file is the reader's alone (0600), and nothing here leaves it.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

KINDS = ("paste", "scan")
DAY_MS = 24 * 60 * 60 * 1000
#: Retention choices offered in Settings; 0 keeps everything until deleted.
RETENTION_DAYS = (7, 30, 90, 365, 0)
DEFAULT_RETENTION_DAYS = 30
LIST_LIMIT = 200


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    id: int
    kind: str
    text: str
    original: str | None
    target: str | None
    at: int  # unix milliseconds, when it was last read

    def as_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "text": self.text,
                "original": self.original, "target": self.target, "at": self.at}


def _tidy(text: str) -> str:
    return " ".join(str(text or "").split())


class HistoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not self.path.exists()
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        if fresh or (os.stat(self.path).st_mode & 0o077):
            os.chmod(self.path, 0o600)
        # A deleted entry is overwritten, not left in a free page for a disk
        # tool to read back.
        self._db.execute("PRAGMA secure_delete = ON")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS history ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " kind TEXT NOT NULL CHECK (kind IN ('paste', 'scan')),"
            " text TEXT NOT NULL,"
            " key TEXT NOT NULL,"
            " original TEXT,"
            " target TEXT,"
            " at INTEGER NOT NULL)"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS history_at ON history (at DESC)")
        self._db.execute("CREATE INDEX IF NOT EXISTS history_key ON history (kind, key)")
        self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def add(self, kind: str, text: str, *, original: str | None = None,
            target: str | None = None, at: int) -> HistoryEntry:
        """Keep one entry; the same words of the same kind move up instead
        of being kept twice (RE-HIST-002)."""
        if kind not in KINDS:
            raise ValueError(f"unknown history kind: {kind}")
        text = str(text or "").strip()
        key = _tidy(text)
        if not key:
            raise ValueError("empty text")
        original = (str(original).strip() or None) if original else None
        target = (str(target).strip() or None) if target else None
        with self._lock:
            row = self._db.execute(
                "SELECT id FROM history WHERE kind = ? AND key = ? AND COALESCE(original, '') = ?",
                (kind, key, _tidy(original or "")),
            ).fetchone()
            if row:
                self._db.execute("UPDATE history SET at = ?, text = ?, original = ?, target = ? WHERE id = ?",
                                 (int(at), text, original, target, row[0]))
                entry_id = row[0]
            else:
                entry_id = self._db.execute(
                    "INSERT INTO history (kind, text, key, original, target, at) VALUES (?, ?, ?, ?, ?, ?)",
                    (kind, text, key, original, target, int(at)),
                ).lastrowid
            self._db.commit()
        return HistoryEntry(int(entry_id), kind, text, original, target, int(at))

    def list(self, *, now: int, days: int, kind: str | None = None, limit: int = LIST_LIMIT) -> list[HistoryEntry]:
        """Newest first, after deleting what is past the retention (RE-HIST-003)."""
        self.purge(now=now, days=days)
        query = "SELECT id, kind, text, original, target, at FROM history"
        args: tuple = ()
        if kind is not None:
            query += " WHERE kind = ?"
            args = (kind,)
        query += " ORDER BY at DESC, id DESC LIMIT ?"
        with self._lock:
            rows = self._db.execute(query, args + (int(limit),)).fetchall()
        return [HistoryEntry(*row) for row in rows]

    def purge(self, *, now: int, days: int) -> int:
        if days <= 0:
            return 0
        with self._lock:
            removed = self._db.execute("DELETE FROM history WHERE at < ?", (int(now) - days * DAY_MS,)).rowcount
            self._db.commit()
        return removed

    def delete(self, entry_id: int) -> bool:
        with self._lock:
            removed = self._db.execute("DELETE FROM history WHERE id = ?", (int(entry_id),)).rowcount
            self._db.commit()
        return removed > 0

    def clear(self, kind: str | None = None) -> int:
        with self._lock:
            if kind is None:
                removed = self._db.execute("DELETE FROM history").rowcount
            else:
                removed = self._db.execute("DELETE FROM history WHERE kind = ?", (kind,)).rowcount
            self._db.commit()
            # Deleted means gone from the disk too, not only from the list.
            self._db.execute("VACUUM")
        return removed
