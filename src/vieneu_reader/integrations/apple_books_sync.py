"""Bring a book and its highlights over from Apple Books - one way, on request.

Apple Books keeps a person's own EPUBs UNPACKED (a folder named `x.epub`), and
ReadEase's importer takes a file, so the folder is zipped first. The zip must
be the same bytes every time: the importer dedupes on the file's hash, and a
folder packed with today's timestamps would come in as a new book on every
sync. Purchased books are encrypted (FairPlay) and cannot be read; a file that
merely obfuscates its fonts is not, and must not be refused for it.

Highlights come back by their WORDS, not their position: Apple stores an EPUB
CFI, which counts elements inside Apple's own rendering of the file, and this
reader splits text differently. The words the person selected are the same in
both, so the segment that contains them is where the highlight goes. The CFI
still helps once - when the same words occur in two chapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
from typing import Sequence
import unicodedata
from xml.etree import ElementTree
import zipfile

from vieneu_reader.integrations.apple_books import Annotation
from vieneu_reader.integrations.epub_layout import spine_index

HIGHLIGHT_KIND = 2
_SKIPPED_NAMES = frozenset({"iTunesMetadata.plist", "iTunesArtwork", ".DS_Store"})
_SKIPPED_DIRS = frozenset({"__MACOSX"})
_FONT_SUFFIXES = frozenset({".ttf", ".otf", ".woff", ".woff2", ".ttc", ".dfont"})
_FIXED_STAMP = (1980, 1, 1, 0, 0, 0)
_TITLE_PREFIX = 24
_MATCH_CHARS = 40


def folder_is_encrypted(folder: Path) -> bool:
    """True when the EPUB's content (not just its fonts) is encrypted.

    `META-INF/encryption.xml` also appears in honest files that obfuscate
    embedded fonts (IDPF/Adobe); those list font files only. Anything else
    behind a CipherReference means DRM, and the text cannot be read.
    """

    manifest = Path(folder) / "META-INF" / "encryption.xml"
    if not manifest.is_file():
        return False
    try:
        root = ElementTree.fromstring(manifest.read_bytes())
    except ElementTree.ParseError:
        return True
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "CipherReference":
            continue
        target = element.attrib.get("URI", "")
        if Path(target).suffix.lower() not in _FONT_SUFFIXES:
            return True
    return False


def folder_size(folder: Path) -> int:
    return sum(path.stat().st_size for path in Path(folder).rglob("*") if path.is_file())


def pack_epub_folder(folder: Path, destination: Path) -> Path:
    """Zip an unpacked EPUB into a file with the same bytes on every run."""

    folder = Path(folder)
    members: list[Path] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(folder)
        if relative.parts[0] in _SKIPPED_DIRS or relative.name in _SKIPPED_NAMES:
            continue
        members.append(relative)
    mimetype = Path("mimetype")
    ordered = ([mimetype] if mimetype in members else []) + [m for m in members if m != mimetype]
    with zipfile.ZipFile(destination, "w") as archive:
        for relative in ordered:
            info = zipfile.ZipInfo(relative.as_posix(), date_time=_FIXED_STAMP)
            info.external_attr = 0o644 << 16
            if relative == mimetype:
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, b"application/epub+zip")
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (folder / relative).read_bytes(), compresslevel=6)
    return destination


def normalize_text(value: str | None) -> str:
    """Words as words: quotes straightened, spaces collapsed, case folded."""

    text = unicodedata.normalize("NFC", value or "")
    text = (
        text.replace("“", '"').replace("”", '"').replace("‘", "'")
        .replace("’", "'").replace(" ", " ").replace("…", "...")
    )
    return re.sub(r"\s+", " ", text).strip().casefold()


def normalize_title(value: str | None) -> str:
    return re.sub(r"[^\w\s]", " ", normalize_text(value)).strip()


def same_title(left: str | None, right: str | None) -> bool:
    """Two listings of one book, allowing for a subtitle rendered differently.

    Equal after normalising, or equal over the first 24 characters when both
    are at least that long - the translated subtitle of one copy may differ
    word for word from the other while the title itself is identical.
    """

    a = re.sub(r"\s+", " ", normalize_title(left))
    b = re.sub(r"\s+", " ", normalize_title(right))
    if not a or not b:
        return False
    if a == b:
        return True
    return len(a) >= _TITLE_PREFIX and len(b) >= _TITLE_PREFIX and a[:_TITLE_PREFIX] == b[:_TITLE_PREFIX]


@dataclass(frozen=True, slots=True)
class SegmentRef:
    chapter_index: int
    segment_id: str
    text: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class MatchedNote:
    id: str
    segment_id: str
    selected_text: str = field(repr=False)
    note: str | None = field(repr=False, default=None)
    style: int = 0


@dataclass(frozen=True, slots=True)
class MatchReport:
    matched: tuple[MatchedNote, ...]
    unmatched: int
    skipped: int


def annotation_id(annotation: Annotation) -> str:
    digest = hashlib.sha256()
    for part in (annotation.asset_id, annotation.location, annotation.selected_text or ""):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return "applebooks:" + digest.hexdigest()[:24]


def match_annotations(
    segments: Sequence[SegmentRef], annotations: Sequence[Annotation]
) -> MatchReport:
    """Place each highlight on the segment that holds its words.

    Bookmarks and anything without selected text are skipped, not failed.
    The opening 40 normalised characters are what is searched: a highlight
    may run across several segments, and the segment it starts in is the one
    that gets it. Several candidates → the chapter nearest the CFI's spine
    position wins, then the earliest.
    """

    haystack = [(ref, normalize_text(ref.text)) for ref in segments]
    matched: list[MatchedNote] = []
    unmatched = skipped = 0
    for annotation in annotations:
        if annotation.kind != HIGHLIGHT_KIND or not (annotation.selected_text or "").strip():
            skipped += 1
            continue
        needle = normalize_text(annotation.selected_text)[:_MATCH_CHARS]
        candidates = [ref for ref, text in haystack if needle and needle in text]
        if not candidates:
            unmatched += 1
            continue
        hint = spine_index(annotation.location)
        if hint is not None and len(candidates) > 1:
            candidates.sort(key=lambda ref: (abs(ref.chapter_index - hint), ref.chapter_index))
        chosen = candidates[0]
        matched.append(MatchedNote(
            id=annotation_id(annotation),
            segment_id=chosen.segment_id,
            selected_text=annotation.selected_text or "",
            note=annotation.note or None,
            style=getattr(annotation, "style", 0),
        ))
    return MatchReport(tuple(matched), unmatched, skipped)
