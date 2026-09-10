"""A library written by an older build must still open on this one.

`SCHEMA_VERSION` and `_migrate()` guard the shape of the TABLES. Nothing
guarded the shape of the JSON inside `document_json`, and that is where a
whole book lives. Measured 10/09 on a temporary data root: add one required
field to `_document_payload` and to `_document_from_payload` together - the
ordinary way a format grows - and all 748 Python tests stay green while a
library written by the previous build answers
`RepositoryCorruptionError: Dữ liệu sách trong thư viện cục bộ bị hỏng.`
for EVERY book on the shelf. `SCHEMA_VERSION` never moves, so `_migrate()`
never runs.

Why the existing tests could not see it: every storage test writes and
reads with the same build, so a round trip agrees with itself no matter
what the format is. The migration tests build the database with today's
code and then STAMP a version number onto it - they exercise the ladder,
not the bytes. Nothing in the repository held bytes from an older build.

So this file holds them. Each golden below was read back out of a real
`books` row with `sqlite3`, not produced by calling the serialiser - a
fixture derived from the code it guards agrees with itself too.

**The list is append-only.** When the format changes on purpose, the last
test here goes red. The fix is to ADD a golden for the new shape, never to
edit an old one: an old golden IS the library of somebody who already
installed the app, and rewriting it is how this guard would quietly become
another same-build round trip. If an old golden can no longer be read, that
is not a stale fixture - it is every existing reader losing their shelf,
and it needs a migration, or a reader that still accepts the old shape.

Sibling: `test_corrupt_book_row_is_load_bearing.py` says what happens once
a row IS unreadable, and why skipping it silently strands the book. This
file is about the most likely way a row becomes unreadable in the first
place - not a damaged disk, but a shipped update.
"""

import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.domain.models import BookDocument, Chapter, Segment, stable_id
from vieneu_reader.storage.repository import LibraryRepository, _document_payload


GOLDEN_2026_09_10 = {
    "id": (
        '07003d1f68fd32704bcb4778cb2a068632562f46131f6e272a6547ab7e6c1642'
    ),
    "title": (
        'Sách mẫu để đời'
    ),
    "source_format": (
        'epub'
    ),
    "source_hash": (
        'acea2a539a35eb4276bc668c1ca9e2930848ff8885706b2ef96682b02583333b'
    ),
    "managed_path": (
        '/thu-vien-mau/sach-mau.epub'
    ),
    "document_json": (
        '{"chapters":[{"id":"5cfe324d97b6fcb0f92f4d1a09b5ec523740b50043b000b0fde9f7'
        'c047777851","ordinal":0,"segments":[{"chapter_id":"5cfe324d97b6fcb0f92f4d1'
        'a09b5ec523740b50043b000b0fde9f7c047777851","id":"4127fd261fd844b6ab4c6a681'
        '248d77f9350469780621b8a8e99501305e246d6","joint":"block","kind":"heading",'
        '"ordinal":0,"text":"Chương một"},{"chapter_id":"5cfe324d97b6fcb0f92f4d1a09'
        'b5ec523740b50043b000b0fde9f7c047777851","id":"28380eae3e297ce17eebaffa90f9'
        'bd877a005a0f3b45bc15603e2e178fc7fa70","joint":"block","kind":"paragraph","'
        'ordinal":1,"text":"Đoạn văn thường."},{"chapter_id":"5cfe324d97b6fcb0f92f4'
        'd1a09b5ec523740b50043b000b0fde9f7c047777851","id":"a9b9c700cf2d7fedb058c96'
        '98d7745af456b8c48408610038f6d8bc01fb524af","joint":"line","kind":"list_ite'
        'm","ordinal":2,"text":"Một mục danh sách."},{"chapter_id":"5cfe324d97b6fcb'
        '0f92f4d1a09b5ec523740b50043b000b0fde9f7c047777851","id":"06201639f0ffc22bd'
        '3098eca19d6d8fb1646a62a1ce6fc09003968e1c89c7582","joint":"split","kind":"q'
        'uote","ordinal":3,"text":"Một câu trích."}],"title":"Chương một"},{"id":"4'
        'de8bb59133645b59473dd239f7ff57daf06e94ed2c268dffa7c00e171e55fd6","ordinal"'
        ':1,"segments":[{"chapter_id":"4de8bb59133645b59473dd239f7ff57daf06e94ed2c2'
        '68dffa7c00e171e55fd6","id":"34bbc15762644003fad55e1448a3623a80f186b9c59555'
        '1908ccf41b55a203d3","joint":"block","kind":"caption","ordinal":0,"text":"C'
        'hú thích ảnh."},{"chapter_id":"4de8bb59133645b59473dd239f7ff57daf06e94ed2c'
        '268dffa7c00e171e55fd6","id":"782fc91e3e39b0472e833f9a9d53b46fe6a988461e578'
        '2f6605a31445c95eaf9","joint":"line","kind":"preformatted","ordinal":1,"tex'
        't":"  văn bản giữ nguyên"}],"title":"Chương hai"}],"id":"07003d1f68fd32704'
        'bcb4778cb2a068632562f46131f6e272a6547ab7e6c1642","source_format":"epub","s'
        'ource_hash":"acea2a539a35eb4276bc668c1ca9e2930848ff8885706b2ef96682b025833'
        '33b","title":"Sách mẫu để đời"}'
    ),
}

#: Append only. Read the module docstring before touching an existing entry.
GOLDENS: tuple[tuple[str, dict[str, str]], ...] = (
    ("2026-09-10", GOLDEN_2026_09_10),
)

#: What the 2026-09-10 golden says, written out by hand so a reader that
#: silently drops a chapter, a segment or a `kind` cannot pass by agreeing
#: with whatever it happened to parse.
EXPECTED_CHAPTERS = (
    (
        "Chương một",
        (
            ("Chương một", "heading", "block"),
            ("Đoạn văn thường.", "paragraph", "block"),
            ("Một mục danh sách.", "list_item", "line"),
            ("Một câu trích.", "quote", "split"),
        ),
    ),
    (
        "Chương hai",
        (
            ("Chú thích ảnh.", "caption", "block"),
            ("  văn bản giữ nguyên", "preformatted", "line"),
        ),
    ),
)


def _rebuild_the_2026_09_10_book() -> BookDocument:
    """The same document the 2026-09-10 golden was written from.

    Only the LAST test uses this - the one that asks whether today's writer
    still produces the recorded bytes. The other tests must never build a
    document, or they would be checking the code against itself.
    """

    source_hash = stable_id("golden", "book")
    book_id = stable_id(source_hash, "epub")
    chapters = []
    for chapter_index, (title, segments) in enumerate(EXPECTED_CHAPTERS):
        chapter_id = stable_id(book_id, "chapter", str(chapter_index))
        chapters.append(
            Chapter(
                chapter_id,
                title,
                chapter_index,
                tuple(
                    Segment(
                        stable_id(chapter_id, "segment", str(index)),
                        chapter_id,
                        index,
                        text,
                        kind,
                        joint,
                    )
                    for index, (text, kind, joint) in enumerate(segments)
                ),
            )
        )
    return BookDocument(
        id=book_id,
        title="Sách mẫu để đời",
        source_format="epub",
        source_hash=source_hash,
        chapters=tuple(chapters),
    )


class StoredBooksOutliveTheBuildThatWroteThemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "library.db"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _shelf_holding(self, golden: dict[str, str]) -> LibraryRepository:
        """A library whose one row is those exact bytes, put there as an
        older build left them - not through today's `add_book`."""

        LibraryRepository(self.database)  # creates the schema, then closes over it
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                INSERT INTO books(
                    id, title, source_format, source_hash, managed_path, document_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                tuple(
                    golden[name]
                    for name in (
                        "id",
                        "title",
                        "source_format",
                        "source_hash",
                        "managed_path",
                        "document_json",
                    )
                ),
            )
        connection.close()
        return LibraryRepository(self.database)

    def test_every_golden_shelf_still_opens(self) -> None:
        for stamped, golden in GOLDENS:
            with self.subTest(golden=stamped):
                books = self._shelf_holding(golden).list_books()

                self.assertEqual(len(books), 1, "cả kệ sách biến mất")
                self.assertEqual(books[0].book.id, golden["id"])
                self.assertEqual(books[0].book.title, golden["title"])

    def test_every_golden_book_comes_back_whole(self) -> None:
        """Opening is not enough: a reader that drops a chapter, a segment or
        the kind of one still 'works' while the book it hands over is not the
        book that was stored."""

        stamped, golden = GOLDENS[0]
        with self.subTest(golden=stamped):
            book = self._shelf_holding(golden).list_books()[0].book

            self.assertEqual(len(book.chapters), len(EXPECTED_CHAPTERS))
            for chapter, (title, segments) in zip(book.chapters, EXPECTED_CHAPTERS):
                self.assertEqual(chapter.title, title)
                self.assertEqual(
                    tuple(
                        (segment.text, segment.kind, segment.joint)
                        for segment in chapter.segments
                    ),
                    segments,
                )

    def test_the_writer_still_produces_the_newest_golden(self) -> None:
        """The tripwire that keeps the goldens above from going stale.

        Red here means the stored format changed. THÊM một golden mới vào
        cuối `GOLDENS` - ĐỪNG sửa golden cũ: nó là thư viện của những người
        đã cài bản trước. Và trước khi thêm, phải trả lời được câu hỏi mà
        test trên hỏi: bản mới còn ĐỌC được golden cũ không? Nếu không, thì
        cần một bước migrate, chứ không phải một fixture mới.
        """

        stamped, newest = GOLDENS[-1]

        self.assertEqual(
            json.loads(_document_payload(_rebuild_the_2026_09_10_book())),
            json.loads(newest["document_json"]),
            f"định dạng lưu trữ đã đổi kể từ golden {stamped}",
        )


if __name__ == "__main__":
    unittest.main()
