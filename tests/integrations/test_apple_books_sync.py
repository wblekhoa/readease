import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from vieneu_reader.integrations.apple_books import Annotation
from vieneu_reader.integrations.apple_books_sync import (
    MatchReport,
    SegmentRef,
    folder_is_encrypted,
    match_annotations,
    pack_epub_folder,
    same_title,
)


def _unpacked_epub(root: Path, *, extra: dict[str, bytes] | None = None) -> Path:
    folder = root / "Sách.epub"
    (folder / "META-INF").mkdir(parents=True)
    (folder / "OEBPS").mkdir()
    (folder / "mimetype").write_bytes(b"application/epub+zip")
    (folder / "META-INF" / "container.xml").write_bytes(b"<container/>")
    (folder / "OEBPS" / "content.opf").write_bytes(b"<package/>")
    (folder / "OEBPS" / "ch1.xhtml").write_bytes(b"<html/>")
    for name, payload in (extra or {}).items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return folder


class PackTests(unittest.TestCase):
    def test_the_same_folder_packs_to_the_same_bytes_twice(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = _unpacked_epub(root, extra={
                "iTunesMetadata.plist": b"<plist/>", ".DS_Store": b"x",
                "__MACOSX/OEBPS/._ch1.xhtml": b"junk",
            })
            first = pack_epub_folder(folder, root / "a.epub").read_bytes()
            (folder / "iTunesMetadata.plist").write_bytes(b"<plist>changed by Books</plist>")
            second = pack_epub_folder(folder, root / "b.epub").read_bytes()
            self.assertEqual(first, second)
            with ZipFile(root / "a.epub") as archive:
                names = archive.namelist()
                self.assertEqual(names[0], "mimetype")
                self.assertEqual(archive.getinfo("mimetype").compress_type, 0)
                self.assertNotIn("iTunesMetadata.plist", names)
                self.assertNotIn(".DS_Store", names)
                self.assertFalse(any(name.startswith("__MACOSX") for name in names))

    def test_font_obfuscation_is_not_drm_but_encrypted_content_is(self) -> None:
        fonts = b"""<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#">
            <EncryptionMethod Algorithm="http://www.idpf.org/2008/embedding"/>
            <CipherData><CipherReference URI="OEBPS/fonts/Serif.ttf"/></CipherData>
          </EncryptedData></encryption>"""
        drm = fonts.replace(b"OEBPS/fonts/Serif.ttf", b"OEBPS/ch1.xhtml")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            plain = _unpacked_epub(root / "plain")
            self.assertFalse(folder_is_encrypted(plain))
            obfuscated = _unpacked_epub(root / "fonts", extra={"META-INF/encryption.xml": fonts})
            self.assertFalse(folder_is_encrypted(obfuscated))
            locked = _unpacked_epub(root / "drm", extra={"META-INF/encryption.xml": drm})
            self.assertTrue(folder_is_encrypted(locked))


class TitleTests(unittest.TestCase):
    def test_a_subtitle_rendered_differently_still_pairs(self) -> None:
        self.assertTrue(same_title(
            "Đừng bắt tôi phải suy nghĩ! Tái bản: Một cách tiếp cận bằng lẽ thường đối với tính dễ sử dụng trên Web",
            "Đừng bắt tôi phải suy nghĩ! — Tái bản: Một cách tiếp cận bằng lẽ thường đối với usability trên Web",
        ))

    def test_short_titles_must_match_whole(self) -> None:
        self.assertTrue(same_title("Thiên Nga Đen", "thiên nga đen"))
        self.assertFalse(same_title("Thiên Nga Đen", "Thiên Nga Trắng"))
        self.assertFalse(same_title("", "Thiên Nga Đen"))


class MatchTests(unittest.TestCase):
    SEGMENTS = (
        SegmentRef(0, "s1", "Năm nào họ cũng chú ý rất tốt đến tính dễ sử dụng."),
        SegmentRef(1, "s2", "“Đừng hiểu lầm ý tôi.” Trước hết, sản phẩm phải hoạt động."),
        SegmentRef(2, "s3", "Trước hết, sản phẩm phải hoạt động. Lặp lại ở chương sau."),
    )

    def test_curly_quotes_nbsp_and_spacing_do_not_break_a_match(self) -> None:
        report = match_annotations(self.SEGMENTS, (
            Annotation("a", 2, "epubcfi(/6/4!/4/2)", selected_text='"Đừng  hiểu lầm ý tôi." Trước', note="ghi chú"),
        ))
        self.assertEqual([m.segment_id for m in report.matched], ["s2"])
        self.assertEqual(report.matched[0].note, "ghi chú")
        self.assertEqual(report.unmatched, 0)

    def test_the_cfi_breaks_a_tie_between_chapters(self) -> None:
        near_third = Annotation("a", 2, "epubcfi(/6/8!/4/2)", selected_text="Trước hết, sản phẩm phải hoạt động.")
        near_second = Annotation("a", 2, "epubcfi(/6/4!/4/2)", selected_text="Trước hết, sản phẩm phải hoạt động.")
        report = match_annotations(self.SEGMENTS, (near_third, near_second))
        self.assertEqual([m.segment_id for m in report.matched], ["s3", "s2"])

    def test_bookmarks_are_skipped_and_missing_words_are_unmatched(self) -> None:
        report = match_annotations(self.SEGMENTS, (
            Annotation("a", 3, "epubcfi(/6/4!/4/2)"),
            Annotation("a", 2, "epubcfi(/6/4!/4/2)", selected_text="Câu này không có trong sách."),
        ))
        self.assertEqual(report, MatchReport((), unmatched=1, skipped=1))

    def test_ids_are_stable_across_runs(self) -> None:
        annotation = Annotation("a", 2, "epubcfi(/6/4!/4/2)", selected_text="Năm nào họ cũng chú ý")
        first = match_annotations(self.SEGMENTS, (annotation,)).matched[0].id
        second = match_annotations(self.SEGMENTS, (annotation,)).matched[0].id
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("applebooks:"))


if __name__ == "__main__":
    unittest.main()
