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


class AppleBooksNotPermitted(RuntimeError):
    """macOS has not granted access to the Apple Books folder."""


class UnknownAsset(LookupError):
    """The requested book is not in the Apple Books library."""


class AmbiguousAsset(LookupError):
    """One asset id names more than one row, so a choice cannot be made safely."""


class SameBook(ValueError):
    """Source and target are the same book; there is nothing to compare."""


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


def _as_float(value: object) -> float:
    """Apple's schema is undocumented; a surprising value must not crash a slot."""

    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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
        # Kept unresolved: locating the defaults means listing the person's Books
        # container, which must not happen for someone who never opens the tab.
        self._library_override = library_database
        self._annotation_override = annotation_database

    @property
    def _library(self) -> Path | None:
        return self._library_override or default_library_database()

    @property
    def _annotations(self) -> Path | None:
        return self._annotation_override or default_annotation_database()

    @property
    def annotation_database(self) -> Path | None:
        """Where the annotations live, for the one caller that writes to them.

        Resolving this still touches the Books container, so it stays lazy like
        everything else here.
        """

        return self._annotations

    def _rows(
        self,
        database: Path | None,
        query: str,
        parameters: tuple = (),
    ) -> list[tuple]:
        if database is None:
            raise AppleBooksUnavailable(
                "Không tìm thấy dữ liệu Apple Books trên máy này."
            )
        try:
            present = Path(database).is_file()
        except PermissionError as error:
            raise AppleBooksNotPermitted(
                "ReadEase chưa được phép đọc thư mục Apple Books."
            ) from error
        if not present:
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
            except PermissionError as error:
                raise AppleBooksNotPermitted(
                    "ReadEase chưa được phép đọc thư mục Apple Books."
                ) from error
            except OSError as error:
                raise AppleBooksUnreadable(
                    "Không đọc được dữ liệu Apple Books. Hãy thử lại sau."
                ) from error
            try:
                connection = sqlite3.connect(copy)
                try:
                    return connection.execute(query, parameters).fetchall()
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
                reading_progress=_as_float(progress),
            )
            for asset_id, title, edition_id, progress in rows
        )

    def book(self, asset_id: str) -> Book:
        return select_book(self.books(), asset_id)

    def annotations(self, asset_id: str) -> tuple[Annotation, ...]:
        """Annotations stored against this asset id.

        A book that is not in the library simply has none, because the filter is
        bound in SQL - so this needs no library read of its own, and callers that
        must reject an unknown book do that where they already hold the listing.
        """

        rows = self._rows(
            self._annotations,
            # Bound in SQL, not filtered afterwards: reading every book's notes
            # into memory to show one book's would make the privacy note false.
            "SELECT ZANNOTATIONASSETID, ZANNOTATIONTYPE, ZANNOTATIONLOCATION, "
            "ZANNOTATIONSELECTEDTEXT, ZANNOTATIONNOTE FROM ZAEANNOTATION "
            "WHERE ZANNOTATIONDELETED = 0 AND ZANNOTATIONASSETID = ?",
            (asset_id,),
        )
        return tuple(
            Annotation(
                asset_id=str(row[0]),
                kind=_as_int(row[1]),
                location=str(row[2] or ""),
                selected_text=row[3],
                note=row[4],
            )
            for row in rows
        )


def select_book(books: tuple[Book, ...], asset_id: str) -> Book:
    """Find one book by id, refusing to guess when the id is not unique."""

    matches = [book for book in books if book.asset_id == asset_id]
    if not matches:
        raise UnknownAsset(asset_id)
    if len(matches) > 1 and len({book.edition_id for book in matches}) > 1:
        # Same id, different editions: choosing one would settle the verdict by
        # row order, which is not a decision this module may make.
        raise AmbiguousAsset(asset_id)
    return matches[0]


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

    if source_asset_id == target_asset_id:
        raise SameBook(source_asset_id)
    # One listing serves both lookups: each extra read copies the person's data
    # to disk again for no gain.
    books = library.books()
    source = select_book(books, source_asset_id)
    target = select_book(books, target_asset_id)
    same_edition = bool(source.edition_id) and source.edition_id == target.edition_id
    verdict = "same-edition" if same_edition else "needs-review"
    items = [
        TransferItem(annotation=annotation, verdict=verdict)
        for annotation in library.annotations(source_asset_id)
    ]
    return TransferPlan(source=source, target=target, items=tuple(items))
