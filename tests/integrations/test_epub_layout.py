from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from vieneu_reader.integrations.epub_layout import (
    Layout,
    UnreadableBook,
    carries_over,
    read_layout,
    spine_index,
)

_CHAPTER = (
    '<html xmlns="http://www.w3.org/1999/xhtml"><body><p>{body}</p></body></html>'
)


def _package(chapters: int, *, base: str = "OEBPS") -> str:
    manifest = "".join(
        f'<item id="c{i}" href="text/part{i}.html" '
        'media-type="application/xhtml+xml"/>'
        for i in range(chapters)
    )
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(chapters))
    return (
        '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" '
        'version="3.0" unique-identifier="uid"><metadata/>'
        f"<manifest>{manifest}</manifest><spine>{spine}</spine></package>"
    )


def _container(package: str) -> str:
    return (
        '<?xml version="1.0"?><container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
        f'<rootfile full-path="{package}" '
        'media-type="application/oebps-package+xml"/></rootfiles></container>'
    )


def _zip_book(
    path: Path,
    *,
    chapters: int = 3,
    differs_at: int | None = None,
    base: str = "OEBPS",
    with_container: bool = True,
) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        package = f"{base}/content.opf" if base else "content.opf"
        if with_container:
            archive.writestr("META-INF/container.xml", _container(package))
        archive.writestr(package, _package(chapters, base=base))
        for index in range(chapters):
            body = "khac" if index == differs_at else f"chuong {index}"
            name = f"{base}/text/part{index}.html" if base else f"text/part{index}.html"
            archive.writestr(name, _CHAPTER.format(body=body))
    return path


def _directory_book(root: Path, *, chapters: int = 3) -> Path:
    book = root / "unpacked.epub"
    (book / "META-INF").mkdir(parents=True)
    (book / "OEBPS" / "text").mkdir(parents=True)
    (book / "META-INF" / "container.xml").write_text(
        _container("OEBPS/content.opf"), encoding="utf-8"
    )
    (book / "OEBPS" / "content.opf").write_text(_package(chapters), encoding="utf-8")
    for index in range(chapters):
        (book / "OEBPS" / "text" / f"part{index}.html").write_text(
            _CHAPTER.format(body=f"chuong {index}"), encoding="utf-8"
        )
    return book


class SpineIndexTests(unittest.TestCase):
    """A CFI's spine step, or nothing.

    Nothing is the safe answer: the caller treats it as "cannot vouch for this".
    """

    def test_the_first_spine_item_is_step_two(self) -> None:
        self.assertEqual(spine_index("epubcfi(/6/2)"), 0)
        self.assertEqual(spine_index("epubcfi(/6/38[id206]!/4/188)"), 18)

    def test_an_odd_step_names_no_spine_item(self) -> None:
        """Odd steps address text inside an element, not a child element."""

        self.assertIsNone(spine_index("epubcfi(/6/3)"))

    def test_a_step_below_two_names_no_spine_item(self) -> None:
        self.assertIsNone(spine_index("epubcfi(/6/0)"))

    def test_a_path_that_does_not_start_at_the_spine_is_refused(self) -> None:
        self.assertIsNone(spine_index("epubcfi(/4/2)"))

    def test_nonsense_is_refused_rather_than_raised(self) -> None:
        for value in ("", "not a cfi", None):
            with self.subTest(value=value):
                self.assertIsNone(spine_index(value))


class ReadLayoutTests(unittest.TestCase):
    def test_a_zipped_book_hashes_one_digest_per_spine_item(self) -> None:
        with TemporaryDirectory() as directory:
            book = _zip_book(Path(directory) / "a.epub", chapters=4)
            self.assertEqual(len(read_layout(book).digests), 4)

    def test_an_unpacked_book_reads_the_same_as_a_zipped_one(self) -> None:
        """Apple Books keeps some titles as a directory, not an archive."""

        with TemporaryDirectory() as directory:
            root = Path(directory)
            packed = read_layout(_zip_book(root / "a.epub", chapters=3))
            unpacked = read_layout(_directory_book(root, chapters=3))
            self.assertEqual(packed.digests, unpacked.digests)

    def test_the_package_is_found_without_a_container_file(self) -> None:
        with TemporaryDirectory() as directory:
            book = _zip_book(
                Path(directory) / "a.epub", chapters=2, with_container=False
            )
            self.assertEqual(len(read_layout(book).digests), 2)

    def test_chapter_paths_are_resolved_relative_to_the_package(self) -> None:
        """The package sits in a subdirectory, so hrefs are relative to it."""

        with TemporaryDirectory() as directory:
            nested = read_layout(_zip_book(Path(directory) / "a.epub", base="OEBPS"))
            flat = read_layout(
                _zip_book(Path(directory) / "b.epub", base="")
            )
            self.assertEqual(nested.digests, flat.digests)
            self.assertTrue(all(nested.digests), "a chapter could not be read")

    def test_a_file_that_is_not_a_book_is_named_as_such(self) -> None:
        with TemporaryDirectory() as directory:
            junk = Path(directory) / "junk.epub"
            junk.write_bytes(b"nope")
            with self.assertRaises(UnreadableBook):
                read_layout(junk)

    def test_a_missing_book_is_named_as_such(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(UnreadableBook):
                read_layout(Path(directory) / "absent.epub")

    def test_a_directory_with_no_package_is_named_as_such(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(UnreadableBook):
                read_layout(Path(directory))

    def test_a_chapter_that_cannot_be_read_yields_no_digest(self) -> None:
        """One missing chapter must not lose the whole layout."""

        with TemporaryDirectory() as directory:
            path = Path(directory) / "a.epub"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("META-INF/container.xml", _container("content.opf"))
                archive.writestr("content.opf", _package(2, base=""))
                archive.writestr("text/part0.html", _CHAPTER.format(body="một"))
                # part1.html is simply absent.
            layout = read_layout(path)
            self.assertTrue(layout.digests[0])
            self.assertEqual(layout.digests[1], "")


class CarriesOverTests(unittest.TestCase):
    """The question the whole module exists to answer."""

    def _pair(self, root: Path, differs_at: int | None):
        return (
            read_layout(_zip_book(root / "src.epub", chapters=4)),
            read_layout(_zip_book(root / "dst.epub", chapters=4, differs_at=differs_at)),
        )

    def test_identical_books_carry_every_position(self) -> None:
        with TemporaryDirectory() as directory:
            source, target = self._pair(Path(directory), None)
            for step in (2, 4, 6, 8):
                with self.subTest(step=step):
                    self.assertTrue(carries_over(source, target, f"epubcfi(/6/{step})"))

    def test_a_differing_chapter_refuses_only_its_own_positions(self) -> None:
        with TemporaryDirectory() as directory:
            source, target = self._pair(Path(directory), 2)
            self.assertFalse(carries_over(source, target, "epubcfi(/6/6)"))
            self.assertTrue(carries_over(source, target, "epubcfi(/6/4)"))

    def test_a_position_past_the_end_of_the_spine_is_refused(self) -> None:
        with TemporaryDirectory() as directory:
            source, target = self._pair(Path(directory), None)
            self.assertFalse(carries_over(source, target, "epubcfi(/6/400)"))

    def test_a_position_that_names_no_spine_item_is_refused(self) -> None:
        with TemporaryDirectory() as directory:
            source, target = self._pair(Path(directory), None)
            self.assertFalse(carries_over(source, target, "khong phai cfi"))

    def test_two_chapters_neither_side_could_read_do_not_match(self) -> None:
        """Empty equals empty, and that must not read as agreement."""

        empty = Layout(("",))
        self.assertFalse(carries_over(empty, empty, "epubcfi(/6/2)"))

    def test_an_empty_layout_carries_nothing(self) -> None:
        self.assertFalse(carries_over(Layout(()), Layout(()), "epubcfi(/6/2)"))


if __name__ == "__main__":
    unittest.main()
