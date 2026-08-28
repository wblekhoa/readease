"""Decide whether a position in one copy of a book means the same in another.

An Apple Books annotation stores its position as an EPUB CFI, which begins by
counting into the spine - `epubcfi(/6/38[id206]!/…)` is the nineteenth spine
item - and then counts elements inside that document. Copying such a position
between two copies of a book is only safe when the document it lands in is the
same document; insert one image into the chapter and every element index after
it moves, so the note lands somewhere else while still looking valid.

Two copies of one book sharing an edition id does **not** make them the same
book. That was learned the hard way on a real library: two files with identical
`ZEPUBID` and identical spines, where one chapter carried four extra images and
941 more bytes, so notes copied into it appeared in the sidebar and highlighted
nothing on the page. Only the bytes of the document settle it, so that is what
this compares.

Nothing here reads a book's prose. It reads the package file to learn the spine
order, then hashes whole documents.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

_CFI_SPINE = re.compile(r"^epubcfi\(/6/(\d+)")
_CONTAINER = "META-INF/container.xml"
_READ_LIMIT = 64 * 1024 * 1024


class UnreadableBook(RuntimeError):
    """The book file could not be opened or made sense of."""


@dataclass(frozen=True, slots=True)
class Layout:
    """A book's spine, with each document reduced to a digest."""

    digests: tuple[str, ...]

    def digest_at(self, spine_index: int) -> str | None:
        if 0 <= spine_index < len(self.digests):
            return self.digests[spine_index]
        return None


def spine_index(location: str) -> int | None:
    """The spine position a CFI starts at, or None if it does not say.

    CFI step 6 addresses the spine element and its children are counted from
    two, so `/6/38` is spine item nineteen, counted from zero as eighteen.
    """

    match = _CFI_SPINE.match(location or "")
    if match is None:
        return None
    step = int(match.group(1))
    if step < 2 or step % 2:
        return None
    return step // 2 - 1


def _package_path(read, names: list[str]) -> str:
    if _CONTAINER in names:
        try:
            root = ET.fromstring(read(_CONTAINER))
        except ET.ParseError:
            pass
        else:
            for element in root.iter():
                if element.tag.endswith("rootfile"):
                    full = element.get("full-path")
                    if full:
                        return full
    packages = [name for name in names if name.endswith(".opf")]
    if not packages:
        raise UnreadableBook("no package document")
    # Shallowest wins: a nested copy in a backup folder is not the real one.
    return min(packages, key=lambda name: (name.count("/"), len(name)))


def _spine_hrefs(package: bytes, package_name: str) -> list[str]:
    try:
        root = ET.fromstring(package)
    except ET.ParseError as error:
        raise UnreadableBook("package document is not valid XML") from error
    namespace = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""
    tag = (lambda name: f"{{{namespace}}}{name}") if namespace else (lambda name: name)

    manifest = {
        item.get("id"): item.get("href")
        for item in root.iter(tag("item"))
        if item.get("id") and item.get("href")
    }
    order = [
        reference.get("idref")
        for reference in root.iter(tag("itemref"))
        if reference.get("idref")
    ]
    base = package_name.rsplit("/", 1)[0] if "/" in package_name else ""
    hrefs = []
    for identifier in order:
        href = manifest.get(identifier)
        if href is None:
            hrefs.append("")
            continue
        joined = f"{base}/{href}" if base else href
        # Normalise "a/../b" so the same document hashes once.
        parts: list[str] = []
        for piece in joined.split("/"):
            if piece in ("", "."):
                continue
            if piece == ".." and parts:
                parts.pop()
            else:
                parts.append(piece)
        hrefs.append("/".join(parts))
    return hrefs


def read_layout(book_path: str | Path) -> Layout:
    """Hash every spine document of a book.

    Apple Books keeps some titles as a plain directory rather than a zip, so
    both shapes are handled.
    """

    path = Path(book_path).expanduser()
    if path.is_dir():
        names = [
            str(item.relative_to(path))
            for item in path.rglob("*")
            if item.is_file()
        ]

        def read(name: str) -> bytes:
            target = path / name
            if not target.is_file() or target.stat().st_size > _READ_LIMIT:
                raise UnreadableBook(name)
            return target.read_bytes()

    elif path.is_file():
        try:
            archive = zipfile.ZipFile(path)
        except (OSError, zipfile.BadZipFile) as error:
            raise UnreadableBook(str(path)) from error
        names = archive.namelist()

        def read(name: str) -> bytes:
            info = archive.getinfo(name)
            if info.file_size > _READ_LIMIT:
                raise UnreadableBook(name)
            return archive.read(name)

    else:
        raise UnreadableBook(str(path))

    try:
        package_name = _package_path(read, names)
        hrefs = _spine_hrefs(read(package_name), package_name)
        digests = []
        for href in hrefs:
            try:
                digests.append(hashlib.sha256(read(href)).hexdigest() if href else "")
            except (OSError, KeyError, UnreadableBook):
                # A document we cannot read is a document we cannot vouch for.
                digests.append("")
    except (OSError, KeyError) as error:
        raise UnreadableBook(str(path)) from error
    return Layout(digests=tuple(digests))


def carries_over(source: Layout, target: Layout, location: str) -> bool:
    """True when this position addresses the same document in both books.

    False is the answer whenever that cannot be established - an unparsable
    CFI, a spine that is too short, or a document either side could not be
    read. A position that cannot be vouched for is not one to copy silently.
    """

    index = spine_index(location)
    if index is None:
        return False
    first, second = source.digest_at(index), target.digest_at(index)
    return bool(first) and first == second
