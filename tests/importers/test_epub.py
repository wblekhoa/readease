import lzma
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import base64
import unittest
from unittest.mock import patch
import zlib

from vieneu_reader.importers import epub as epub_module
from vieneu_reader.importers.epub import import_epub
from vieneu_reader.importers.errors import CorruptBookError
from vieneu_reader.importers.epub_presentation import (
    load_epub_assets,
    load_epub_presentation,
)

from tests.importers.epub_fixture import make_epub, make_png


class EpubImportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_import_records_what_each_block_is_and_how_it_was_cut(self):
        long_paragraph = "Câu văn này khá dài và được lặp lại nhiều lần để vượt cửa sổ đọc. " * 5
        chapter = f"""<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Chương mở đầu</h1>
        <p>{long_paragraph}</p>
        <ul><li>Táo chín.</li><li>Cam ngọt.</li></ul>
        <blockquote>Lời trích dẫn xưa.</blockquote>
        <figure><figcaption>Chú thích một tấm hình.</figcaption></figure>
        </body></html>"""
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
        )

        book = import_epub(path)

        segments = book.chapters[0].segments
        self.assertEqual(
            [segment.kind for segment in segments],
            [
                "heading",
                "paragraph",
                "paragraph",
                "list_item",
                "list_item",
                "quote",
                "caption",
            ],
        )
        self.assertEqual(
            [segment.joint for segment in segments],
            ["block", "block", "split", "block", "block", "block", "block"],
        )

    def test_import_follows_spine_and_excludes_nonreading_content(self):
        path = make_epub(self.root, spine=("chapter-2", "chapter-1"))

        book = import_epub(path)

        self.assertEqual(book.title, "Sách thử nghiệm")
        self.assertEqual(book.source_format, "epub")
        self.assertEqual([chapter.title for chapter in book.chapters], ["Hai", "Một"])
        spoken = " ".join(
            segment.text
            for chapter in book.chapters
            for segment in chapter.segments
        )
        self.assertIn("Nội dung chương hai.", spoken)
        self.assertNotIn("window.alert", spoken)
        self.assertNotIn("display: block", spoken)
        self.assertNotIn("Nội dung ẩn", spoken)
        self.assertNotIn("Cũng bị ẩn", spoken)

    def test_import_preserves_visible_text_outside_semantic_reading_tags(self):
        chapter = """<?xml version="1.0" encoding="utf-8"?>
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head><title>Không đọc tiêu đề HTML</title></head>
          <body>
            Mở đầu trực tiếp.
            <div>Đoạn nằm trực tiếp trong div.</div>
            <p>Đoạn nằm trong thẻ p.</p>
            Đoạn kết trực tiếp.
          </body>
        </html>
        """
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
        )

        book = import_epub(path)

        spoken = " ".join(
            segment.text
            for chapter in book.chapters
            for segment in chapter.segments
        )
        self.assertIn("Mở đầu trực tiếp.", spoken)
        self.assertIn("Đoạn nằm trực tiếp trong div.", spoken)
        self.assertIn("Đoạn nằm trong thẻ p.", spoken)
        self.assertIn("Đoạn kết trực tiếp.", spoken)
        self.assertNotIn("Không đọc tiêu đề HTML", spoken)

    def test_repeated_import_has_identical_domain_identity(self):
        path = make_epub(self.root)

        first = import_epub(path)
        second = import_epub(path)

        self.assertEqual(first, second)
        self.assertEqual(len(first.id), 64)
        self.assertTrue(all(len(chapter.id) == 64 for chapter in first.chapters))
        self.assertTrue(
            all(
                len(segment.id) == 64
                for chapter in first.chapters
                for segment in chapter.segments
            )
        )

    def test_import_preserves_text_and_anchors_meaningful_figures_in_reading_order(self):
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1>
        <p>Đoạn trước hình.</p>
        <div><img src="images/diagram.png" alt="Sơ đồ luồng đọc sách"/></div>
        <p>Đoạn giữa hai hình.</p>
        <div><img src="images/diagram.png" alt="Sơ đồ luồng đọc sách"/></div>
        <p>Đoạn sau hình.</p>
        <div><img src="images/dot.png" alt="Image"/></div>
        <div><img src="images/empty.png" alt=""/></div>
        </body></html>"""
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
            image_entries={
                "images/diagram.png": (make_png(320, 200), "image/png"),
                "images/dot.png": (make_png(10, 10), "image/png"),
                "images/empty.png": (make_png(320, 200), "image/png"),
            },
        )

        book = import_epub(path)
        imported = book.chapters[0]
        original_segments = imported.segments
        presentation = load_epub_presentation(path, book)
        figures = presentation.chapters[0].figures

        self.assertEqual(
            [segment.text for segment in imported.segments],
            ["Một", "Đoạn trước hình.", "Đoạn giữa hai hình.", "Đoạn sau hình."],
        )
        self.assertIs(imported.segments, original_segments)
        self.assertEqual(len(figures), 2)
        first, second = figures
        self.assertEqual((first.number, second.number), (1, 2))
        self.assertEqual(first.asset_path, "OEBPS/images/diagram.png")
        self.assertEqual(first.media_type, "image/png")
        self.assertEqual((first.width, first.height), (320, 200))
        self.assertEqual(first.alt_text, "Sơ đồ luồng đọc sách")
        self.assertFalse(first.alt_is_generic)
        self.assertEqual(first.placement, "after")
        self.assertEqual(first.anchor_segment_id, imported.segments[1].id)
        self.assertEqual(second.anchor_segment_id, imported.segments[2].id)
        self.assertNotEqual(first.id, second.id)

    def test_figure_at_chapter_start_anchors_before_first_text_segment(self):
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <img src="images/cover.png" alt="Minh họa mở đầu"/>
        <h1>Một</h1><p>Nội dung.</p>
        </body></html>"""
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
            image_entries={
                "images/cover.png": (make_png(300, 180), "image/png"),
            },
        )

        book = import_epub(path)
        chapter_model = book.chapters[0]
        figures = load_epub_presentation(path, book).chapters[0].figures

        self.assertEqual(len(figures), 1)
        figure = figures[0]
        self.assertEqual(figure.placement, "before")
        self.assertEqual(figure.anchor_segment_id, chapter_model.segments[0].id)

    def test_generic_alt_is_kept_for_large_images_but_tiny_generic_art_is_suppressed(self):
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1>
        <img src="images/large.png" alt="Image"/>
        <img src="images/tiny.png" alt="Hình"/>
        <p>Nội dung.</p>
        </body></html>"""
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
            image_entries={
                "images/large.png": (make_png(300, 180), "image/png"),
                "images/tiny.png": (make_png(10, 10), "image/png"),
            },
        )

        book = import_epub(path)
        figures = load_epub_presentation(path, book).chapters[0].figures

        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].alt_text, "Image")
        self.assertTrue(figures[0].alt_is_generic)

    def test_load_epub_assets_returns_requested_managed_bytes_without_extraction(self):
        payload = make_png(320, 200)
        path = make_epub(
            self.root,
            image_entries={"images/diagram.png": (payload, "image/png")},
        )

        loaded = load_epub_assets(path, ("OEBPS/images/diagram.png",))

        self.assertEqual(loaded, {"OEBPS/images/diagram.png": payload})
        self.assertFalse((self.root / "diagram.png").exists())

    def test_load_epub_assets_rejects_unsafe_member_names(self):
        path = make_epub(self.root)

        with self.assertRaisesRegex(CorruptBookError, "không an toàn"):
            load_epub_assets(path, ("../outside.png",))

    def test_localized_companion_replaces_immediately_preceding_original(self):
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1>
        <div class="image"><img src="images/original.png" alt="Image"/></div>
        <div class="bs-image-localized-block">
          <div class="image bs-image-companion">
            <img src="images/localized.png" alt="Sơ đồ tiếng Việt"/>
          </div>
          <p class="bs-image-annotation">Chú giải ảnh bằng tiếng Việt.</p>
        </div>
        </body></html>"""
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
            image_entries={
                "images/original.png": (make_png(320, 200), "image/png"),
                "images/localized.png": (make_png(320, 200), "image/png"),
            },
        )
        book = import_epub(path)

        figures = load_epub_presentation(path, book).chapters[0].figures

        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].asset_path, "OEBPS/images/localized.png")
        self.assertEqual(figures[0].alt_text, "Sơ đồ tiếng Việt")

    def test_repeated_spine_member_gets_distinct_chapter_scoped_occurrences(self):
        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1><p>Nội dung.</p>
        <img src="images/diagram.png" alt="Sơ đồ"/>
        </body></html>"""
        path = make_epub(
            self.root,
            spine=("chapter-1", "chapter-1"),
            chapter_overrides={"chapter-1": chapter},
            image_entries={
                "images/diagram.png": (make_png(320, 200), "image/png"),
            },
        )
        book = import_epub(path)

        presentation = load_epub_presentation(path, book)
        first = presentation.chapters[0].figures[0]
        second = presentation.chapters[1].figures[0]

        self.assertEqual((first.number, second.number), (1, 2))
        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first.chapter_id, second.chapter_id)

    def test_overlay_fails_closed_when_stored_segment_text_no_longer_matches(self):
        path = make_epub(self.root)
        book = import_epub(path)
        chapter = book.chapters[0]
        changed = replace(
            book,
            chapters=(
                replace(
                    chapter,
                    segments=(
                        replace(chapter.segments[0], text="Đã thay đổi"),
                        *chapter.segments[1:],
                    ),
                ),
                *book.chapters[1:],
            ),
        )

        with self.assertRaisesRegex(CorruptBookError, "khớp"):
            load_epub_presentation(path, changed)

    def test_jpeg_dimensions_filter_tiny_generic_art_without_decoding(self):
        def jpeg_header(width: int, height: int) -> bytes:
            components = b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
            return (
                b"\xff\xd8\xff\xc0\x00\x11\x08"
                + height.to_bytes(2, "big")
                + width.to_bytes(2, "big")
                + components
                + b"\xff\xd9"
            )

        chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Một</h1><img src="images/tiny.jpg" alt="Image"/>
        <img src="images/large.jpg" alt="Image"/><p>Nội dung.</p>
        </body></html>"""
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
            image_entries={
                "images/tiny.jpg": (jpeg_header(10, 10), "image/jpeg"),
                "images/large.jpg": (jpeg_header(640, 480), "image/jpeg"),
            },
        )
        book = import_epub(path)

        figures = load_epub_presentation(path, book).chapters[0].figures

        self.assertEqual(len(figures), 1)
        self.assertEqual((figures[0].width, figures[0].height), (640, 480))

    def test_invalid_zip_is_reported_as_a_corrupt_book(self):
        path = self.root / "broken.epub"
        path.write_bytes(b"not a zip archive")

        with self.assertRaisesRegex(CorruptBookError, "EPUB"):
            import_epub(path)

    def test_deflate_decoder_failure_is_reported_as_a_corrupt_book(self):
        path = make_epub(self.root, name="corrupt-deflate.epub")

        with patch.object(
            epub_module.ZipFile,
            "read",
            side_effect=zlib.error("invalid compressed data"),
        ):
            with self.assertRaisesRegex(CorruptBookError, "EPUB"):
                import_epub(path)

    def test_lzma_decoder_failure_is_reported_as_a_corrupt_book(self):
        path = make_epub(self.root, name="corrupt-lzma.epub")

        with patch.object(
            epub_module.ZipFile,
            "read",
            side_effect=lzma.LZMAError("corrupt input data"),
        ):
            with self.assertRaisesRegex(CorruptBookError, "EPUB"):
                import_epub(path)

    def test_archive_entry_cannot_escape_the_epub_root(self):
        path = make_epub(self.root, unsafe_entry="../outside.txt")

        with self.assertRaisesRegex(CorruptBookError, "không an toàn"):
            import_epub(path)

        self.assertFalse((self.root / "outside.txt").exists())

    def test_manifest_href_cannot_escape_the_package_root(self):
        path = make_epub(self.root, unsafe_href="../../outside.xhtml")

        with self.assertRaisesRegex(CorruptBookError, "không an toàn"):
            import_epub(path)

    def test_epub_without_readable_spine_content_is_rejected(self):
        path = make_epub(self.root, empty_chapters=True)

        with self.assertRaisesRegex(CorruptBookError, "nội dung đọc"):
            import_epub(path)

    def test_member_size_limit_rejects_oversized_content_before_parsing(self):
        path = make_epub(self.root)

        with patch("vieneu_reader.importers.epub.MAX_MEMBER_BYTES", 64):
            with self.assertRaisesRegex(CorruptBookError, "vượt giới hạn"):
                import_epub(path)

    def test_total_size_limit_rejects_an_oversized_archive(self):
        path = make_epub(self.root)

        with patch("vieneu_reader.importers.epub.MAX_ARCHIVE_BYTES", 256):
            with self.assertRaisesRegex(CorruptBookError, "vượt giới hạn"):
                import_epub(path)

    def test_member_count_limit_rejects_archive_metadata_flood(self):
        path = make_epub(self.root)

        with (
            patch(
                "vieneu_reader.importers.epub.MAX_ARCHIVE_MEMBERS",
                2,
            ),
            patch(
                "vieneu_reader.importers.epub.ZipFile",
                side_effect=AssertionError("ZipFile opened before member preflight"),
            ),
        ):
            with self.assertRaisesRegex(CorruptBookError, "quá nhiều"):
                import_epub(path)

    def test_forged_eocd_count_cannot_bypass_bounded_directory_scan(self):
        path = make_epub(self.root)
        payload = bytearray(path.read_bytes())
        eocd = payload.rfind(b"PK\x05\x06")
        self.assertGreaterEqual(eocd, 0)
        payload[eocd + 8 : eocd + 10] = (1).to_bytes(2, "little")
        payload[eocd + 10 : eocd + 12] = (1).to_bytes(2, "little")
        path.write_bytes(payload)

        with (
            patch("vieneu_reader.importers.epub.MAX_ARCHIVE_MEMBERS", 2),
            patch(
                "vieneu_reader.importers.epub.ZipFile",
                side_effect=AssertionError("forged count reached ZipFile"),
            ),
        ):
            with self.assertRaisesRegex(CorruptBookError, "quá nhiều"):
                import_epub(path)

    def test_inconsistent_eocd_comment_length_is_rejected_before_zipfile(self):
        path = make_epub(self.root)
        payload = bytearray(path.read_bytes())
        eocd = payload.rfind(b"PK\x05\x06")
        self.assertGreaterEqual(eocd, 0)
        payload[eocd + 20 : eocd + 22] = (1).to_bytes(2, "little")
        path.write_bytes(payload)

        with patch(
            "vieneu_reader.importers.epub.ZipFile",
            side_effect=AssertionError("EOCD preflight was skipped"),
        ):
            with self.assertRaisesRegex(CorruptBookError, "mục lục ZIP"):
                import_epub(path)

    def test_manifest_item_limit_is_checked_before_spine_expansion(self):
        path = make_epub(self.root)

        with patch(
            "vieneu_reader.importers.epub.MAX_MANIFEST_ITEMS",
            1,
            create=True,
        ):
            with self.assertRaisesRegex(CorruptBookError, "manifest"):
                import_epub(path)

    def test_spine_item_limit_rejects_repeated_logical_entries(self):
        path = make_epub(
            self.root,
            spine=("chapter-1", "chapter-1", "chapter-1"),
        )

        with patch(
            "vieneu_reader.importers.epub.MAX_SPINE_ITEMS",
            2,
            create=True,
        ):
            with self.assertRaisesRegex(CorruptBookError, "spine"):
                import_epub(path)

    def test_repeated_spine_member_is_parsed_only_once(self):
        path = make_epub(
            self.root,
            spine=("chapter-1", "chapter-1", "chapter-1"),
        )

        with patch(
            "vieneu_reader.importers.epub._parse_xml",
            wraps=epub_module._parse_xml,
        ) as parse_xml:
            book = import_epub(path)

        chapter_parses = [
            call for call in parse_xml.call_args_list if call.args[1] == "EPUB chapter"
        ]
        self.assertEqual(len(book.chapters), 3)
        self.assertEqual(len(chapter_parses), 1)

    def test_generated_segment_limit_bounds_logical_book_size(self):
        path = make_epub(self.root)

        with patch(
            "vieneu_reader.importers.epub.MAX_BOOK_SEGMENTS",
            1,
            create=True,
        ):
            with self.assertRaisesRegex(CorruptBookError, "quá nhiều đoạn"):
                import_epub(path)

    def test_generated_text_limit_bounds_repeated_spine_content(self):
        path = make_epub(
            self.root,
            spine=("chapter-1", "chapter-1"),
        )

        with patch(
            "vieneu_reader.importers.epub.MAX_BOOK_TEXT_CHARS",
            10,
            create=True,
        ):
            with self.assertRaisesRegex(CorruptBookError, "nội dung đọc quá dài"):
                import_epub(path)

    def test_xml_element_limit_rejects_before_reading_blocks_materialize(self):
        paragraphs = "".join("<p>a</p>" for _ in range(20))
        chapter = (
            '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
            f"{paragraphs}</body></html>"
        )
        path = make_epub(
            self.root,
            chapter_overrides={"chapter-1": chapter},
        )

        with (
            patch(
                "vieneu_reader.importers.epub.MAX_XML_ELEMENTS",
                10,
                create=True,
            ),
            patch(
                "vieneu_reader.importers.epub._reading_blocks",
                side_effect=AssertionError("reading blocks materialized before XML cap"),
            ),
        ):
            with self.assertRaisesRegex(CorruptBookError, "XML quá phức tạp"):
                import_epub(path)

    def test_segment_budget_stops_incremental_block_preparation(self):
        paragraphs = "".join("<p>a</p>" for _ in range(100))
        chapter = (
            '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
            f"{paragraphs}</body></html>"
        )
        path = make_epub(
            self.root,
            chapter_overrides={"chapter-1": chapter},
        )

        with (
            patch("vieneu_reader.importers.epub.MAX_BOOK_SEGMENTS", 1),
            patch(
                "vieneu_reader.importers.epub.split_paragraph",
                wraps=epub_module.split_paragraph,
            ) as split,
        ):
            with self.assertRaisesRegex(CorruptBookError, "quá nhiều đoạn"):
                import_epub(path)

        self.assertEqual(split.call_count, 1)

    def test_metadata_title_length_is_bounded(self):
        path = make_epub(self.root, title="T" * 100)

        with patch(
            "vieneu_reader.importers.epub.MAX_TITLE_CHARS",
            10,
            create=True,
        ):
            with self.assertRaisesRegex(CorruptBookError, "tiêu đề quá dài"):
                import_epub(path)

    def test_xml_entity_declarations_are_rejected(self):
        malicious = """<?xml version="1.0"?>
        <!DOCTYPE html [<!ENTITY payload "không an toàn">]>
        <html xmlns="http://www.w3.org/1999/xhtml"><body><p>&payload;</p></body></html>
        """
        path = make_epub(
            self.root,
            chapter_overrides={"chapter-1": malicious},
        )

        with self.assertRaisesRegex(CorruptBookError, "XML không an toàn"):
            import_epub(path)

    def test_utf16_xml_entity_declarations_are_rejected_before_expansion(self):
        xml = '''<?xml version="1.0" encoding="utf-16"?>
                <!DOCTYPE html [<!ENTITY payload "expanded">]>
                <html xmlns="http://www.w3.org/1999/xhtml"><body>
                  <p>&payload;</p>
                </body></html>
                '''
        encodings = {
            "utf-16": xml.encode("utf-16"),
            "utf-16-be": b"\xfe\xff" + xml.encode("utf-16-be"),
        }
        for encoding, malicious in encodings.items():
            with self.subTest(encoding=encoding):
                path = make_epub(
                    self.root,
                    name=f"entity-{encoding}.epub",
                    spine=("chapter-1",),
                    chapter_overrides={"chapter-1": malicious},
                )

                with self.assertRaisesRegex(CorruptBookError, "XML không an toàn"):
                    import_epub(path)

    def test_unknown_xml_encoding_is_reported_as_a_corrupt_book(self):
        chapter = '''<?xml version="1.0" encoding="x-unknown"?>
        <html xmlns="http://www.w3.org/1999/xhtml"><body><p>Nội dung.</p></body></html>
        '''
        path = make_epub(
            self.root,
            spine=("chapter-1",),
            chapter_overrides={"chapter-1": chapter},
        )

        with self.assertRaisesRegex(CorruptBookError, "XML hợp lệ"):
            import_epub(path)

    def test_malformed_manifest_url_is_reported_as_a_corrupt_book(self):
        path = make_epub(self.root, unsafe_href="http://[")

        with self.assertRaisesRegex(CorruptBookError, "đường dẫn"):
            import_epub(path)


if __name__ == "__main__":
    unittest.main()


class CoverTests(unittest.TestCase):
    """The cover is found by the three conventions publishers use, and only
    real image bytes ever reach the shelf."""

    PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )

    def _cover(self, root, **extras):
        from vieneu_reader.importers.epub_presentation import load_epub_cover
        return load_epub_cover(make_epub(root, **extras))

    def test_epub3_cover_image_property_wins(self) -> None:
        with TemporaryDirectory() as directory:
            cover = self._cover(
                Path(directory),
                manifest_extra='<item id="art" href="images/front.png" media-type="image/png" properties="cover-image"/>',
                extra_members={"OEBPS/images/front.png": self.PNG},
            )
        self.assertEqual(cover, (self.PNG, "image/png"))

    def test_epub2_meta_cover_names_an_item_or_an_href(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            by_id = self._cover(
                root, name="a.epub",
                metadata_extra='<meta name="cover" content="art"/>',
                manifest_extra='<item id="art" href="images/x.png" media-type="image/png"/>',
                extra_members={"OEBPS/images/x.png": self.PNG},
            )
            by_href = self._cover(
                root, name="b.epub",
                metadata_extra='<meta name="cover" content="images/x.png"/>',
                manifest_extra='<item id="whatever" href="images/x.png" media-type="image/jpg"/>',
                extra_members={"OEBPS/images/x.png": self.PNG},
            )
        self.assertEqual(by_id, (self.PNG, "image/png"))
        # "image/jpg" is normalised, and the PNG bytes then fail the JPEG
        # check: a declared type that lies never ships.
        self.assertIsNone(by_href)

    def test_an_image_called_cover_is_the_fallback(self) -> None:
        with TemporaryDirectory() as directory:
            cover = self._cover(
                Path(directory),
                manifest_extra='<item id="img7" href="images/Cover.png" media-type="image/png"/>',
                extra_members={"OEBPS/images/Cover.png": self.PNG},
            )
        self.assertEqual(cover, (self.PNG, "image/png"))

    def test_no_cover_and_a_non_image_are_none_not_errors(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            none = self._cover(root, name="a.epub")
            not_an_image = self._cover(
                root, name="b.epub",
                manifest_extra='<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>',
                extra_members={"OEBPS/cover.xhtml": b"<html/>"},
            )
            lying_bytes = self._cover(
                root, name="c.epub",
                manifest_extra='<item id="cover" href="c.png" media-type="image/png" properties="cover-image"/>',
                extra_members={"OEBPS/c.png": b"not a png at all"},
            )
        self.assertIsNone(none)
        self.assertIsNone(not_an_image)
        self.assertIsNone(lying_bytes)

    def test_a_print_size_cover_is_shrunk_to_shelf_size(self) -> None:
        from io import BytesIO
        import PIL.Image
        from vieneu_reader.importers.covers import COVER_HEIGHT_PX
        from vieneu_reader.importers.epub_presentation import _jpeg_dimensions
        big = BytesIO()
        PIL.Image.new("RGB", (1300, 2000), (200, 30, 30)).save(big, format="PNG")
        with TemporaryDirectory() as directory:
            cover = self._cover(
                Path(directory),
                manifest_extra='<item id="art" href="big.png" media-type="image/png" properties="cover-image"/>',
                extra_members={"OEBPS/big.png": big.getvalue()},
            )
        payload, media_type = cover
        self.assertEqual(media_type, "image/jpeg")
        self.assertEqual(_jpeg_dimensions(payload)[1], COVER_HEIGHT_PX)
        self.assertLess(len(payload), len(big.getvalue()))

