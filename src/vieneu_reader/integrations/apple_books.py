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
from typing import Callable
import tempfile

from vieneu_reader.integrations.epub_layout import (
    Layout,
    UnreadableBook,
    carries_over,
    read_layout,
)

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
    # Where the book itself sits. Two copies can share an edition id and still
    # differ in content, and only the files can settle that.
    path: str = ""


@dataclass(frozen=True, slots=True)
class Annotation:
    asset_id: str
    kind: int
    location: str
    # Excluded from repr on purpose: these carry the person's own words, and a
    # default dataclass repr would put them into any traceback or %r log line.
    selected_text: str | None = field(repr=False, default=None)
    note: str | None = field(repr=False, default=None)
    # Apple's highlight colour (1 green, 3 yellow, 5 purple...). Not read
    # yet - ReadEase paints one tint - so it is always 0 for now.
    style: int = 0

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

    @property
    def copyable(self) -> tuple["TransferItem", ...]:
        """The items a copy would actually write - what the count should mean.

        Only positions proven to mean the same thing in the target book. A note
        whose chapter differs stays listed and is never written: it would look
        like it worked and highlight the wrong words, or nothing at all.
        """

        return tuple(item for item in self.items if item.verdict == "same-edition")


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
        query: str | Callable[[sqlite3.Connection], str],
        parameters: tuple = (),
    ) -> list[tuple]:
        """One copy, one query - and EVERY annotation read comes through here.

        `query` may be a callable given the open connection, for a query whose
        columns depend on the schema in front of it. It stays a parameter of
        this method rather than a separate path around it: the read-scope
        guards watch this seam, and a second way in would be a way past them.
        """

        def read(connection):
            statement = query(connection) if callable(query) else query
            return connection.execute(statement, parameters).fetchall()

        return self._with_copy(database, read)

    @staticmethod
    def _has_column(connection, table: str, column: str) -> bool:
        """Whether this copy of Apple Books' schema carries a column.

        Asked rather than assumed, because this is somebody else's database:
        its shape follows whatever version of Books wrote it, and a column
        that is missing must cost one field, not every annotation. A plain
        SELECT of an absent column fails the whole read.
        """

        return any(
            str(row[1]) == column
            for row in connection.execute(f"PRAGMA table_info({table})")
        )

    def _with_copy(self, database: Path | None, read) -> list[tuple]:
        """Copy the database (and its sidecars) once, run `read` on the copy.

        One copy per call, whatever `read` asks of it: every extra copy is
        another window with the person's notes on disk."""

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
                    return read(connection)
                finally:
                    connection.close()
            except sqlite3.Error as error:
                raise AppleBooksUnreadable(
                    "Không đọc được dữ liệu Apple Books. Hãy thử lại sau."
                ) from error

    def books(self) -> tuple[Book, ...]:
        rows = self._rows(
            self._library,
            "SELECT ZASSETID, ZTITLE, ZEPUBID, ZREADINGPROGRESS, ZPATH "
            "FROM ZBKLIBRARYASSET WHERE ZASSETID IS NOT NULL",
        )
        return tuple(
            Book(
                asset_id=str(asset_id),
                title=str(title or ""),
                edition_id=str(edition_id or ""),
                reading_progress=_as_float(progress),
                path=str(path or ""),
            )
            for asset_id, title, edition_id, progress, path in rows
        )

    def book(self, asset_id: str) -> Book:
        return select_book(self.books(), asset_id)

    def annotations(self, asset_id: str) -> tuple[Annotation, ...]:
        """Annotations stored against this asset id.

        A book that is not in the library simply has none, because the filter is
        bound in SQL - so this needs no library read of its own, and callers that
        must reject an unknown book do that where they already hold the listing.
        """

        return self.annotations_for(asset_id).get(asset_id, ())

    def annotations_for(
        self, *asset_ids: str
    ) -> dict[str, tuple[Annotation, ...]]:
        """Annotations for several books, grouped by book, in one read.

        Two books need comparing to say which notes are already on the other
        side. Asking twice would copy the database to disk twice, so the ids are
        bound into a single query instead.
        """

        if not asset_ids:
            return {}

        def query(connection) -> str:
            # The colour is appended only when this schema carries it, so the
            # row reader's `len(row) > 5` guard is what decides, not a hope.
            colour = (
                ", ZANNOTATIONSTYLE"
                if self._has_column(connection, "ZAEANNOTATION", "ZANNOTATIONSTYLE")
                else ""
            )
            return (
                "SELECT ZANNOTATIONASSETID, ZANNOTATIONTYPE, ZANNOTATIONLOCATION, "
                f"ZANNOTATIONSELECTEDTEXT, ZANNOTATIONNOTE{colour} "
                "FROM ZAEANNOTATION "
                "WHERE ZANNOTATIONDELETED = 0 AND ZANNOTATIONASSETID IN "
                f"({', '.join('?' for _ in asset_ids)})"
            )

        # Bound in SQL, not filtered afterwards: reading every book's notes
        # into memory to show one book's would make the privacy note false.
        rows = self._rows(self._annotations, query, tuple(asset_ids))
        grouped: dict[str, list[Annotation]] = {key: [] for key in asset_ids}
        for row in rows:
            asset_id = str(row[0])
            grouped.setdefault(asset_id, []).append(
                Annotation(
                    asset_id=asset_id,
                    kind=_as_int(row[1]),
                    location=str(row[2] or ""),
                    selected_text=row[3],
                    note=row[4],
                    # 1 green · 2 blue · 3 yellow · 4 pink · 5 purple.
                    # 0 means "no colour": Books gives it to underlines and
                    # to reading bookmarks. Corroborated by two independent
                    # readers of this database (py-apple-books'
                    # AnnotationColor, and the apple-books-annotation-import
                    # plugin), which agree exactly.
                    style=_as_int(row[5]) if len(row) > 5 else 0,
                )
            )
        return {key: tuple(value) for key, value in grouped.items()}


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


def _layouts(source: Book, target: Book) -> tuple[Layout, Layout] | None:
    """Both books' spine digests, or None when either cannot be read.

    A book that cannot be opened yields no verdict rather than a hopeful one:
    every position then needs a person to look at it.
    """

    if not source.path or not target.path:
        return None
    try:
        return read_layout(source.path), read_layout(target.path)
    except (UnreadableBook, OSError):
        return None


def _verdict(
    annotation: Annotation,
    already_there: set[str],
    layouts: tuple[Layout, Layout] | None,
) -> str:
    if annotation.location in already_there:
        return "already-there"
    if layouts is None:
        return "needs-review"
    return (
        "same-edition"
        if carries_over(layouts[0], layouts[1], annotation.location)
        else "needs-review"
    )


def build_transfer_plan(
    library: AppleBooksLibrary,
    source_asset_id: str,
    target_asset_id: str,
) -> TransferPlan:
    """Describe what moving the source book's annotations would mean.

    Nothing is written. A verdict of `same-edition` means the chapter this note
    sits in is byte-for-byte the same document in both books, so its position
    means the same thing there.

    A shared edition id is **not** enough and was once trusted here. Two files
    can carry the same `ZEPUBID`, the same spine, the same chapter filenames, and
    still differ inside: one extra image in a chapter shifts every element index
    after it, and a note copied on that evidence appears in the sidebar while
    highlighting nothing on the page. So the documents themselves are compared,
    and anything that cannot be established is flagged for a person to look at.
    """

    if source_asset_id == target_asset_id:
        raise SameBook(source_asset_id)
    # One listing serves both lookups: each extra read copies the person's data
    # to disk again for no gain.
    books = library.books()
    source = select_book(books, source_asset_id)
    target = select_book(books, target_asset_id)
    layouts = _layouts(source, target)
    # The target's annotations are read for one reason: to say which of these
    # are already over there. Without it the preview promises items the copy
    # will skip, and the two disagree in front of the person using them. Both
    # books come out of one read, so this still copies the database only once.
    found = library.annotations_for(source_asset_id, target_asset_id)
    already_there = {
        annotation.location for annotation in found.get(target_asset_id, ())
    }
    items = [
        TransferItem(
            annotation=annotation,
            verdict=_verdict(annotation, already_there, layouts),
        )
        for annotation in found.get(source_asset_id, ())
    ]
    return TransferPlan(source=source, target=target, items=tuple(items))
