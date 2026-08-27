"""Bounded, spine-ordered EPUB import using only the Python standard library."""

from __future__ import annotations

from collections.abc import Iterator
from hashlib import sha256
import lzma
from pathlib import Path, PurePosixPath
import posixpath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile, ZipInfo
import zlib

from vieneu_reader.domain.models import BookDocument, Chapter, Segment, stable_id
from vieneu_reader.domain.segmenter import normalize_paragraph, split_paragraph

from .errors import CorruptBookError


MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_METADATA_BYTES = 20 * 1024 * 1024
MAX_MANIFEST_ITEMS = 20_000
MAX_SPINE_ITEMS = 2_000
MAX_BOOK_CHAPTERS = 2_000
MAX_BOOK_SEGMENTS = 100_000
MAX_BOOK_TEXT_CHARS = 20_000_000
MAX_XML_ELEMENTS = 100_000
MAX_TITLE_CHARS = 500
SPEECH_SEGMENT_MAX_CHARS = 240
_IGNORED_TAGS = frozenset({"head", "script", "style", "nav", "noscript", "svg"})
_READING_TAGS = frozenset(
    {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre", "figcaption"}
)
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_EOCD_SIGNATURE = b"PK\x05\x06"
_EOCD_BYTES = 22
_MAX_ZIP_COMMENT_BYTES = 65_535
_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
_CENTRAL_DIRECTORY_HEADER_BYTES = 46


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or (path.parts and ":" in path.parts[0])
    ):
        raise CorruptBookError("EPUB chứa đường dẫn không an toàn.")
    return path.as_posix()


def _validate_archive(infos: list[ZipInfo]) -> None:
    if len(infos) > MAX_ARCHIVE_MEMBERS:
        raise CorruptBookError("EPUB chứa quá nhiều thành phần.")
    total = 0
    seen: set[str] = set()
    for info in infos:
        safe_name = _safe_member_name(info.filename)
        if info.is_dir():
            continue
        if safe_name in seen:
            raise CorruptBookError("EPUB chứa mục tệp trùng lặp.")
        seen.add(safe_name)
        if info.flag_bits & 0x1:
            raise CorruptBookError("EPUB được mã hóa nên không thể đọc.")
        if info.file_size < 0 or info.file_size > MAX_MEMBER_BYTES:
            raise CorruptBookError("Một thành phần EPUB vượt giới hạn an toàn.")
        total += info.file_size
        if total > MAX_ARCHIVE_BYTES:
            raise CorruptBookError("EPUB vượt giới hạn dung lượng an toàn.")


def _find_eocd(path: Path) -> tuple[int, bytes] | None:
    """Find a structurally complete classic ZIP end record in a bounded tail."""

    size = path.stat().st_size
    if size < _EOCD_BYTES:
        return None
    tail_size = min(size, _EOCD_BYTES + _MAX_ZIP_COMMENT_BYTES)
    with path.open("rb") as source:
        source.seek(size - tail_size)
        tail = source.read(tail_size)
    search_end = len(tail)
    while search_end:
        offset = tail.rfind(_EOCD_SIGNATURE, 0, search_end)
        if offset < 0:
            return None
        if offset + _EOCD_BYTES <= len(tail):
            comment_size = int.from_bytes(tail[offset + 20 : offset + 22], "little")
            if offset + _EOCD_BYTES + comment_size == len(tail):
                absolute_offset = size - tail_size + offset
                return absolute_offset, tail[offset : offset + _EOCD_BYTES]
        search_end = offset
    return None


def _preflight_archive(path: Path) -> None:
    end_record = _find_eocd(path)
    if end_record is None:
        raise CorruptBookError("EPUB không có mục lục ZIP hợp lệ.")
    eocd_offset, eocd = end_record
    declared_comment_size = int.from_bytes(eocd[20:22], "little")
    actual_comment_size = path.stat().st_size - eocd_offset - _EOCD_BYTES
    if declared_comment_size != actual_comment_size:
        raise CorruptBookError("EPUB có mục lục ZIP không nhất quán.")
    disk_number = int.from_bytes(eocd[4:6], "little")
    directory_disk = int.from_bytes(eocd[6:8], "little")
    disk_entries = int.from_bytes(eocd[8:10], "little")
    declared_entries = int.from_bytes(eocd[10:12], "little")
    directory_size = int.from_bytes(eocd[12:16], "little")
    directory_offset = int.from_bytes(eocd[16:20], "little")
    if disk_number or directory_disk or disk_entries != declared_entries:
        raise CorruptBookError("EPUB nhiều phần không được hỗ trợ.")
    if (
        declared_entries == 0xFFFF
        or directory_size == 0xFFFFFFFF
        or directory_offset == 0xFFFFFFFF
    ):
        raise CorruptBookError("EPUB ZIP64 không được hỗ trợ trong bản MVP.")
    if directory_size > MAX_ARCHIVE_METADATA_BYTES:
        raise CorruptBookError("Mục lục EPUB vượt giới hạn an toàn.")

    concatenated_prefix = eocd_offset - directory_size - directory_offset
    directory_start = concatenated_prefix + directory_offset
    if directory_start < 0 or directory_start + directory_size != eocd_offset:
        raise CorruptBookError("Mục lục EPUB không hợp lệ.")

    actual_entries = 0
    remaining = directory_size
    with path.open("rb") as source:
        source.seek(directory_start)
        while remaining:
            if remaining < _CENTRAL_DIRECTORY_HEADER_BYTES:
                raise CorruptBookError("Mục lục EPUB không hợp lệ.")
            header = source.read(_CENTRAL_DIRECTORY_HEADER_BYTES)
            if (
                len(header) != _CENTRAL_DIRECTORY_HEADER_BYTES
                or header[:4] != _CENTRAL_DIRECTORY_SIGNATURE
            ):
                raise CorruptBookError("Mục lục EPUB không hợp lệ.")
            variable_size = sum(
                int.from_bytes(header[offset : offset + 2], "little")
                for offset in (28, 30, 32)
            )
            entry_size = _CENTRAL_DIRECTORY_HEADER_BYTES + variable_size
            if entry_size > remaining:
                raise CorruptBookError("Mục lục EPUB không hợp lệ.")
            source.seek(variable_size, 1)
            remaining -= entry_size
            actual_entries += 1
            if actual_entries > MAX_ARCHIVE_MEMBERS:
                raise CorruptBookError("EPUB chứa quá nhiều thành phần.")
    if actual_entries != declared_entries:
        raise CorruptBookError("Mục lục EPUB khai báo số thành phần không nhất quán.")


class _BoundedTreeBuilder(ElementTree.TreeBuilder):
    def __init__(self, label: str):
        super().__init__()
        self._label = label
        self._element_count = 0

    def start(self, tag: str, attrs: dict[str, str]) -> ElementTree.Element:
        self._element_count += 1
        if self._element_count > MAX_XML_ELEMENTS:
            raise CorruptBookError(f"{self._label} có XML quá phức tạp.")
        return super().start(tag, attrs)

    def doctype(
        self,
        name: str,
        public_id: str | None,
        system_id: str | None,
    ) -> None:
        del name, public_id, system_id
        raise CorruptBookError(
            f"{self._label} chứa khai báo XML không an toàn."
        )


def _parse_xml(payload: bytes, label: str) -> ElementTree.Element:
    parser = ElementTree.XMLParser(target=_BoundedTreeBuilder(label))
    try:
        for offset in range(0, len(payload), 64 * 1024):
            parser.feed(payload[offset : offset + 64 * 1024])
        return parser.close()
    except CorruptBookError:
        raise
    except (ElementTree.ParseError, LookupError, ValueError) as error:
        raise CorruptBookError(f"{label} không phải XML hợp lệ.") from error


def _read_member(archive: ZipFile, name: str) -> bytes:
    safe_name = _safe_member_name(name)
    try:
        info = archive.getinfo(safe_name)
    except KeyError as error:
        raise CorruptBookError(f"EPUB thiếu thành phần bắt buộc: {safe_name}.") from error
    if info.file_size > MAX_MEMBER_BYTES:
        raise CorruptBookError("Một thành phần EPUB vượt giới hạn an toàn.")
    try:
        return archive.read(info)
    except (zlib.error, lzma.LZMAError) as error:
        raise CorruptBookError("Một thành phần EPUB bị hỏng.") from error


def _resolve_href(package_path: str, href: str) -> str:
    try:
        parsed = urlsplit(href)
    except ValueError as error:
        raise CorruptBookError(
            "EPUB chứa đường dẫn nội dung không hợp lệ."
        ) from error
    if parsed.scheme or parsed.netloc:
        raise CorruptBookError("EPUB chứa đường dẫn nội dung không an toàn.")
    decoded = unquote(parsed.path).replace("\\", "/")
    base = PurePosixPath(package_path).parent.as_posix()
    resolved = posixpath.normpath(posixpath.join(base, decoded))
    return _safe_member_name(resolved)


def _is_hidden(element: ElementTree.Element) -> bool:
    attributes = {_local_name(key): value.lower() for key, value in element.attrib.items()}
    if "hidden" in attributes or attributes.get("aria-hidden") == "true":
        return True
    style = attributes.get("style", "").replace(" ", "")
    return "display:none" in style or "visibility:hidden" in style


def _visible_inner_text(element: ElementTree.Element) -> str:
    if _local_name(element.tag) in _IGNORED_TAGS or _is_hidden(element):
        return ""
    pieces = [element.text or ""]
    for child in element:
        pieces.append(_visible_inner_text(child))
        pieces.append(child.tail or "")
    return normalize_paragraph(" ".join(pieces))


def _reading_blocks(root: ElementTree.Element) -> Iterator[tuple[str, str]]:
    def normalized_block(tag: str, text: str | None) -> tuple[str, str] | None:
        normalized = normalize_paragraph(text or "")
        if normalized:
            return tag, normalized
        return None

    def visit(element: ElementTree.Element) -> Iterator[tuple[str, str]]:
        tag = _local_name(element.tag)
        if tag in _IGNORED_TAGS or _is_hidden(element):
            return
        if tag in _READING_TAGS:
            text = _visible_inner_text(element)
            if text:
                yield tag, text
            return
        block = normalized_block("p", element.text)
        if block is not None:
            yield block
        for child in element:
            yield from visit(child)
            block = normalized_block("p", child.tail)
            if block is not None:
                yield block

    yield from visit(root)


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_title(package_root: ElementTree.Element, fallback: str) -> str:
    for element in package_root.iter():
        if _local_name(element.tag) == "title":
            title = normalize_paragraph(element.text or "")
            if title:
                if len(title) > MAX_TITLE_CHARS:
                    raise CorruptBookError("EPUB có tiêu đề quá dài.")
                return title
    if len(fallback) > MAX_TITLE_CHARS:
        raise CorruptBookError("EPUB có tiêu đề quá dài.")
    return fallback


def import_epub(path: Path) -> BookDocument:
    """Import one EPUB into the normalized reading-domain contract."""

    source = Path(path)
    try:
        _preflight_archive(source)
        source_hash = _file_hash(source)
        with ZipFile(source) as archive:
            _validate_archive(archive.infolist())
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
            book_title = _metadata_title(package_root, source.stem)
            manifest: dict[str, str] = {}
            manifest_items = 0
            for element in package_root.iter():
                if _local_name(element.tag) != "item":
                    continue
                manifest_items += 1
                if manifest_items > MAX_MANIFEST_ITEMS:
                    raise CorruptBookError("EPUB manifest chứa quá nhiều mục.")
                item_id = element.attrib.get("id", "")
                href = element.attrib.get("href", "")
                media_type = element.attrib.get("media-type", "")
                if item_id and href and media_type == "application/xhtml+xml":
                    manifest[item_id] = _resolve_href(package_path, href)

            spine: list[str] = []
            for element in package_root.iter():
                if _local_name(element.tag) != "itemref":
                    continue
                if len(spine) >= MAX_SPINE_ITEMS:
                    raise CorruptBookError("EPUB spine chứa quá nhiều mục đọc.")
                spine.append(element.attrib.get("idref", ""))
            book_id = stable_id(source_hash, "epub")
            chapters: list[Chapter] = []
            content_cache: dict[
                str,
                tuple[
                    tuple[tuple[str, str, tuple[str, ...]], ...],
                    int,
                    int,
                ],
            ] = {}
            generated_segments = 0
            generated_text_chars = 0
            for item_id in spine:
                member = manifest.get(item_id)
                if not member:
                    continue
                cached_content = content_cache.get(member)
                if cached_content is None:
                    content_root = _parse_xml(
                        _read_member(archive, member),
                        "EPUB chapter",
                    )
                    prepared_blocks: list[tuple[str, str, tuple[str, ...]]] = []
                    prepared_segments = 0
                    prepared_text_chars = 0
                    for tag, paragraph in _reading_blocks(content_root):
                        remaining_segments = (
                            MAX_BOOK_SEGMENTS
                            - generated_segments
                            - prepared_segments
                        )
                        minimum_segments = (
                            len(paragraph) + SPEECH_SEGMENT_MAX_CHARS - 1
                        ) // SPEECH_SEGMENT_MAX_CHARS
                        if remaining_segments <= 0 or minimum_segments > remaining_segments:
                            raise CorruptBookError("EPUB tạo ra quá nhiều đoạn đọc.")
                        if (
                            generated_text_chars
                            + prepared_text_chars
                            + len(paragraph)
                            > MAX_BOOK_TEXT_CHARS
                        ):
                            raise CorruptBookError("EPUB có nội dung đọc quá dài.")
                        speech_parts = split_paragraph(
                            paragraph,
                            max_chars=SPEECH_SEGMENT_MAX_CHARS,
                        )
                        prepared_segments += len(speech_parts)
                        if generated_segments + prepared_segments > MAX_BOOK_SEGMENTS:
                            raise CorruptBookError("EPUB tạo ra quá nhiều đoạn đọc.")
                        prepared_text_chars += sum(map(len, speech_parts))
                        if (
                            generated_text_chars + prepared_text_chars
                            > MAX_BOOK_TEXT_CHARS
                        ):
                            raise CorruptBookError("EPUB có nội dung đọc quá dài.")
                        prepared_blocks.append((tag, paragraph, speech_parts))
                    cached_content = (
                        tuple(prepared_blocks),
                        prepared_segments,
                        prepared_text_chars,
                    )
                    content_cache[member] = cached_content
                prepared, prepared_segments, prepared_text_chars = cached_content
                if not prepared:
                    continue
                if len(chapters) >= MAX_BOOK_CHAPTERS:
                    raise CorruptBookError("EPUB tạo ra quá nhiều chương.")
                if generated_segments + prepared_segments > MAX_BOOK_SEGMENTS:
                    raise CorruptBookError("EPUB tạo ra quá nhiều đoạn đọc.")
                if generated_text_chars + prepared_text_chars > MAX_BOOK_TEXT_CHARS:
                    raise CorruptBookError("EPUB có nội dung đọc quá dài.")
                ordinal = len(chapters)
                chapter_id = stable_id(book_id, "chapter", str(ordinal))
                title = next(
                    (text for tag, text, _parts in prepared if tag in _HEADING_TAGS),
                    f"Chương {ordinal + 1}",
                )
                if len(title) > MAX_TITLE_CHARS:
                    raise CorruptBookError("EPUB có tiêu đề quá dài.")
                segments: list[Segment] = []
                for _tag, _paragraph, speech_parts in prepared:
                    for speech_text in speech_parts:
                        segment_ordinal = len(segments)
                        segments.append(
                            Segment(
                                id=stable_id(
                                    chapter_id,
                                    "segment",
                                    str(segment_ordinal),
                                ),
                                chapter_id=chapter_id,
                                ordinal=segment_ordinal,
                                text=speech_text,
                            )
                        )
                generated_segments += prepared_segments
                generated_text_chars += prepared_text_chars
                chapters.append(
                    Chapter(
                        id=chapter_id,
                        title=title,
                        ordinal=ordinal,
                        segments=tuple(segments),
                    )
                )

            if not chapters:
                raise CorruptBookError("EPUB không có nội dung đọc trong spine.")
            return BookDocument(
                id=book_id,
                title=book_title,
                source_format="epub",
                source_hash=source_hash,
                chapters=tuple(chapters),
            )
    except CorruptBookError:
        raise
    except (BadZipFile, OSError, RuntimeError, UnicodeError) as error:
        raise CorruptBookError("Không thể đọc tệp EPUB bị hỏng.") from error
