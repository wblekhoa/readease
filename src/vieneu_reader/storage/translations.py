"""A book's translations, kept on this Mac (RE-PLAY-032).

The host translates (Apple, ReadEase's own translator, a local server); the
engine keeps what came back, paragraph by paragraph, so a chapter read a
second time - or shown beside the original - is never translated again.
Its own file, like the History: no migration of the library database, and
removing a book removes its translations with it.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import threading
import time

TARGETS = ("vi", "en")


class TranslationStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not self.path.exists()
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        if fresh or (os.stat(self.path).st_mode & 0o077):
            os.chmod(self.path, 0o600)
        self._db.execute("PRAGMA secure_delete = ON")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS translations ("
            " book_id TEXT NOT NULL, segment_id TEXT NOT NULL, target TEXT NOT NULL,"
            " text TEXT NOT NULL, provider TEXT NOT NULL, at INTEGER NOT NULL,"
            " PRIMARY KEY (book_id, segment_id, target))"
        )
        self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def put(self, book_id: str, target: str, provider: str, items: dict[str, str], at: int | None = None) -> int:
        """Keep each paragraph's translation; a later one replaces it."""
        if target not in TARGETS:
            raise ValueError(f"unknown target: {target}")
        now = int(at if at is not None else time.time() * 1000)
        rows = [(book_id, str(sid), target, str(text).strip(), str(provider)[:40], now)
                for sid, text in items.items() if str(text).strip()]
        with self._lock:
            self._db.executemany(
                "INSERT INTO translations (book_id, segment_id, target, text, provider, at) VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (book_id, segment_id, target) DO UPDATE SET text = excluded.text,"
                " provider = excluded.provider, at = excluded.at",
                rows,
            )
            self._db.commit()
        return len(rows)

    def get(self, book_id: str, target: str, segment_ids: list[str] | None = None) -> dict[str, str]:
        with self._lock:
            if segment_ids is None:
                found = self._db.execute(
                    "SELECT segment_id, text FROM translations WHERE book_id = ? AND target = ?", (book_id, target)
                ).fetchall()
            else:
                found = []
                ids = list(segment_ids)
                for start in range(0, len(ids), 500):
                    chunk = ids[start:start + 500]
                    found += self._db.execute(
                        f"SELECT segment_id, text FROM translations WHERE book_id = ? AND target = ?"
                        f" AND segment_id IN ({','.join('?' * len(chunk))})", (book_id, target, *chunk)
                    ).fetchall()
        return {segment_id: text for segment_id, text in found}

    def delete(self, book_id: str, target: str | None = None, segment_ids: list[str] | None = None) -> int:
        clauses, values = ["book_id = ?"], [book_id]
        if target is not None:
            clauses.append("target = ?"); values.append(target)
        with self._lock:
            if segment_ids is not None:
                deleted = 0
                for start in range(0, len(segment_ids), 500):
                    chunk = segment_ids[start:start + 500]
                    deleted += self._db.execute(
                        f"DELETE FROM translations WHERE {' AND '.join(clauses)} AND segment_id IN ({','.join('?' * len(chunk))})",
                        (*values, *chunk),
                    ).rowcount
            else:
                deleted = self._db.execute(f"DELETE FROM translations WHERE {' AND '.join(clauses)}", values).rowcount
            self._db.commit()
        return deleted
