"""Bounded text-layer PDF import through the bundled QtPdf runtime."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from PySide6.QtCore import QModelIndex
from PySide6.QtPdf import QPdfBookmarkModel, QPdfDocument

from vieneu_reader.domain.models import BookDocument, Chapter, Segment, stable_id
from vieneu_reader.domain.segmenter import normalize_paragraph, split_paragraph

from .errors import CorruptBookError


MAX_PAGES = 10_000
MAX_BLOCKS = 100_000
MAX_TEXT_CHARS = 20_000_000
MAX_TITLE_CHARS = 500
SPEECH_SEGMENT_MAX_CHARS = 240
MIN_NON_WHITESPACE_CHARS = 20
_WRAPPED_LINE_GAP_FACTOR = 1.25
_VERTICAL_TOLERANCE = 1.0


@dataclass(frozen=True, slots=True)
class _VisualLine:
    text: str
    top: float | None
    bottom: float | None


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utf16_length(value: str) -> int:
    """Return Qt's UTF-16 text-index length, including surrogate pairs."""

    return len(value.encode("utf-16-le")) // 2


def _document_title(document: QPdfDocument, fallback: str) -> str:
    title = normalize_paragraph(
        str(document.metaData(QPdfDocument.MetaDataField.Title) or "")
    ) or fallback
    if len(title) > MAX_TITLE_CHARS:
        raise CorruptBookError("PDF có tiêu đề quá dài.")
    return title


def _visual_lines(document: QPdfDocument, page_index: int) -> tuple[_VisualLine, ...]:
    text = document.getAllText(page_index).text()
    lines: list[_VisualLine] = []
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        paragraph = normalize_paragraph(line)
        line_length = _utf16_length(line)
        if not paragraph:
            lines.append(_VisualLine("", None, None))
        else:
            selection = document.getSelectionAtIndex(page_index, offset, line_length)
            rectangle = selection.boundingRectangle()
            if selection.isValid() and not rectangle.isNull():
                lines.append(
                    _VisualLine(
                        paragraph,
                        top=float(rectangle.top()),
                        bottom=float(rectangle.bottom()),
                    )
                )
            else:
                lines.append(_VisualLine(paragraph, None, None))
        offset += _utf16_length(raw_line)
    return tuple(lines)


def _group_visual_lines(lines: tuple[_VisualLine, ...]) -> tuple[str, ...]:
    """Join wrapped logical lines while preserving gaps and column resets."""

    paragraphs: list[str] = []
    current: list[str] = []
    previous: _VisualLine | None = None

    def flush() -> None:
        if current:
            paragraphs.append(normalize_paragraph(" ".join(current)))
            current.clear()

    for line in lines:
        if not line.text:
            flush()
            previous = None
            continue

        can_compare = (
            previous is not None
            and previous.top is not None
            and previous.bottom is not None
            and line.top is not None
            and line.bottom is not None
        )
        continues = False
        if can_compare:
            previous_height = max(previous.bottom - previous.top, 1.0)
            line_height = max(line.bottom - line.top, 1.0)
            continues = (
                line.top >= previous.top - _VERTICAL_TOLERANCE
                and line.top - previous.bottom
                <= _WRAPPED_LINE_GAP_FACTOR * max(previous_height, line_height)
            )
        if current and not continues:
            flush()
        current.append(line.text)
        previous = line

    flush()
    return tuple(paragraph for paragraph in paragraphs if paragraph)


def _page_blocks(document: QPdfDocument) -> tuple[tuple[str, ...], ...]:
    pages: list[tuple[str, ...]] = []
    block_count = 0
    text_char_count = 0
    for page_index in range(document.pageCount()):
        paragraphs = _group_visual_lines(_visual_lines(document, page_index))
        for paragraph in paragraphs:
            block_count += 1
            if block_count > MAX_BLOCKS:
                raise CorruptBookError("PDF chứa quá nhiều khối văn bản.")
            text_char_count += len(paragraph)
            if text_char_count > MAX_TEXT_CHARS:
                raise CorruptBookError("PDF có nội dung đọc quá dài.")
        pages.append(paragraphs)
    return tuple(pages)


def _valid_outline_ranges(
    document: QPdfDocument,
    page_count: int,
) -> tuple[tuple[str, int, int], ...]:
    try:
        model = QPdfBookmarkModel()
        model.setDocument(document)
        root = QModelIndex()
        entries: list[tuple[str, int]] = []
        for row in range(model.rowCount(root)):
            index = model.index(row, 0, root)
            title = normalize_paragraph(
                str(model.data(index, QPdfBookmarkModel.Role.Title) or "")
            )
            page_number = model.data(index, QPdfBookmarkModel.Role.Page)
            if (
                not title
                or len(title) > MAX_TITLE_CHARS
                or not isinstance(page_number, int)
                or isinstance(page_number, bool)
                or page_number < 0
                or page_number >= page_count
            ):
                return ()
            if entries and page_number <= entries[-1][1]:
                return ()
            entries.append((title, page_number))
    except (RuntimeError, TypeError, ValueError):
        return ()

    if not entries or entries[0][1] != 0:
        return ()
    return tuple(
        (
            title,
            start,
            entries[index + 1][1] if index + 1 < len(entries) else page_count,
        )
        for index, (title, start) in enumerate(entries)
    )


def _chapter_specs(
    document: QPdfDocument,
    pages: tuple[tuple[str, ...], ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    ranges = _valid_outline_ranges(document, len(pages))
    if ranges:
        return tuple(
            (title, tuple(text for page in pages[start:end] for text in page))
            for title, start, end in ranges
        )
    return tuple((f"Trang {index + 1}", blocks) for index, blocks in enumerate(pages))


def _open_document(source: Path) -> QPdfDocument:
    document = QPdfDocument()
    error = document.load(str(source))
    if error in (
        QPdfDocument.Error.IncorrectPassword,
        QPdfDocument.Error.UnsupportedSecurityScheme,
    ):
        document.close()
        raise CorruptBookError("PDF được bảo vệ bằng mật khẩu nên không thể đọc.")
    if error != QPdfDocument.Error.None_:
        document.close()
        raise CorruptBookError("Không thể đọc tệp PDF bị hỏng.")
    return document


def import_pdf(path: Path) -> BookDocument:
    """Import text from a PDF, rejecting scans that require OCR."""

    source = Path(path)
    document: QPdfDocument | None = None
    try:
        source_hash = _file_hash(source)
        document = _open_document(source)
        if document.pageCount() < 1 or document.pageCount() > MAX_PAGES:
            raise CorruptBookError("PDF có số trang không hợp lệ hoặc vượt giới hạn.")

        pages = _page_blocks(document)
        non_whitespace_count = sum(
            1
            for page in pages
            for paragraph in page
            for character in paragraph
            if not character.isspace()
        )
        if non_whitespace_count < MIN_NON_WHITESPACE_CHARS:
            raise CorruptBookError(
                "PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR."
            )

        book_id = stable_id(source_hash, "pdf")
        chapters: list[Chapter] = []
        for title, paragraphs in _chapter_specs(document, pages):
            speech_parts = tuple(
                (part, "block" if part_index == 0 else "split")
                for paragraph in paragraphs
                for part_index, part in enumerate(
                    split_paragraph(
                        paragraph,
                        max_chars=SPEECH_SEGMENT_MAX_CHARS,
                    )
                )
            )
            if not speech_parts:
                continue
            chapter_ordinal = len(chapters)
            chapter_id = stable_id(book_id, "chapter", str(chapter_ordinal))
            segments = tuple(
                Segment(
                    id=stable_id(chapter_id, "segment", str(segment_ordinal)),
                    chapter_id=chapter_id,
                    ordinal=segment_ordinal,
                    text=text,
                    joint=joint,
                )
                for segment_ordinal, (text, joint) in enumerate(speech_parts)
            )
            chapters.append(
                Chapter(
                    id=chapter_id,
                    title=title,
                    ordinal=chapter_ordinal,
                    segments=segments,
                )
            )

        if not chapters:
            raise CorruptBookError(
                "PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR."
            )
        return BookDocument(
            id=book_id,
            title=_document_title(document, source.stem),
            source_format="pdf",
            source_hash=source_hash,
            chapters=tuple(chapters),
        )
    except CorruptBookError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise CorruptBookError("Không thể đọc tệp PDF bị hỏng.") from error
    finally:
        if document is not None:
            document.close()
