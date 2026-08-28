"""Read-only view of the Apple Books library and its annotations.

Apple Books keeps its own SQLite databases and gives no supported API for them, so
everything here is deliberately one-way: this module copies the files it needs and
reads the copy. The originals are never opened for writing, and nothing in ReadEase
writes an annotation back.

Two details cost real debugging time and are load-bearing:

* Books runs with write-ahead logging, so the `.sqlite` file alone is stale. Reading
  it without its `-wal` sidecar silently omitted a whole book that the person could
  see in Books at that moment. Every copy takes the sidecars too.
* An annotation row survives deletion with `ZANNOTATIONDELETED = 1`. Counting rows
  without that filter reports notes the person already threw away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import sqlite3
import tempfile

_LIBRARY_CONTAINER = (
    Path.home()
    / "Library"
    / "Containers"
    / "com.apple.iBooksX"
    / "Data"
    / "Documents"
)
_LIBRARY_GLOB = ("BKLibrary", "BKLibrary*.sqlite")
_ANNOTATION_GLOB = ("AEAnnotation", "AEAnnotation*.sqlite")
_SIDECARS = ("-wal", "-shm")


class AppleBooksUnavailable(RuntimeError):
    """Apple Books stores nothing at the expected location on this Mac."""


class AppleBooksUnreadable(RuntimeError):
    """The databases exist but could not be read as Apple Books data."""


class UnknownAsset(LookupError):
    """The requested book is not in the Apple Books library."""


@dataclass(frozen=True, slots=True)
class Book:
    asset_id: str
    title: str
    edition_id: str
    reading_progress: float


@dataclass(frozen=True, slots=True)
class Annotation:
    asset_id: str
    kind: int
    location: str
    # Excluded from repr on purpose: these carry the person's own words, and a
    # default dataclass repr would put them into any traceback or %r log line.
    selected_text: str | None = field(repr=False, default=None)
    note: str | None = field(repr=False, default=None)

    @property
    def has_note(self) -> bool:
        return bool(self.note)


@dataclass(frozen=True, slots=True)
class TransferItem:
    """One annotation and what moving it would mean.

    `verdict` is a stable token, not a sentence: the wording belongs to whichever
    surface renders it, so this module stays free of display copy and of the
    localisation that copy would drag in.
    """

    annotation: Annotation
    verdict: str


@dataclass(frozen=True, slots=True)
class TransferPlan:
    source: Book
    target: Book
    items: tuple[TransferItem, ...]

    @property
    def same_edition(self) -> bool:
        return bool(self.source.edition_id) and (
            self.source.edition_id == self.target.edition_id
        )


def _newest(directory: Path, pattern: str) -> Path | None:
    """Most recently written match - lexicographic order puts -9 after -10."""

    candidates = sorted(
        (path for path in directory.glob(pattern) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def default_library_database() -> Path | None:
    return _newest(_LIBRARY_CONTAINER / _LIBRARY_GLOB[0], _LIBRARY_GLOB[1])


def default_annotation_database() -> Path | None:
    return _newest(_LIBRARY_CONTAINER / _ANNOTATION_GLOB[0], _ANNOTATION_GLOB[1])


class AppleBooksLibrary:
    def __init__(
        self,
        library_database: Path | None = None,
        annotation_database: Path | None = None,
    ) -> None:
        self._library = library_database or default_library_database()
        self._annotations = annotation_database or default_annotation_database()

    def _rows(self, database: Path | None, query: str) -> list[tuple]:
        if database is None or not Path(database).is_file():
            raise AppleBooksUnavailable(
                "Không tìm thấy dữ liệu Apple Books trên máy này."
            )
        # Resolve first: a symlinked database would otherwise have its sidecars
        # looked up beside the link, silently returning a stale read - the exact
        # omission this module exists to avoid.
        source = Path(database).resolve()
        with tempfile.TemporaryDirectory() as scratch:
            copy = Path(scratch) / source.name
            try:
                shutil.copy2(source, copy)
                for suffix in _SIDECARS:
                    sidecar = source.with_name(source.name + suffix)
                    try:
                        shutil.copy2(sidecar, copy.with_name(copy.name + suffix))
                    except FileNotFoundError:
                        # Books removes the log on a clean quit. Missing is normal;
                        # unreadable is not, and falls through to the handler below.
                        continue
            except OSError as error:
                raise AppleBooksUnreadable(
                    "Không đọc được dữ liệu Apple Books. Hãy thử lại sau."
                ) from error
            try:
                connection = sqlite3.connect(copy)
                try:
                    return connection.execute(query).fetchall()
                finally:
                    connection.close()
            except sqlite3.Error as error:
                raise AppleBooksUnreadable(
                    "Không đọc được dữ liệu Apple Books. Hãy thử lại sau."
                ) from error

    def books(self) -> tuple[Book, ...]:
        rows = self._rows(
            self._library,
            "SELECT ZASSETID, ZTITLE, ZEPUBID, ZREADINGPROGRESS "
            "FROM ZBKLIBRARYASSET WHERE ZASSETID IS NOT NULL",
        )
        return tuple(
            Book(
                asset_id=str(asset_id),
                title=str(title or ""),
                edition_id=str(edition_id or ""),
                reading_progress=float(progress or 0.0),
            )
            for asset_id, title, edition_id, progress in rows
        )

    def book(self, asset_id: str) -> Book:
        for candidate in self.books():
            if candidate.asset_id == asset_id:
                return candidate
        raise UnknownAsset(asset_id)

    def annotations(self, asset_id: str) -> tuple[Annotation, ...]:
        rows = self._rows(
            self._annotations,
            "SELECT ZANNOTATIONASSETID, ZANNOTATIONTYPE, ZANNOTATIONLOCATION, "
            "ZANNOTATIONSELECTEDTEXT, ZANNOTATIONNOTE FROM ZAEANNOTATION "
            "WHERE ZANNOTATIONDELETED = 0 AND ZANNOTATIONASSETID IS NOT NULL",
        )
        return tuple(
            Annotation(
                asset_id=str(row[0]),
                kind=int(row[1] or 0),
                location=str(row[2] or ""),
                selected_text=row[3],
                note=row[4],
            )
            for row in rows
            if str(row[0]) == asset_id
        )


def build_transfer_plan(
    library: AppleBooksLibrary,
    source_asset_id: str,
    target_asset_id: str,
) -> TransferPlan:
    """Describe what moving the source book's annotations would mean.

    Nothing is written. The verdict is deliberately conservative: two copies of the
    same EPUB share an edition id, and their CFI paths address the same spine, so
    those transfer as-is. Anything else is flagged for a person to look at, because a
    character offset into one edition means nothing in another.
    """

    source = library.book(source_asset_id)
    target = library.book(target_asset_id)
    same_edition = bool(source.edition_id) and source.edition_id == target.edition_id
    verdict = "same-edition" if same_edition else "needs-review"
    items = [
        TransferItem(annotation=annotation, verdict=verdict)
        for annotation in library.annotations(source_asset_id)
    ]
    return TransferPlan(source=source, target=target, items=tuple(items))
