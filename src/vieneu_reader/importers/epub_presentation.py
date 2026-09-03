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

from vieneu_reader.domain.models import BookDocument, Chapter, stable_id
from vieneu_reader.domain.presentation import (
    BookPresentation,
    ChapterPresentation,
    FigureRef,
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


@dataclass(frozen=True, slots=True)
class _ImageEvent:
    source_occurrence: int
    src: str
    alt_text: str | None
    alt_is_generic: bool
    is_companion: bool


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
    )


def _chapter_events(root: ElementTree.Element) -> tuple[_Event, ...]:
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
                events.append(_TextEvent(text))
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


def _prefer_localized_companions(
    events: tuple[_PreparedEvent, ...],
) -> tuple[_PreparedEvent, ...]:
    selected: list[_PreparedEvent] = []
    last_image_index: int | None = None
    for event in events:
        if isinstance(event, _TextEvent):
            selected.append(event)
            last_image_index = None
            continue
        if event.is_companion and last_image_index is not None:
            previous = selected[last_image_index]
            if isinstance(previous, _AcceptedImage) and not previous.is_companion:
                selected[last_image_index] = event
                continue
        selected.append(event)
        last_image_index = len(selected) - 1
    return tuple(selected)


def _prepared_events(
    archive: ZipFile,
    content_member: str,
    content_root: ElementTree.Element,
    image_manifest: dict[str, str],
    dimensions: dict[str, tuple[int, int] | None],
) -> tuple[_PreparedEvent, ...]:
    prepared: list[_PreparedEvent] = []
    for event in _chapter_events(content_root):
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
            )
        )
    return _prefer_localized_companions(tuple(prepared))


def _chapter_presentation(
    book: BookDocument,
    chapter: Chapter,
    events: tuple[_PreparedEvent, ...],
    *,
    first_figure_number: int,
) -> tuple[ChapterPresentation, int]:
    generated_text: list[str] = []
    image_anchors: list[tuple[_AcceptedImage, int | None]] = []
    previous_segment_index: int | None = None
    for event in events:
        if isinstance(event, _TextEvent):
            parts = split_paragraph(event.text, max_chars=SPEECH_SEGMENT_MAX_CHARS)
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
    for image, previous_index in image_anchors:
        if len(figures) + first_figure_number > MAX_FIGURE_OCCURRENCES:
            raise CorruptBookError("EPUB tạo ra quá nhiều hình ảnh đọc.")
        if previous_index is None:
            anchor = chapter.segments[0]
            placement: Literal["before", "after"] = "before"
        else:
            anchor = chapter.segments[previous_index]
            placement = "after"
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
            )
        )
        next_number += 1
    return ChapterPresentation(chapter.id, tuple(figures)), next_number


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
        content_cache: dict[str, tuple[_PreparedEvent, ...]] = {}
        dimensions: dict[str, tuple[int, int] | None] = {}
        presentations: list[ChapterPresentation] = []
        chapter_index = 0
        next_figure_number = 1
        for item_id in spine:
            item = manifest.get(item_id)
            if item is None or item[1] != "application/xhtml+xml":
                continue
            member = item[0]
            events = content_cache.get(member)
            if events is None:
                root = _parse_xml(_read_member(archive, member), "EPUB chapter")
                events = _prepared_events(
                    archive,
                    member,
                    root,
                    image_manifest,
                    dimensions,
                )
                content_cache[member] = events
            text_exists = any(isinstance(event, _TextEvent) for event in events)
            if not text_exists:
                continue
            if chapter_index >= len(book.chapters):
                raise CorruptBookError("Spine EPUB không còn khớp bản sách đã nhập.")
            presentation, next_figure_number = _chapter_presentation(
                book,
                book.chapters[chapter_index],
                events,
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
