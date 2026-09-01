from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.domain.models import stable_id
from vieneu_reader.importers.errors import CorruptBookError
from vieneu_reader.importers.pdf import (
    _VisualLine,
    _group_visual_lines,
    import_pdf,
)

from tests.importers.pdf_fixture import (
    make_blank_pdf,
    make_encrypted_pdf,
    make_short_pdf,
    make_pdf,
    make_text_pdf,
)


class PdfImporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_imports_visual_lines_by_page_and_reading_position(self) -> None:
        path = make_text_pdf(self.directory)

        book = import_pdf(path)

        self.assertEqual(book.title, "Sách đọc thử")
        self.assertEqual([chapter.title for chapter in book.chapters], ["Mở đầu", "Tiếp theo"])
        self.assertEqual(
            [segment.text for chapter in book.chapters for segment in chapter.segments],
            [
                "Ben trai cua dong dau tien. Ben phai cua dong dau tien.",
                "Noi dung o phia duoi trang mot.",
                "Noi dung cua trang hai du dai.",
            ],
        )

    def test_split_parts_remember_they_continue_their_paragraph(self) -> None:
        long_paragraph = "Cau van kha dai va duoc lap lai nhieu lan de vuot qua cua so doc. " * 5
        path = make_pdf(
            self.directory / "dai.pdf",
            pages=(
                (
                    (50, 720, long_paragraph.strip()),
                    (50, 662, "Doan van moi."),
                ),
            ),
        )

        book = import_pdf(path)

        segments = book.chapters[0].segments
        self.assertEqual(len(segments), 3)
        self.assertEqual([segment.joint for segment in segments], ["block", "split", "block"])
        self.assertEqual({segment.kind for segment in segments}, {"paragraph"})

    def test_wrapped_lines_merge_but_large_gaps_and_column_resets_split(self) -> None:
        lines = (
            _VisualLine("Dòng đầu", top=10, bottom=20),
            _VisualLine("được xuống hàng", top=22, bottom=32),
            _VisualLine("Đoạn cách xa", top=60, bottom=70),
            _VisualLine("Cột mới", top=8, bottom=18),
        )

        self.assertEqual(
            _group_visual_lines(lines),
            ("Dòng đầu được xuống hàng", "Đoạn cách xa", "Cột mới"),
        )

    def test_without_valid_outline_uses_one_chapter_per_page(self) -> None:
        path = make_text_pdf(self.directory, with_outline=False)

        book = import_pdf(path)

        self.assertEqual([chapter.title for chapter in book.chapters], ["Trang 1", "Trang 2"])
        self.assertEqual([len(chapter.segments) for chapter in book.chapters], [2, 1])

    def test_ids_are_stable_and_derived_from_file_hash_and_order(self) -> None:
        path = make_text_pdf(self.directory)

        first = import_pdf(path)
        second = import_pdf(path)

        self.assertEqual(first, second)
        self.assertEqual(first.id, stable_id(first.source_hash, "pdf"))
        for chapter_index, chapter in enumerate(first.chapters):
            self.assertEqual(chapter.id, stable_id(first.id, "chapter", str(chapter_index)))
            for segment_index, segment in enumerate(chapter.segments):
                self.assertEqual(
                    segment.id,
                    stable_id(chapter.id, "segment", str(segment_index)),
                )

    def test_textless_pdf_reports_that_ocr_is_not_supported(self) -> None:
        path = make_blank_pdf(self.directory / "scan.pdf")

        with self.assertRaisesRegex(
            CorruptBookError,
            r"^PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR\.$",
        ):
            import_pdf(path)

    def test_pdf_with_fewer_than_twenty_non_whitespace_characters_is_textless(self) -> None:
        path = make_short_pdf(self.directory / "gan-trong.pdf")

        with self.assertRaisesRegex(CorruptBookError, "chưa hỗ trợ OCR"):
            import_pdf(path)

    def test_encrypted_pdf_is_rejected_with_a_safe_error(self) -> None:
        path = make_encrypted_pdf(self.directory / "khoa.pdf")

        with self.assertRaisesRegex(CorruptBookError, "mật khẩu"):
            import_pdf(path)

    def test_corrupt_pdf_is_rejected_with_a_safe_error(self) -> None:
        path = self.directory / "hong.pdf"
        path.write_bytes(b"not a pdf")

        with self.assertRaisesRegex(CorruptBookError, "PDF bị hỏng"):
            import_pdf(path)


if __name__ == "__main__":
    unittest.main()
