"""Safe, transient image projection for an already imported EPUB document."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import stat
import struct
from typing import BinaryIO, Literal
import unicodedata
from urllib.parse import unquote, urlsplit
import posixpath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from vieneu_reader.domain.models import BookDocument, Chapter, Segment, stable_id
from vieneu_reader.domain.content_patterns import is_image_annotation
from vieneu_reader.domain.presentation import (
    BookPresentation,
    ChapterPresentation,
    FigureRef,
    NoteRef,
    figure_label,
)
from vieneu_reader.domain.segmenter import normalize_paragraph, split_paragraph

from .epub import (
    MAX_ARCHIVE_BYTES,
    MAX_MANIFEST_ITEMS,
    MAX_SPINE_ITEMS,
    SPEECH_SEGMENT_MAX_CHARS,
    _IGNORED_TAGS,
    _READING_TAGS,
    _is_hidden,
    _local_name,
    _parse_xml,
    _preflight_archive,
    _read_member,
    _resolve_href,
    _safe_member_name,
    _validate_archive,
    _visible_inner_text,
)
from .covers import shrink_cover
from .errors import CorruptBookError


MAX_FIGURE_OCCURRENCES = 20_000
#: A book with more references than this is not a book with footnotes.
MAX_NOTE_OCCURRENCES = 5_000
#: A note longer than this stopped being a note: read aloud in the middle of
#: a paragraph it buries the sentence it was meant to help. Measured against
#: the owner's two annotated books - 138 notes, median 254 characters, one
#: outlier at 1,546 - so this clears every real note and still refuses an
#: essay. Over the line the block is NOT truncated and NOT spoken inline; it
#: stays a paragraph, read where the book put it. Cutting it would lose the
#: tail twice over, since a note read inline is then not read again.
MAX_NOTE_CHARS = 2_000

#: Private-use characters wrapped around a reference's label while the text
#: is being rebuilt, so its position survives the same whitespace collapsing
#: the stored text went through. They never reach a screen or a voice: the
#: text is compared to the stored segment only AFTER they come out, and that
#: comparison is what proves the position is right.
_NOTE_OPEN = "\ue000"
_NOTE_CLOSE = "\ue001"
MAX_ASSETS_PER_REQUEST = 2_000
MAX_COVER_BYTES = 8_000_000
_COVER_MEDIA_TYPES = {"image/png", "image/gif", "image/jpeg", "image/svg+xml"}
_SUPPORTED_IMAGE_MEDIA_TYPES = frozenset(
    {"image/gif", "image/jpeg", "image/png", "image/webp"}
)
_GENERIC_ALT_TEXT = frozenset(
    {"anh", "hinh", "image", "illustration", "photo", "picture"}
)


@dataclass(frozen=True, slots=True)
class _TextEvent:
    text: str
    #: Its words have already been read, as a footnote, at the sentence that
    #: referenced it. The block stays on the page; the voice skips it.
    spoken: bool = False


@dataclass(frozen=True, slots=True)
class _ImageEvent:
    source_occurrence: int
    src: str
    alt_text: str | None
    alt_is_generic: bool
    is_companion: bool
    #: BookStudio's newer mark for a translated copy of the picture before
    #: it (`bs-localized-image`, in a `bs-localized-image-block`). Unlike a
    #: companion it does NOT replace the original on the page - it is kept
    #: and marked `duplicate_of`, so the reader sees both and hears one.
    is_localized: bool = False


@dataclass(frozen=True, slots=True)
class _AcceptedImage:
    source_occurrence: int
    asset_path: str
    media_type: str
    alt_text: str | None
    alt_is_generic: bool
    is_companion: bool
    width: int | None
    height: int | None
    is_localized: bool = False


_Event = _TextEvent | _ImageEvent
_PreparedEvent = _TextEvent | _AcceptedImage


def _normalized_alt(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_paragraph(value)
    return normalized or None


def _generic_alt(value: str | None) -> bool:
    if value is None:
        return True
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    folded = "".join(
        character
        for character in decomposed
        if character.isalnum() and not unicodedata.combining(character)
    )
    return folded in _GENERIC_ALT_TEXT


def _class_names(element: ElementTree.Element) -> frozenset[str]:
    value = next(
        (
            raw
            for key, raw in element.attrib.items()
            if _local_name(key) == "class"
        ),
        "",
    )
    return frozenset(part.casefold() for part in value.split() if part)


def _image_event(
    element: ElementTree.Element,
    *,
    source_occurrence: int,
    ancestor_classes: frozenset[str],
) -> _ImageEvent | None:
    attributes = {_local_name(key): value for key, value in element.attrib.items()}
    role = attributes.get("role", "").casefold().strip()
    if role in {"none", "presentation"}:
        return None
    if "alt" in attributes and _normalized_alt(attributes.get("alt")) is None:
        return None
    src = attributes.get("src", "").strip()
    if not src:
        return None
    alt_text = _normalized_alt(attributes.get("alt"))
    classes = ancestor_classes | _class_names(element)
    return _ImageEvent(
        source_occurrence=source_occurrence,
        src=src,
        alt_text=alt_text,
        alt_is_generic=_generic_alt(alt_text),
        is_companion="bs-image-companion" in classes,
        is_localized=bool(classes & {"bs-localized-image", "bs-localized-image-block"}),
    )


def _chapter_events(
    root: ElementTree.Element,
    spoken_blocks: frozenset[int] = frozenset(),
) -> tuple[_Event, ...]:
    """Every readable block in one chapter, in order.

    `spoken_blocks` holds the identities of the blocks whose words have
    already been read as footnotes, where they belonged. They still make
    segments - they are on the page, and a person can point at them - but
    the voice has said them once already.
    """

    events: list[_Event] = []
    occurrence = 0

    def images_within(
        element: ElementTree.Element,
        ancestor_classes: frozenset[str],
    ) -> Iterator[_ImageEvent]:
        nonlocal occurrence
        classes = ancestor_classes | _class_names(element)
        for child in element:
            tag = _local_name(child.tag)
            if tag in _IGNORED_TAGS or _is_hidden(child):
                continue
            if tag == "img":
                current = occurrence
                occurrence += 1
                event = _image_event(
                    child,
                    source_occurrence=current,
                    ancestor_classes=classes,
                )
                if event is not None:
                    yield event
            else:
                yield from images_within(child, classes)

    def visit(
        element: ElementTree.Element,
        ancestor_classes: frozenset[str],
    ) -> None:
        nonlocal occurrence
        tag = _local_name(element.tag)
        if tag in _IGNORED_TAGS or _is_hidden(element):
            return
        classes = ancestor_classes | _class_names(element)
        if tag in _READING_TAGS:
            text = _visible_inner_text(element)
            if text:
                events.append(_TextEvent(text, id(element) in spoken_blocks))
            events.extend(images_within(element, ancestor_classes))
            return
        normalized = normalize_paragraph(element.text or "")
        if normalized:
            events.append(_TextEvent(normalized))
        for child in element:
            child_tag = _local_name(child.tag)
            if child_tag == "img" and not _is_hidden(child):
                current = occurrence
                occurrence += 1
                image = _image_event(
                    child,
                    source_occurrence=current,
                    ancestor_classes=classes,
                )
                if image is not None:
                    events.append(image)
            else:
                visit(child, classes)
            normalized_tail = normalize_paragraph(child.tail or "")
            if normalized_tail:
                events.append(_TextEvent(normalized_tail))

    visit(root, frozenset())
    return tuple(events)


@dataclass(frozen=True, slots=True)
class _NoteSource:
    """One reference found in a chapter, before its note has been read."""

    #: The anchor's own id, if it has one - what the note links BACK to.
    ref_id: str
    label: str
    href: str


def _attributes(element: ElementTree.Element) -> dict[str, str]:
    return {_local_name(key): value for key, value in element.attrib.items()}


def _is_noteref(anchor: ElementTree.Element, parent_tag: str) -> bool:
    """Is this link a footnote reference, or just a link?

    Two shapes, both in the owner's library. EPUB 3 says so outright
    (`epub:type="noteref"`, or ARIA's `doc-noteref`); older books say it by
    typography - a bare number set as a superscript that links somewhere.

    The second rule is deliberately narrow. A note's own way-back link is
    also a numbered link between the same two files, and reading it as a
    reference would attach a note to itself: it fails here because there the
    number is INSIDE the anchor (`<a><sup>1</sup></a>`) rather than the
    anchor inside the superscript, and because a link with no digits in it
    is not a reference at all.
    """

    attributes = _attributes(anchor)
    if "#" not in attributes.get("href", ""):
        return False
    kinds = " ".join(
        attributes.get(name, "") for name in ("type", "role", "class")
    ).lower()
    if "noteref" in kinds:
        return True
    label = _visible_inner_text(anchor)
    return parent_tag == "sup" and label.isdigit()


def _mark_noterefs(root: ElementTree.Element) -> tuple[_NoteSource, ...]:
    """Wrap every reference's number in sentinels, in reading order.

    The tree is edited rather than measured, because the number's position
    has to survive `_visible_inner_text` and the whitespace collapsing after
    it - and the only thing that reliably survives those is a character that
    goes through them. What comes back is the references in document order,
    which is the same order the sentinels appear in the rebuilt text.
    """

    found: list[_NoteSource] = []

    def visit(element: ElementTree.Element, parent_tag: str) -> None:
        tag = _local_name(element.tag)
        if tag in _IGNORED_TAGS or _is_hidden(element):
            return
        if tag == "a" and _is_noteref(element, parent_tag):
            if len(found) >= MAX_NOTE_OCCURRENCES:
                raise CorruptBookError("EPUB có quá nhiều chú thích.")
            attributes = _attributes(element)
            # The number is often a CHILD, not the anchor's own text:
            # `<a epub:type="noteref"><sup>6</sup></a>` is the commonest
            # EPUB 3 shape. Read whole, then flattened - a sentinel pair
            # wrapped around nothing would leave the digit in the text for
            # the voice to read AND push every later reference in the
            # paragraph one character off its own number.
            label = _visible_inner_text(element)
            if not label:
                return
            element.text = f"{_NOTE_OPEN}{label}{_NOTE_CLOSE}"
            for child in list(element):
                element.remove(child)
            found.append(
                _NoteSource(
                    ref_id=attributes.get("id", ""),
                    label=label,
                    href=attributes.get("href", ""),
                )
            )
            return
        for child in element:
            visit(child, tag)

    visit(root, "")
    return tuple(found)


def _note_body_text(element: ElementTree.Element, back_id: str) -> str:
    """The note's own words: no number, no way back.

    The link home is furniture for a finger. Spoken it lands as a stray
    arrow or a repeat of the number, so an anchor pointing at the reference
    that sent us here is dropped whole - by its target, not by its class,
    which every publisher spells differently.
    """

    def pieces(node: ElementTree.Element) -> Iterator[str]:
        tag = _local_name(node.tag)
        if tag in _IGNORED_TAGS or _is_hidden(node):
            return
        if tag == "a" and back_id:
            target = _attributes(node).get("href", "")
            if target.rsplit("#", 1)[-1] == back_id and "#" in target:
                # Still yield what followed it - the note's first words
                # often sit in the anchor's tail.
                return
        yield node.text or ""
        for child in node:
            yield from pieces(child)
            yield child.tail or ""

    return normalize_paragraph(" ".join(pieces(element)))


def _without_leading_label(text: str, label: str) -> str:
    """Drop the note's own number: the ear already heard it announced."""

    body = text.lstrip()
    # `startswith` alone turns a note that opens "10 năm sau" into "0 năm
    # sau" when the reference happened to be number 1.
    if label and body.startswith(label) and not body[len(label):len(label) + 1].isdigit():
        body = body[len(label):].lstrip()
        while body[:1] in (".", ")", ":", "-", "\u2013", "\u2014"):
            body = body[1:].lstrip()
    return body


#: Where a note's words actually live. A reference does not always point at
#: the block holding the note - very often it points at the little number
#: INSIDE it (`<p class="footnote"><a id="…fn1a">1</a> iPhone was…`), and
#: reading the anchor alone gives back the number and nothing else.
_NOTE_BLOCKS = frozenset(
    {"p", "li", "aside", "blockquote", "div", "section", "dd", "td"}
)


def _element_by_id(
    root: ElementTree.Element, wanted: str
) -> ElementTree.Element | None:
    """The block a reference points into, not just the thing it points at."""

    parents = {child: parent for parent in root.iter() for child in parent}
    found = next(
        (
            element
            for element in root.iter()
            if _attributes(element).get("id") == wanted
        ),
        None,
    )
    if found is None:
        return None
    node: ElementTree.Element | None = found
    while node is not None and _local_name(node.tag) not in _NOTE_BLOCKS:
        if _local_name(node.tag) in ("body", "html"):
            return found
        node = parents.get(node)
    if node is None:
        return found
    # A book that hangs every note off one `<div>` would otherwise make the
    # first reference swallow all of them - and then suppress the lot as
    # "already read". A block that big is not one note.
    if len(_visible_inner_text(node)) > MAX_NOTE_CHARS:
        return found
    return node


def _resolved_notes(
    archive: ZipFile,
    content_member: str,
    sources: tuple[_NoteSource, ...],
    documents: dict[str, ElementTree.Element | None],
    consumed: set[int] | None = None,
) -> tuple[str, ...]:
    """Read each reference's note. One entry per source, "" when unreadable.

    Position matters more than completeness here: the list is paired with
    the sentinels by index, so a note that cannot be found has to leave a
    hole rather than shift every note after it onto the wrong sentence.
    """

    notes: list[str] = []
    for source in sources:
        member, _, fragment = source.href.partition("#")
        try:
            target_member = (
                _resolve_href(content_member, member) if member else content_member
            )
        except CorruptBookError:
            notes.append("")
            continue
        if target_member not in documents:
            try:
                documents[target_member] = _parse_xml(
                    _read_member(archive, target_member), "EPUB note"
                )
            except (CorruptBookError, KeyError, OSError):
                documents[target_member] = None
        root = documents[target_member]
        element = _element_by_id(root, fragment) if root is not None else None
        if element is None:
            notes.append("")
            continue
        body = _without_leading_label(
            _note_body_text(element, source.ref_id), source.label
        ).strip()
        if len(body) > MAX_NOTE_CHARS:
            # Left alone entirely: it keeps its place in the book and gets
            # read there, whole.
            notes.append("")
            continue
        if body and consumed is not None:
            # Remembered by identity, so the pass that builds the segments
            # can tell the voice it has already said this one.
            consumed.add(id(element))
        notes.append(body)
    return tuple(notes)


def _strip_sentinels(text: str) -> tuple[str, tuple[tuple[int, int], ...]]:
    """The text as it is stored, and where each reference's label sits in it."""

    clean: list[str] = []
    marks: list[tuple[int, int]] = []
    length = 0
    start: int | None = None
    for character in text:
        if character == _NOTE_OPEN:
            start = length
            continue
        if character == _NOTE_CLOSE:
            if start is not None:
                marks.append((start, length - start))
            start = None
            continue
        clean.append(character)
        length += 1
    return "".join(clean), tuple(marks)


def _resolve_image_href(content_member: str, href: str) -> str:
    try:
        parsed = urlsplit(href)
    except ValueError as error:
        raise CorruptBookError("EPUB chứa đường dẫn hình ảnh không hợp lệ.") from error
    if parsed.scheme or parsed.netloc:
        raise CorruptBookError("EPUB chứa đường dẫn hình ảnh từ xa.")
    decoded = unquote(parsed.path).replace("\\", "/")
    base = PurePosixPath(content_member).parent.as_posix()
    resolved = posixpath.normpath(posixpath.join(base, decoded))
    return _safe_member_name(resolved)


def _jpeg_dimensions(payload: bytes) -> tuple[int, int] | None:
    if len(payload) < 4 or payload[:2] != b"\xff\xd8":
        return None
    offset = 2
    while offset + 4 <= len(payload):
        if payload[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(payload) and payload[offset] == 0xFF:
            offset += 1
        if offset >= len(payload):
            return None
        marker = payload[offset]
        offset += 1
        if marker in {0x01, *range(0xD0, 0xDA)}:
            continue
        if offset + 2 > len(payload):
            return None
        length = int.from_bytes(payload[offset : offset + 2], "big")
        if length < 2 or offset + length > len(payload):
            return None
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        } and length >= 7:
            height = int.from_bytes(payload[offset + 3 : offset + 5], "big")
            width = int.from_bytes(payload[offset + 5 : offset + 7], "big")
            return (width, height) if width > 0 and height > 0 else None
        offset += length
    return None


def _image_dimensions(payload: bytes, media_type: str) -> tuple[int, int] | None:
    if media_type == "image/png" and len(payload) >= 24:
        if payload[:8] == b"\x89PNG\r\n\x1a\n" and payload[12:16] == b"IHDR":
            width, height = struct.unpack(">II", payload[16:24])
            return (width, height) if width > 0 and height > 0 else None
    if media_type == "image/gif" and len(payload) >= 10:
        if payload[:6] in {b"GIF87a", b"GIF89a"}:
            width, height = struct.unpack("<HH", payload[6:10])
            return (width, height) if width > 0 and height > 0 else None
    if media_type == "image/jpeg":
        return _jpeg_dimensions(payload)
    return None


def _prepared_events(
    archive: ZipFile,
    content_member: str,
    content_root: ElementTree.Element,
    image_manifest: dict[str, str],
    dimensions: dict[str, tuple[int, int] | None],
    spoken_blocks: frozenset[int] = frozenset(),
) -> tuple[_PreparedEvent, ...]:
    prepared: list[_PreparedEvent] = []
    for event in _chapter_events(content_root, spoken_blocks):
        if isinstance(event, _TextEvent):
            prepared.append(event)
            continue
        try:
            asset_path = _resolve_image_href(content_member, event.src)
        except CorruptBookError:
            continue
        media_type = image_manifest.get(asset_path)
        if media_type not in _SUPPORTED_IMAGE_MEDIA_TYPES:
            continue
        if asset_path not in dimensions:
            try:
                dimensions[asset_path] = _image_dimensions(
                    _read_member(archive, asset_path),
                    media_type,
                )
            except CorruptBookError:
                dimensions[asset_path] = None
        size = dimensions[asset_path]
        width, height = size if size is not None else (None, None)
        if (
            event.alt_is_generic
            and width is not None
            and height is not None
            and max(width, height) <= 64
        ):
            continue
        prepared.append(
            _AcceptedImage(
                source_occurrence=event.source_occurrence,
                asset_path=asset_path,
                media_type=media_type,
                alt_text=event.alt_text,
                alt_is_generic=event.alt_is_generic,
                is_companion=event.is_companion,
                width=width,
                height=height,
                is_localized=event.is_localized,
            )
        )
    return tuple(prepared)


def _caption_of(
    segments: tuple[Segment, ...], previous_index: int | None
) -> Segment | None:
    """The segment that captions the image placed after `previous_index`.

    First the block right after the picture - a figcaption, or a paragraph
    opening with the book's own label ("Hình 1.3. …"), which is how books
    without <figure> caption their art. Failing that, a figcaption right
    before it: some layouts put the caption above. A plain paragraph above
    is never taken - "Hình 1.3 cho thấy…" can open ordinary prose.
    """
    following = 0 if previous_index is None else previous_index + 1
    if following < len(segments):
        candidate = segments[following]
        if candidate.kind == "caption" or figure_label(candidate.text):
            return candidate
    if previous_index is not None:
        above = segments[previous_index]
        # A figcaption above, or a paragraph that is nothing BUT the label
        # ("Minh họa 11") - never prose that merely opens with one.
        if above.kind == "caption" or (
            figure_label(above.text) and len(above.text.split()) <= 8
        ):
            return above
    return None


def _repeats_previous(
    segments: tuple[Segment, ...],
    previous: FigureRef | None,
    previous_image: _AcceptedImage | None,
    previous_anchor: int | None,
    image: _AcceptedImage,
    anchor: int | None,
) -> bool:
    """Is `image` a translated copy of the figure just before it?

    Class-marked only (`bs-localized-image` / `bs-image-companion`): alt
    equality is not a signal - two different figures sit side by side with
    a caption between them all the time. Between the two pictures there may
    be nothing but the first one's caption and a translator's annotation.

    And the picture it repeats must itself be an ORIGINAL: two class-marked
    copies in a row, separated only by the first one's annotation, are two
    different pictures (found by the audit over the owner's library, 05/09).

    An adjacent companion (Krug's layout, `bs-image-companion` right after
    the original) used to REPLACE the original on the page. It is now kept
    and marked like every other copy: one policy for every book, and the
    page keeps everything a reader might want to look back at (owner,
    05/09: "giữ hiển thị đầy đủ để user có thể xem lại").
    """
    if previous is None or not (image.is_localized or image.is_companion):
        return False
    if previous_image is None or previous_image.is_localized or previous_image.is_companion:
        return False
    start = 0 if previous_anchor is None else previous_anchor + 1
    stop = 0 if anchor is None else anchor + 1
    for segment in segments[start:stop]:
        if segment.id == previous.caption_segment_id:
            continue
        if is_image_annotation(segment.text):
            continue
        return False
    return True


def _chapter_presentation(
    book: BookDocument,
    chapter: Chapter,
    events: tuple[_PreparedEvent, ...],
    note_bodies: tuple[str, ...],
    *,
    first_figure_number: int,
) -> tuple[ChapterPresentation, int]:
    generated_text: list[str] = []
    image_anchors: list[tuple[_AcceptedImage, int | None]] = []
    note_marks: list[tuple[int, int, int]] = []
    spoken_indexes: list[int] = []
    previous_segment_index: int | None = None
    for event in events:
        if isinstance(event, _TextEvent):
            # The sentinels come OUT before the split, so a reference cannot
            # change where a long paragraph breaks. Their positions are then
            # carried into whichever part they landed in.
            clean, marks = _strip_sentinels(event.text)
            parts = split_paragraph(clean, max_chars=SPEECH_SEGMENT_MAX_CHARS)
            base = len(generated_text)
            normalized = normalize_paragraph(clean)
            cursor = 0
            spans: list[tuple[int, int, int]] = []
            for offset, part in enumerate(parts):
                at = normalized.find(part, cursor)
                if at < 0:
                    spans = []
                    break
                spans.append((base + offset, at, at + len(part)))
                cursor = at + len(part)
            for start, size in marks:
                # The sentinels were placed in the pre-normalized text; the
                # collapse can only have removed whitespace BEFORE them, so
                # the label is found by name inside the part it fell in.
                placed = next(
                    (
                        (index, start - begin)
                        for index, begin, end in spans
                        if begin <= start < end
                    ),
                    None,
                )
                if placed is not None:
                    note_marks.append((placed[0], placed[1], size))
                else:
                    note_marks.append((-1, -1, size))
            if event.spoken:
                spoken_indexes.extend(range(base, base + len(parts)))
            generated_text.extend(parts)
            if parts:
                previous_segment_index = len(generated_text) - 1
        else:
            image_anchors.append((event, previous_segment_index))
    stored_text = tuple(segment.text for segment in chapter.segments)
    if tuple(generated_text) != stored_text:
        raise CorruptBookError(
            "Nội dung hình ảnh EPUB không còn khớp với bản sách đã nhập."
        )

    figures: list[FigureRef] = []
    next_number = first_figure_number
    previous_anchor: int | None = None
    previous_image: _AcceptedImage | None = None
    for image, previous_index in image_anchors:
        if len(figures) + first_figure_number > MAX_FIGURE_OCCURRENCES:
            raise CorruptBookError("EPUB tạo ra quá nhiều hình ảnh đọc.")
        if previous_index is None:
            anchor = chapter.segments[0]
            placement: Literal["before", "after"] = "before"
        else:
            anchor = chapter.segments[previous_index]
            placement = "after"
        caption = _caption_of(chapter.segments, previous_index)
        labelled = figure_label(caption.text if caption is not None else None)
        if labelled is None:
            labelled = figure_label(image.alt_text)
        original = figures[-1] if figures else None
        duplicate_of: str | None = None
        if _repeats_previous(
            chapter.segments, original, previous_image, previous_anchor,
            image, previous_index,
        ):
            assert original is not None
            # The copy inherits the original's caption and label: one
            # picture, shown twice, named once.
            duplicate_of = original.id
            caption = next(
                (s for s in chapter.segments if s.id == original.caption_segment_id),
                None,
            )
            labelled = figure_label(original.label)
        previous_anchor = previous_index
        previous_image = image
        figures.append(
            FigureRef(
                id=stable_id(
                    book.id,
                    chapter.id,
                    "figure",
                    str(image.source_occurrence),
                    image.asset_path,
                ),
                number=next_number,
                chapter_id=chapter.id,
                source_occurrence=image.source_occurrence,
                anchor_segment_id=anchor.id,
                placement=placement,
                asset_path=image.asset_path,
                media_type=image.media_type,
                alt_text=image.alt_text,
                alt_is_generic=image.alt_is_generic,
                width=image.width,
                height=image.height,
                label=labelled[0] if labelled else None,
                caption_segment_id=caption.id if caption is not None else None,
                duplicate_of=duplicate_of,
            )
        )
        next_number += 1

    notes: list[NoteRef] = []
    for order, (segment_index, offset, size) in enumerate(note_marks):
        body = note_bodies[order] if order < len(note_bodies) else ""
        if not body or segment_index < 0:
            # A note nobody can read, or one whose place could not be found:
            # dropped rather than guessed. A note read after the wrong
            # sentence is worse than a note not read at all.
            continue
        segment = chapter.segments[segment_index]
        notes.append(
            NoteRef(
                id=stable_id(book.id, chapter.id, "note", str(order)),
                label=segment.text[offset:offset + size],
                chapter_id=chapter.id,
                anchor_segment_id=segment.id,
                offset=offset,
                length=size,
                text=body,
            )
        )
    return (
        ChapterPresentation(
            chapter.id,
            tuple(figures),
            tuple(notes),
            tuple(chapter.segments[index].id for index in spoken_indexes),
        ),
        next_number,
    )


@contextmanager
def _verified_archive(
    path: Path,
    *,
    expected_hash: str | None,
) -> Iterator[ZipFile]:
    source = Path(path)
    try:
        metadata = source.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_size > MAX_ARCHIVE_BYTES
        ):
            raise CorruptBookError("Nguồn EPUB được quản lý không còn an toàn.")
        _preflight_archive(source)
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(source, flags)
        stream: BinaryIO | None = None
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != os.getuid()
                or (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino)
            ):
                raise CorruptBookError("Nguồn EPUB được quản lý đã thay đổi.")
            stream = os.fdopen(descriptor, "rb")
            descriptor = -1
            if expected_hash is not None:
                digest = sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                if digest.hexdigest() != expected_hash:
                    raise CorruptBookError("Nguồn EPUB không khớp bản sách đã nhập.")
                stream.seek(0)
            with ZipFile(stream) as archive:
                _validate_archive(archive.infolist())
                yield archive
        finally:
            if stream is not None:
                stream.close()
            elif descriptor >= 0:
                os.close(descriptor)
    except CorruptBookError:
        raise
    except (BadZipFile, OSError, RuntimeError, UnicodeError) as error:
        raise CorruptBookError("Không thể đọc hình ảnh trong EPUB.") from error


def _package_document(archive: ZipFile) -> tuple[str, ElementTree.Element]:
    """The OPF's path and parsed root - shared by the contract and the cover."""

    container = _parse_xml(
        _read_member(archive, "META-INF/container.xml"),
        "EPUB container",
    )
    rootfile = next(
        (
            element
            for element in container.iter()
            if _local_name(element.tag) == "rootfile"
        ),
        None,
    )
    package_path = (
        _safe_member_name(rootfile.attrib.get("full-path", ""))
        if rootfile is not None
        else ""
    )
    if not package_path:
        raise CorruptBookError("EPUB thiếu đường dẫn package.")
    package_root = _parse_xml(
        _read_member(archive, package_path),
        "EPUB package",
    )
    return package_path, package_root


def _package_contract(
    archive: ZipFile,
) -> tuple[str, dict[str, tuple[str, str]], tuple[str, ...]]:
    package_path, package_root = _package_document(archive)
    manifest: dict[str, tuple[str, str]] = {}
    for element in package_root.iter():
        if _local_name(element.tag) != "item":
            continue
        if len(manifest) >= MAX_MANIFEST_ITEMS:
            raise CorruptBookError("EPUB manifest chứa quá nhiều mục.")
        item_id = element.attrib.get("id", "")
        href = element.attrib.get("href", "")
        media_type = element.attrib.get("media-type", "")
        if item_id and href and media_type:
            manifest[item_id] = (_resolve_href(package_path, href), media_type)
    spine: list[str] = []
    for element in package_root.iter():
        if _local_name(element.tag) != "itemref":
            continue
        if len(spine) >= MAX_SPINE_ITEMS:
            raise CorruptBookError("EPUB spine chứa quá nhiều mục đọc.")
        spine.append(element.attrib.get("idref", ""))
    return package_path, manifest, tuple(spine)


def load_epub_presentation(path: Path, book: BookDocument) -> BookPresentation:
    """Derive a figure overlay while proving the stored text still matches."""

    if book.source_format != "epub" or book.id != stable_id(book.source_hash, "epub"):
        raise ValueError("book must be a valid imported EPUB")
    with _verified_archive(Path(path), expected_hash=book.source_hash) as archive:
        _package_path, manifest, spine = _package_contract(archive)
        image_manifest = {
            member: media_type
            for member, media_type in manifest.values()
            if media_type.startswith("image/")
        }
        content_cache: dict[
            str, tuple[tuple[_PreparedEvent, ...], tuple[str, ...]]
        ] = {}
        # ONE parsed tree per member, shared by both passes. A note's block
        # has to be the very object the second pass walks, or "already read"
        # cannot be recognised when the segments are built.
        roots: dict[str, ElementTree.Element | None] = {}
        spoken_blocks: set[int] = set()
        note_bodies_by_member: dict[str, tuple[str, ...]] = {}
        members = [
            manifest[item_id][0]
            for item_id in spine
            if manifest.get(item_id) is not None
            and manifest[item_id][1] == "application/xhtml+xml"
        ]
        # Pass one: find every reference and read the note it points at.
        # Whole-spine first, because a note can live in the same file as its
        # reference, or in a file the spine reaches long before or after it.
        for member in members:
            if member in note_bodies_by_member:
                continue
            if member not in roots:
                roots[member] = _parse_xml(
                    _read_member(archive, member), "EPUB chapter"
                )
            root = roots[member]
            if root is None:
                note_bodies_by_member[member] = ()
                continue
            sources = _mark_noterefs(root)
            note_bodies_by_member[member] = _resolved_notes(
                archive, member, sources, roots, spoken_blocks
            )
        frozen_blocks = frozenset(spoken_blocks)
        dimensions: dict[str, tuple[int, int] | None] = {}
        presentations: list[ChapterPresentation] = []
        chapter_index = 0
        next_figure_number = 1
        for item_id in spine:
            item = manifest.get(item_id)
            if item is None or item[1] != "application/xhtml+xml":
                continue
            member = item[0]
            cached = content_cache.get(member)
            if cached is None:
                root = roots.get(member)
                if root is None:
                    root = _parse_xml(
                        _read_member(archive, member), "EPUB chapter"
                    )
                    roots[member] = root
                events = _prepared_events(
                    archive,
                    member,
                    root,
                    image_manifest,
                    dimensions,
                    frozen_blocks,
                )
                cached = (events, note_bodies_by_member.get(member, ()))
                content_cache[member] = cached
            events, note_bodies = cached
            text_exists = any(isinstance(event, _TextEvent) for event in events)
            if not text_exists:
                continue
            if chapter_index >= len(book.chapters):
                raise CorruptBookError("Spine EPUB không còn khớp bản sách đã nhập.")
            presentation, next_figure_number = _chapter_presentation(
                book,
                book.chapters[chapter_index],
                events,
                note_bodies,
                first_figure_number=next_figure_number,
            )
            presentations.append(presentation)
            chapter_index += 1
        if chapter_index != len(book.chapters):
            raise CorruptBookError("Spine EPUB không còn khớp bản sách đã nhập.")
        return BookPresentation(book.id, book.source_hash, tuple(presentations))


def load_epub_assets(
    path: Path,
    asset_paths: tuple[str, ...],
    *,
    expected_hash: str | None = None,
) -> dict[str, bytes]:
    """Read requested managed EPUB members in memory without extracting files."""

    if len(asset_paths) > MAX_ASSETS_PER_REQUEST:
        raise CorruptBookError("Chương EPUB chứa quá nhiều hình ảnh.")
    requested = tuple(dict.fromkeys(_safe_member_name(item) for item in asset_paths))
    loaded: dict[str, bytes] = {}
    with _verified_archive(Path(path), expected_hash=expected_hash) as archive:
        for member in requested:
            try:
                loaded[member] = _read_member(archive, member)
            except CorruptBookError:
                continue
    return loaded


def _cover_member(
    package_path: str, package_root: ElementTree.Element
) -> tuple[str, str] | None:
    """The manifest member that is the book's cover, by the three conventions
    publishers actually use: EPUB 3's `properties="cover-image"`, EPUB 2's
    `<meta name="cover" content="…">` (an item id, occasionally an href),
    and - for the many files that declare neither - an image whose id or
    file name says "cover". A `<guide type="cover">` pointing at an XHTML
    page is a known gap, left alone on purpose."""

    items: dict[str, tuple[str, str, str]] = {}
    by_href: dict[str, str] = {}
    for element in package_root.iter():
        if _local_name(element.tag) != "item":
            continue
        if len(items) >= MAX_MANIFEST_ITEMS:
            raise CorruptBookError("EPUB manifest chứa quá nhiều mục.")
        item_id = element.attrib.get("id", "")
        href = element.attrib.get("href", "")
        media_type = element.attrib.get("media-type", "").lower()
        if media_type == "image/jpg":
            media_type = "image/jpeg"
        if item_id and href and media_type:
            items[item_id] = (
                _resolve_href(package_path, href),
                media_type,
                element.attrib.get("properties", ""),
            )
            by_href[href] = item_id

    def image(item_id: str) -> tuple[str, str] | None:
        item = items.get(item_id)
        if item is not None and item[1].startswith("image/"):
            return item[0], item[1]
        return None

    for item_id, (_member, media_type, properties) in items.items():
        if "cover-image" in properties.split() and media_type.startswith("image/"):
            return items[item_id][0], media_type
    for element in package_root.iter():
        if (
            _local_name(element.tag) == "meta"
            and element.attrib.get("name", "").lower() == "cover"
        ):
            content = element.attrib.get("content", "")
            found = image(content) or image(by_href.get(content, ""))
            if found is not None:
                return found
    for item_id, (member, media_type, _properties) in items.items():
        name = PurePosixPath(member).name.lower()
        if media_type.startswith("image/") and (
            "cover" in item_id.lower() or "cover" in name
        ):
            return member, media_type
    return None


def _looks_like_image(payload: bytes, media_type: str) -> bool:
    if media_type == "image/svg+xml":
        head = payload[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
        return head.startswith(b"<") and b"<svg" in head
    return _image_dimensions(payload, media_type) is not None


def load_epub_cover(
    path: Path,
    *,
    expected_hash: str | None = None,
) -> tuple[bytes, str] | None:
    """The cover's bytes and media type, or None when the book has none."""

    with _verified_archive(Path(path), expected_hash=expected_hash) as archive:
        package_path, package_root = _package_document(archive)
        found = _cover_member(package_path, package_root)
        if found is None:
            return None
        member, media_type = found
        if media_type not in _COVER_MEDIA_TYPES:
            return None
        try:
            payload = _read_member(archive, member)
        except CorruptBookError:
            return None
        if not payload or len(payload) > MAX_COVER_BYTES:
            return None
        if not _looks_like_image(payload, media_type):
            return None
        return shrink_cover(payload, media_type)
