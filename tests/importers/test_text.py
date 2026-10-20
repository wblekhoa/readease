"""Text documents as books (RE-LIB-011)."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from vieneu_reader.config import AppPaths
from vieneu_reader.importers.errors import CorruptBookError
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.importers.text import (
    import_doc, import_docx, import_html, import_md, import_odt, import_rtf, import_txt,
)
from vieneu_reader.storage.repository import LibraryRepository


def outline(book):
    return [(chapter.title, [segment.text for segment in chapter.segments]) for chapter in book.chapters]


def make_docx(path: Path, paragraphs: list[tuple[str | None, str]], title: str | None = None) -> Path:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(
        f'<w:p>{f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""}'
        f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
        for style, text in paragraphs
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        archive.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>')
        if title:
            archive.writestr("docProps/core.xml", f'<?xml version="1.0"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title></cp:coreProperties>')
    return path


class TextImportTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def file(self, name: str, content: str | bytes) -> Path:
        path = self.root / name
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    # RE-LIB-011
    def test_plain_text_reads_paragraphs_and_chapter_lines(self):
        book = import_txt(self.file("Mùa thu.txt", "Lời mở đầu,\nxuống dòng mềm.\n\nChương 1: Hà Nội\n\nPhố nhỏ.\n\nChương 2\n\nLá vàng."))
        self.assertEqual(book.title, "Mùa thu")
        self.assertEqual(book.source_format, "txt")
        self.assertEqual(outline(book), [
            ("Mùa thu", ["Lời mở đầu, xuống dòng mềm."]),
            ("Chương 1: Hà Nội", ["Phố nhỏ."]),
            ("Chương 2", ["Lá vàng."]),
        ])

    # RE-LIB-011
    def test_sentences_that_open_like_a_chapter_word_are_read_not_dropped(self):
        book = import_txt(self.file("a.txt", "Hồi đó tôi mới mười tuổi.\n\nChương trình học rất nặng.\n\nPhần còn lại để sau."))
        self.assertEqual(outline(book), [("a", ["Hồi đó tôi mới mười tuổi.", "Chương trình học rất nặng.", "Phần còn lại để sau."])])

    def test_a_contents_list_of_chapter_lines_is_kept_as_text(self):
        book = import_txt(self.file("b.txt", "Chương 1\n\nChương 2\n\nChương 1\n\nMở đầu.\n\nChương hai: Kết\n\nHết."))
        self.assertEqual(outline(book), [
            ("b", ["Chương 1", "Chương 2"]), ("Chương 1", ["Mở đầu."]), ("Chương hai: Kết", ["Hết."]),
        ])

    def test_html_marked_hidden_is_not_read(self):
        book = import_html(self.file("h.html", '<p>Đọc <span aria-hidden="true">ICON</span>cái này.</p><div hidden>BÍ MẬT</div><p>Tiếp <img hidden src="x"> theo.</p>'))
        self.assertEqual(outline(book), [("h", ["Đọc cái này.", "Tiếp theo."])])

    # RE-LIB-011
    def test_utf16_and_a_bom_are_read_and_legacy_encodings_refused(self):
        self.assertEqual(outline(import_txt(self.file("a.txt", "Xin chào".encode("utf-16"))))[0][1], ["Xin chào"])
        self.assertEqual(outline(import_txt(self.file("b.txt", b"\xef\xbb\xbfXin ch\xc3\xa0o")))[0][1], ["Xin chào"])
        # VNI/TCVN3-era bytes are not UTF-8: refused in words, never guessed.
        with self.assertRaisesRegex(CorruptBookError, "UTF-8"):
            import_txt(self.file("c.txt", b"Xin ch\xe0o"))

    # RE-LIB-011
    def test_an_empty_document_is_refused(self):
        with self.assertRaisesRegex(CorruptBookError, "không có chữ"):
            import_txt(self.file("empty.txt", "  \n\n "))

    # RE-LIB-011
    def test_markdown_keeps_words_and_drops_markup(self):
        source = "\n".join([
            "---", "title: ignored", "---",
            "# Sổ tay đọc sách",
            "Đọc **chậm** và [ghi chú](https://example.com). ![bìa](cover.png)",
            "",
            "## Thói quen",
            "- Mỗi ngày `20` phút",
            "- Một cuốn mỗi tháng",
            "",
            "```", "print('không đọc')", "```",
            "> Trích dẫn hay.",
            "| Cột A | Cột B |", "|---|---|", "| một | hai |",
        ])
        book = import_md(self.file("notes.md", source))
        self.assertEqual(book.title, "Sổ tay đọc sách")
        self.assertEqual(outline(book), [
            ("Sổ tay đọc sách", ["Đọc chậm và ghi chú."]),
            ("Thói quen", ["Mỗi ngày 20 phút", "Một cuốn mỗi tháng", "Trích dẫn hay.", "Cột A, Cột B", "một, hai"]),
        ])

    # RE-LIB-011
    def test_html_reads_headings_and_skips_scripts(self):
        markup = ("<html><head><title>Trang thử</title><style>p{}</style></head><body>"
                  "<nav>Menu</nav><p>Mở đầu &amp; giới thiệu.</p><script>alert(1)</script>"
                  "<h2>Phần một</h2><p>Đoạn <b>đậm</b>.</p><ul><li>Ý một</li><li>Ý hai</li></ul></body></html>")
        book = import_html(self.file("page.html", markup))
        self.assertEqual(book.title, "Trang thử")
        self.assertEqual(outline(book), [
            ("Trang thử", ["Mở đầu & giới thiệu."]),
            ("Phần một", ["Đoạn đậm.", "Ý một", "Ý hai"]),
        ])

    # RE-LIB-011
    def test_docx_headings_become_chapters(self):
        path = make_docx(self.root / "báo cáo.docx", [
            ("Title", "Báo cáo quý"), (None, "Tóm tắt."),
            ("Heading1", "Doanh thu"), (None, "Tăng 12%."), ("Heading3", "Chi tiết"), (None, "Theo vùng."),
        ])
        book = import_docx(path)
        self.assertEqual((book.title, book.source_format), ("Báo cáo quý", "docx"))
        self.assertEqual(outline(book), [
            ("Báo cáo quý", ["Tóm tắt."]),
            ("Doanh thu", ["Tăng 12%.", "Chi tiết", "Theo vùng."]),
        ])

    def test_a_docx_that_is_not_a_zip_is_refused(self):
        with self.assertRaises(CorruptBookError):
            import_docx(self.file("fake.docx", "not a zip"))

    def test_a_docx_with_an_entity_declaration_is_refused(self):
        path = self.root / "bomb.docx"
        with ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]><d>&a;</d>')
        with self.assertRaises(CorruptBookError):
            import_docx(path)

    # RE-LIB-011
    @unittest.skipUnless(shutil.which("textutil"), "macOS textutil")
    def test_doc_rtf_and_odt_go_through_textutil(self):
        html = self.file("source.html", "<html><body><p>Xin chào, đây là tài liệu.</p><p>Đoạn thứ hai.</p></body></html>")
        for fmt, importer in (("doc", import_doc), ("rtf", import_rtf), ("odt", import_odt)):
            target = self.root / f"tài liệu.{fmt}"
            subprocess.run(["textutil", "-inputencoding", "UTF-8", "-convert", fmt, "-output", str(target), str(html)], check=True)
            book = importer(target)
            self.assertEqual(book.source_format, fmt)
            words = " ".join(text for _, texts in outline(book) for text in texts)
            self.assertIn("Xin chào, đây là tài liệu.", words, fmt)
            self.assertIn("Đoạn thứ hai.", words, fmt)

    @unittest.skipUnless(shutil.which("textutil"), "macOS textutil")
    def test_a_damaged_rtf_is_refused(self):
        with self.assertRaises(CorruptBookError):
            import_rtf(self.file("broken.rtf", b"\x00\x01\x02 not rtf"))


class TextBooksInTheLibraryTests(unittest.TestCase):
    # RE-LIB-011
    def test_a_markdown_book_is_managed_reopened_and_reimported_as_the_same_book(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            paths = AppPaths.create(root / "app-data")
            repository = LibraryRepository(paths.database)
            self.addCleanup(repository.close)
            service = LibraryService(paths, repository)
            source = root / "ghi chú.md"
            source.write_text("# Ghi chú\n\nMột đoạn để đọc.", encoding="utf-8")
            first = service.import_book(source)
            self.assertFalse(first.was_existing)
            self.assertEqual(first.managed_path.suffix, ".md")
            stored = repository.get_book(first.book.id)
            self.assertEqual(stored.book.source_format, "md")
            self.assertEqual(stored.book.chapters[0].segments[0].text, "Một đoạn để đọc.")
            self.assertTrue(service.import_book(source).was_existing)

    def test_a_document_without_headings_names_its_chapter_after_the_file(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            paths = AppPaths.create(root / "app-data")
            repository = LibraryRepository(paths.database)
            self.addCleanup(repository.close)
            source = root / "Nhật ký.txt"
            source.write_text("Chỉ một đoạn.", encoding="utf-8")
            book = LibraryService(paths, repository).import_book(source).book
            self.assertEqual((book.title, book.chapters[0].title), ("Nhật ký", "Nhật ký"))


if __name__ == "__main__":
    unittest.main()
