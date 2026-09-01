"""Bounded text-layer PDF import through pdfium.

This used to run on the bundled QtPdf. The engine now also lives as a headless
sidecar with no Qt runtime, so extraction moved to pypdfium2 - same guards,
same errors, same grouping behaviour. One difference matters: pdfium reports
text rectangles in content-stream order, not layout order, so visual lines are
explicitly sorted by position before grouping (a PDF may draw the right half
of a line first).
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pypdfium2 as pdfium

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
    left: float = 0.0


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _document_title(document: "pdfium.PdfDocument", fallback: str) -> str:
    try:
        raw_title = document.get_metadata_value("Title") or ""
    except pdfium.PdfiumError:
        raw_title = ""
    title = normalize_paragraph(str(raw_title)) or fallback
    if len(title) > MAX_TITLE_CHARS:
        raise CorruptBookError("PDF có tiêu đề quá dài.")
    return title


def _visual_lines(
    document: "pdfium.PdfDocument", page_index: int
) -> tuple[_VisualLine, ...]:
    page = document[page_index]
    text_page = page.get_textpage()
    try:
        _, page_height = page.get_size()
        lines: list[_VisualLine] = []
        for rect_index in range(text_page.count_rects()):
            left, bottom, right, top = text_page.get_rect(rect_index)
            paragraph = normalize_paragraph(
                text_page.get_text_bounded(left, bottom, right, top)
            )
            if not paragraph:
                continue
            # PDF coordinates grow upward; the grouping logic thinks in
            # screen coordinates where a smaller top is higher on the page.
            lines.append(
                _VisualLine(
                    paragraph,
                    top=float(page_height - top),
                    bottom=float(page_height - bottom),
                    left=float(left),
                )
            )
        lines.sort(key=lambda line: (line.top, line.left))
        return tuple(lines)
    finally:
        text_page.close()
        page.close()


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


def _page_blocks(document: "pdfium.PdfDocument") -> tuple[tuple[str, ...], ...]:
    pages: list[tuple[str, ...]] = []
    block_count = 0
    text_char_count = 0
    for page_index in range(len(document)):
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
    document: "pdfium.PdfDocument",
    page_count: int,
) -> tuple[tuple[str, int, int], ...]:
    try:
        entries: list[tuple[str, int]] = []
        for bookmark in document.get_toc(max_depth=1):
            title = normalize_paragraph(str(bookmark.get_title() or ""))
            destination = bookmark.get_dest()
            page_number = destination.get_index() if destination else None
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
    except (pdfium.PdfiumError, RuntimeError, TypeError, ValueError):
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
    document: "pdfium.PdfDocument",
    pages: tuple[tuple[str, ...], ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    ranges = _valid_outline_ranges(document, len(pages))
    if ranges:
        return tuple(
            (title, tuple(text for page in pages[start:end] for text in page))
            for title, start, end in ranges
        )
    return tuple((f"Trang {index + 1}", blocks) for index, blocks in enumerate(pages))


def _open_document(source: Path) -> "pdfium.PdfDocument":
    try:
        return pdfium.PdfDocument(str(source))
    except pdfium.PdfiumError as error:
        if "password" in str(error).lower():
            raise CorruptBookError(
                "PDF được bảo vệ bằng mật khẩu nên không thể đọc."
            ) from error
        raise CorruptBookError("Không thể đọc tệp PDF bị hỏng.") from error


def import_pdf(path: Path) -> BookDocument:
    """Import text from a PDF, rejecting scans that require OCR."""

    source = Path(path)
    document: "pdfium.PdfDocument | None" = None
    try:
        source_hash = _file_hash(source)
        document = _open_document(source)
        if len(document) < 1 or len(document) > MAX_PAGES:
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
