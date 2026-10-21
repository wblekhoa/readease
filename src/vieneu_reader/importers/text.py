"""Text documents as books (RE-LIB-011): plain text, Markdown, HTML, Word,
RTF and OpenDocument.

Every format here ends the same way: a title, and sections of paragraphs -
a heading starts a chapter, and a document without headings is one chapter
under its own title. Plain text, Markdown, HTML and .docx are read with the
standard library alone; .doc, .rtf and .odt go through macOS's own
`textutil`, which converts them to HTML for the same HTML reader, so their
headings survive too.

Guards, like the other importers': a source bound before anything is
decoded, a refusal in words rather than a guess when the bytes are in an
encoding this cannot know (a legacy VNI/TCVN3 file must not turn into
confident gibberish read aloud), and the same paragraph and segment limits.
"""

from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata
import zlib
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from vieneu_reader.domain.models import BookDocument, Chapter, Segment, stable_id
from vieneu_reader.domain.segmenter import normalize_paragraph, split_paragraph

from .epub import _refuse_internal_subset
from .errors import CorruptBookError

#: A 20 MB text is several thousand pages; past that an import would only hang.
MAX_TEXT_SOURCE_BYTES = 20 * 1024 * 1024
#: Word's main part, uncompressed: generous, and still bounded before parsing.
MAX_DOCX_DOCUMENT_BYTES = 100 * 1024 * 1024
MAX_DOCX_XML_ELEMENTS = 5_000_000
MAX_BOOK_CHAPTERS = 2_000
MAX_BOOK_SEGMENTS = 100_000
MAX_TITLE_CHARS = 500
SPEECH_SEGMENT_MAX_CHARS = 240
TEXTUTIL = "/usr/bin/textutil"
TEXTUTIL_TIMEOUT_SECONDS = 120

Section = tuple[str | None, list[str]]


# ---- shared ---------------------------------------------------------------

def _read_bounded(path: Path, limit: int = MAX_TEXT_SOURCE_BYTES) -> bytes:
    try:
        with open(path, "rb") as handle:
            payload = handle.read(limit + 1)
    except OSError as error:
        raise CorruptBookError("Không thể đọc tệp đã chọn.") from error
    if len(payload) > limit:
        raise CorruptBookError(
            "Tài liệu văn bản vượt giới hạn 20 MB." if limit == MAX_TEXT_SOURCE_BYTES
            else "Tài liệu vượt giới hạn an toàn."
        )
    return payload


def _decode(payload: bytes) -> str:
    """UTF-8 (with or without a BOM) or UTF-16 with its BOM; anything else
    is refused - a guessed legacy encoding would be read aloud as nonsense."""

    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return payload.decode("utf-16")
        except UnicodeDecodeError as error:
            raise CorruptBookError("Tệp UTF-16 bị hỏng.") from error
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CorruptBookError(
            "Chưa đọc được bảng mã của tệp này. Hãy lưu lại tệp ở dạng UTF-8 rồi nhập lại."
        ) from error
    if "\x00" in text:
        raise CorruptBookError(
            "Chưa đọc được bảng mã của tệp này. Hãy lưu lại tệp ở dạng UTF-8 rồi nhập lại."
        )
    return text


def _title(value: str | None, fallback: str) -> str:
    title = normalize_paragraph(value or "")
    return (title or normalize_paragraph(fallback) or "Tài liệu")[:MAX_TITLE_CHARS]


#: "Chương 3", "Phần II", "Chapter Twelve", "Hồi thứ nhất": the keyword AND a
#: number - a word or numeral - so "Hồi đó tôi…" or "Chương trình học…" stay
#: sentences. A short title may follow after a colon or dash.
_NUMBER = (r"(?:\d+|[ivxlcdm]+|thứ\s+\w+|một|hai|ba|bốn|tư|năm|sáu|bảy|tám|chín|mười(?:\s+\w+)?"
           r"|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|[a-z]+teen|twenty(?:-\w+)?)")
_TXT_HEADING = re.compile(
    r"^(?:chương|chuong|phần|phan|chapter|part|hồi|quyển)\s+" + _NUMBER + r"[.:]?(?:\s*[:.\-–—]\s*.{1,80})?$",
    re.IGNORECASE,
)
#: "Chương 1 Hà Nội" - a title after the number with only a space: taken
#: when the number is a numeral (not a word like "năm"), the title opens with
#: a capital, and the line does not end like a sentence - so "Hồi 5 giờ sáng
#: tôi dậy." stays text.
_SPACED_HEADING = re.compile(
    r"^(?i:chương|chuong|phần|phan|chapter|part|hồi|quyển)\s+(?:\d+|(?i:[ivxlcdm]+))\s+(\w)[^.!?…]{0,60}$"
)


def _is_chapter_line(line: str) -> bool:
    if len(line) > 100:
        return False
    if _TXT_HEADING.match(line):
        return True
    spaced = _SPACED_HEADING.match(line)
    return bool(spaced and spaced.group(1).isupper())



def _chapter_lines(sections: list[Section]) -> list[Section]:
    """A document that marked no headings - a converted .doc, a typed-up
    .txt - still often has its chapters as short lines of their own
    ("Chương 3: Mùa thu", "Part II"). Those start chapters; nothing else does."""

    if len(sections) != 1:
        return sections
    split: list[Section] = [(sections[0][0], [])]
    for paragraph in sections[0][1]:
        line = normalize_paragraph(paragraph)
        if _is_chapter_line(line):
            if split[-1][0] is not None and not split[-1][1]:
                # Two chapter lines in a row (a contents list): the first had
                # no body, so it is text, never dropped.
                heading, _ = split.pop()
                split[-1][1].append(heading)
            split.append((line, []))
        else:
            split[-1][1].append(paragraph)
    if len(split) > 1 and not split[-1][1]:
        heading, _ = split.pop()
        split[-1][1].append(heading)
    return split


def _book(source_format: str, source_hash: str, title: str, sections: list[Section]) -> BookDocument:
    sections = _chapter_lines(sections)
    book_id = stable_id(source_hash, source_format)
    chapters: list[Chapter] = []
    total_segments = 0
    for heading, paragraphs in sections:
        parts = tuple(
            (part, "block" if index == 0 else "split")
            for raw in paragraphs
            if (paragraph := normalize_paragraph(raw))
            for index, part in enumerate(split_paragraph(paragraph, max_chars=SPEECH_SEGMENT_MAX_CHARS))
        )
        if not parts:
            continue
        if len(chapters) >= MAX_BOOK_CHAPTERS:
            raise CorruptBookError("Tài liệu có quá nhiều chương.")
        total_segments += len(parts)
        if total_segments > MAX_BOOK_SEGMENTS:
            raise CorruptBookError("Tài liệu quá dài để nhập.")
        ordinal = len(chapters)
        chapter_id = stable_id(book_id, "chapter", str(ordinal))
        chapters.append(Chapter(
            id=chapter_id,
            title=_title(heading, title),
            ordinal=ordinal,
            segments=tuple(
                Segment(id=stable_id(chapter_id, "segment", str(index)), chapter_id=chapter_id,
                        ordinal=index, text=text, joint=joint)
                for index, (text, joint) in enumerate(parts)
            ),
        ))
    if not chapters:
        raise CorruptBookError("Tài liệu không có chữ để đọc.")
    return BookDocument(id=book_id, title=title, source_format=source_format,  # type: ignore[arg-type]
                        source_hash=source_hash, chapters=tuple(chapters))


def _paragraphs(block: str) -> list[str]:
    """Blank lines separate paragraphs; single line breaks are soft wraps."""

    return [part for part in re.split(r"\n\s*\n", block) if part.strip()]


# ---- plain text -------------------------------------------------------------



def import_txt(path: Path) -> BookDocument:
    source = Path(path)
    payload = _read_bounded(source)
    text = unicodedata.normalize("NFC", _decode(payload)).replace("\r\n", "\n").replace("\r", "\n")
    # "Chương 3: Mùa thu" alone in its paragraph starts a chapter (`_chapter_lines`).
    sections: list[Section] = [(None, _paragraphs(text))]
    return _book("txt", sha256(payload).hexdigest(), _title(None, source.stem), sections)


# ---- Markdown ---------------------------------------------------------------

_FRONT_MATTER = re.compile(r"\A---[ \t]*\n.*?\n(?:---|\.\.\.)[ \t]*(?:\n|\Z)", re.DOTALL)
_FENCE = re.compile(r"^(```|~~~)")
_ATX = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_RULE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?")
_QUOTE = re.compile(r"^\s*>\s?")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _markdown_inline(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", "", text)          # images: nothing to hear
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)         # links: their words
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    text = re.sub(r"<https?://[^>]+>", "", text)
    text = re.sub(r"<[^>]+>", "", text)                           # inline HTML
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?<![\w*])([*_])(?!\s)(.+?)(?<!\s)\1(?![\w*])", r"\2", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    return text.replace("\\", "")


def markdown_sections(text: str) -> tuple[str | None, list[Section]]:
    text = _FRONT_MATTER.sub("", text.replace("\r\n", "\n").replace("\r", "\n"), count=1)
    title: str | None = None
    sections: list[Section] = [(None, [])]
    paragraph: list[str] = []
    fenced = False

    def flush() -> None:
        if paragraph:
            sections[-1][1].append(" ".join(paragraph))
            paragraph.clear()

    lines = text.split("\n")
    for index, line in enumerate(lines):
        if _FENCE.match(line.strip()):
            flush()
            fenced = not fenced          # code is not read aloud
            continue
        if fenced:
            continue
        heading = _ATX.match(line)
        setext = (index + 1 < len(lines) and line.strip() and not paragraph
                  and re.fullmatch(r"\s*(=+|-+)\s*", lines[index + 1] or "") and not _RULE.match(line))
        if heading or setext:
            flush()
            level = len(heading.group(1)) if heading else (1 if lines[index + 1].strip().startswith("=") else 2)
            words = normalize_paragraph(_markdown_inline(heading.group(2) if heading else line))
            if setext:
                lines[index + 1] = ""
            # A first "# Chương 1" is the first chapter, not the book's name.
            if level == 1 and title is None and not any(paras for _, paras in sections) and not _is_chapter_line(words):
                title = words
                continue
            if level <= 2:
                sections.append((words, []))
            else:
                sections[-1][1].append(words)
            continue
        if not line.strip() or _RULE.match(line) or _TABLE_RULE.match(line):
            flush()
            continue
        item = _LIST.match(line)
        if item:
            flush()
            line = line[item.end():]
        line = _QUOTE.sub("", line)
        row = line.strip().startswith("|")
        if row:
            # One table row, one paragraph: its cells read as a list.
            flush()
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            line = ", ".join(cell for cell in cells if cell)
        paragraph.append(_markdown_inline(line).strip())
        if item or row:
            flush()
    flush()
    return title, sections


def import_md(path: Path) -> BookDocument:
    source = Path(path)
    payload = _read_bounded(source)
    title, sections = markdown_sections(unicodedata.normalize("NFC", _decode(payload)))
    return _book("md", sha256(payload).hexdigest(), _title(title, source.stem), sections)


# ---- HTML (and what textutil converts to it) --------------------------------

_BLOCKS = {"p", "div", "li", "dt", "dd", "blockquote", "pre", "tr", "section", "article",
           "header", "footer", "figcaption", "table", "ul", "ol", "dl", "br", "hr",
           "h3", "h4", "h5", "h6", "td", "th", "caption"}
_VOID = {"br", "hr", "img", "input", "meta", "link", "wbr", "source", "area", "col", "embed"}
_SKIPPED = {"script", "style", "noscript", "template", "svg", "math", "head", "nav", "button", "select", "textarea"}


class _HtmlText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.first_h1: str | None = None
        self.sections: list[Section] = [(None, [])]
        self._skip = 0
        self._hidden: list[str] = []
        self._in_title = False
        self._heading: list[str] | None = None
        self._buffer: list[str] = []
        self._cells = False

    def _flush(self) -> None:
        text = "".join(self._buffer)
        self._buffer.clear()
        if text.strip():
            self.sections[-1][1].append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag in _SKIPPED:
            self._skip += 1
            return
        if tag not in _VOID and any(name == "hidden" or (name == "aria-hidden" and value == "true") for name, value in attrs):
            # Hidden from the page, so not read: skipped until its own end tag.
            self._hidden.append(tag)
            self._skip += 1
            return
        if tag in {"h1", "h2"}:
            self._flush()
            self._heading = []
        elif tag in {"td", "th"} and self._buffer and "".join(self._buffer).strip():
            self._buffer.append(", ")
        elif tag in _BLOCKS and tag not in {"td", "th"}:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if self._hidden and tag == self._hidden[-1]:
            self._hidden.pop()
            self._skip = max(0, self._skip - 1)
            return
        if tag in _SKIPPED:
            self._skip = max(0, self._skip - 1)
            return
        if tag in {"h1", "h2"} and self._heading is not None:
            words = normalize_paragraph("".join(self._heading))
            self._heading = None
            if words:
                if tag == "h1" and self.first_h1 is None and not any(p for _, p in self.sections) and not _is_chapter_line(words):
                    self.first_h1 = words
                else:
                    self.sections.append((words, []))
        elif tag in _BLOCKS and tag not in {"td", "th"}:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title or "") + data
            return
        if self._skip:
            return
        (self._heading if self._heading is not None else self._buffer).append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def html_sections(markup: str) -> tuple[str | None, list[Section]]:
    reader = _HtmlText()
    try:
        reader.feed(markup)
        reader.close()
    except (ValueError, AssertionError) as error:
        raise CorruptBookError("Tệp HTML bị hỏng.") from error
    title = normalize_paragraph(reader.title or "") or reader.first_h1
    return title, reader.sections


def import_html(path: Path) -> BookDocument:
    source = Path(path)
    payload = _read_bounded(source)
    title, sections = html_sections(unicodedata.normalize("NFC", _decode(payload)))
    return _book("html", sha256(payload).hexdigest(), _title(title, source.stem), sections)


# ---- Word (.docx) ------------------------------------------------------------

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_HEADING_STYLE = re.compile(r"^(?:heading|tieude|titre|überschrift|ueberschrift)\s*([12])$|^title$", re.IGNORECASE)


def _docx_title(archive: ZipFile) -> str | None:
    try:
        info = archive.getinfo("docProps/core.xml")
    except KeyError:
        return None
    if info.file_size > 1024 * 1024:
        return None
    try:
        payload = archive.read(info)
    except (BadZipFile, zlib.error, EOFError, OSError):
        return None
    _refuse_internal_subset(payload, "DOCX")
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return None
    found = root.find("{http://purl.org/dc/elements/1.1/}title")
    return found.text if found is not None and found.text else None


def import_docx(path: Path) -> BookDocument:
    source = Path(path)
    try:
        payload = _read_bounded(source, 200 * 1024 * 1024)
        archive = ZipFile(BytesIO(payload))
        info = archive.getinfo("word/document.xml")
    except (BadZipFile, KeyError) as error:
        raise CorruptBookError("Tệp Word (.docx) bị hỏng hoặc không đúng định dạng.") from error
    if info.file_size > MAX_DOCX_DOCUMENT_BYTES:
        raise CorruptBookError("Tệp Word vượt giới hạn an toàn.")
    try:
        document = archive.read(info)
    except (BadZipFile, zlib.error, EOFError, OSError) as error:
        raise CorruptBookError("Tệp Word (.docx) bị hỏng.") from error
    _refuse_internal_subset(document, "DOCX")
    sections: list[Section] = [(None, [])]
    title: str | None = _docx_title(archive)
    seen = 0
    try:
        for event, element in ElementTree.iterparse(BytesIO(document), events=("end",)):
            seen += 1
            if seen > MAX_DOCX_XML_ELEMENTS:
                raise CorruptBookError("Tệp Word có XML quá phức tạp.")
            if element.tag != f"{_W}p":
                continue
            style = element.find(f"{_W}pPr/{_W}pStyle")
            style_id = (style.get(f"{_W}val") or "") if style is not None else ""
            pieces: list[str] = []
            for node in element.iter():
                if node.tag == f"{_W}t" and node.text:
                    pieces.append(node.text)
                elif node.tag in {f"{_W}tab", f"{_W}br", f"{_W}cr"}:
                    pieces.append(" ")
            element.clear()
            words = normalize_paragraph("".join(pieces))
            if not words:
                continue
            heading = _HEADING_STYLE.match(style_id.replace(" ", ""))
            if heading and heading.group(1) is None:      # the Title style
                if title is None and not any(p for _, p in sections):
                    title = words
                    continue
                sections[-1][1].append(words)
            elif heading:
                sections.append((words, []))
            else:
                sections[-1][1].append(words)
    except ElementTree.ParseError as error:
        raise CorruptBookError("Tệp Word (.docx) bị hỏng.") from error
    return _book("docx", sha256(payload).hexdigest(), _title(title, source.stem), sections)


# ---- .doc, .rtf, .odt through macOS's textutil -------------------------------

def _textutil_html(path: Path) -> str:
    if not Path(TEXTUTIL).is_file() and shutil.which("textutil") is None:
        raise CorruptBookError("Máy này thiếu công cụ chuyển đổi văn bản của macOS.")
    try:
        done = subprocess.run(
            [TEXTUTIL if Path(TEXTUTIL).is_file() else "textutil",
             "-convert", "html", "-encoding", "UTF-8", "-stdout", "-noload", "-nostore", str(path)],
            capture_output=True, timeout=TEXTUTIL_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise CorruptBookError("Chuyển đổi tài liệu mất quá lâu.") from error
    except OSError as error:
        raise CorruptBookError("Không chuyển đổi được tài liệu.") from error
    if done.returncode != 0 or not done.stdout:
        raise CorruptBookError("Tài liệu bị hỏng hoặc không đúng định dạng.")
    if len(done.stdout) > MAX_DOCX_DOCUMENT_BYTES:
        raise CorruptBookError("Tài liệu vượt giới hạn an toàn.")
    return done.stdout.decode("utf-8", errors="replace")


def _import_converted(path: Path, source_format: str) -> BookDocument:
    source = Path(path)
    payload = _read_bounded(source, 200 * 1024 * 1024)
    title, sections = html_sections(unicodedata.normalize("NFC", _textutil_html(source)))
    return _book(source_format, sha256(payload).hexdigest(), _title(title, source.stem), sections)


def import_doc(path: Path) -> BookDocument:
    return _import_converted(path, "doc")


def import_rtf(path: Path) -> BookDocument:
    return _import_converted(path, "rtf")


def import_odt(path: Path) -> BookDocument:
    return _import_converted(path, "odt")


#: Suffix → parser, in the shape `LibraryService` takes.
TEXT_PARSERS = {
    ".txt": import_txt, ".md": import_md, ".html": import_html, ".docx": import_docx,
    ".doc": import_doc, ".rtf": import_rtf, ".odt": import_odt,
}
TEXT_FORMATS = frozenset(suffix[1:] for suffix in TEXT_PARSERS)
#: Other spellings of the same formats, read as their canonical suffix.
SUFFIX_ALIASES = {".markdown": ".md", ".htm": ".html", ".xhtml": ".html", ".text": ".txt"}
