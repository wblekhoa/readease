"""Where the voice marks a new part or chapter (HIG 5.1, 24/09).

The rule is the contents column's own (`app/src/ui/contents.ts`), so the
chime falls exactly where the eye sees a chapter or part line. The first two
tests hold the Python port to that file: the same tree and the same titles
its node tests use, the same answers.
"""

import unittest

from vieneu_reader.domain.divisions import (
    PART_OPENING_WORDS,
    contents_marker,
    contents_roles,
    division_plan,
)
from vieneu_reader.domain.models import BookDocument, Chapter, Segment
from vieneu_reader.domain.presentation import ContentsEntry


def book(chapters, *, source_format="epub"):
    """(title, [(text, kind), ...]) per chapter; segment ids are "c{chapter}-s{index}"."""
    built = []
    for index, (title, blocks) in enumerate(chapters):
        chapter_id = f"c{index}"
        built.append(Chapter(
            id=chapter_id,
            title=title,
            ordinal=index,
            segments=tuple(
                Segment(id=f"c{index}-s{position}", chapter_id=chapter_id, ordinal=position, text=text, kind=kind)
                for position, (text, kind) in enumerate(blocks)
            ),
        ))
    return BookDocument(id="b", title="Sách thử", source_format=source_format, source_hash="h", chapters=tuple(built))


def line(level, title, segment_id):
    return ContentsEntry(title=title, level=level, segment_id=segment_id)


PARAGRAPH = "Buổi sáng hôm ấy, sương còn phủ kín mặt sông."
# Shaped like the structures real books use (invented words): a title page,
# a copyright page, a printed contents page, a part page, a chapter that a
# converter split across two files, a second chapter, a second part.
SPINE = [
    ("Bến Sông Xa", [("Bến Sông Xa", "heading"), ("Lê Minh Thư", "paragraph")]),
    ("Bản quyền", [("Bản quyền © 2024 Nhà xuất bản Gió Nam.", "paragraph")]),
    ("Mục lục", [("Mục lục", "heading"), ("Chương 1. Bến sông", "paragraph")]),
    ("PHẦN MỘT", [("PHẦN MỘT", "heading"), ("Những con đường", "paragraph")]),
    ("Chương 1", [("Chương 1", "heading"), ("Bến sông", "heading"), (PARAGRAPH, "paragraph")]),
    ("Chương 1 (tiếp)", [(PARAGRAPH, "paragraph")]),
    ("Chương 2", [("Chương 2", "heading"), ("Mùa nước nổi", "heading"), (PARAGRAPH, "paragraph")]),
    ("PHẦN HAI", [("PHẦN HAI", "heading"), ("Bờ bên kia", "paragraph")]),
    ("Chương 3", [("Chương 3", "heading"), ("Lên núi", "heading"), (PARAGRAPH, "paragraph")]),
]
CONTENTS = [
    line(1, "Phần Một: Những con đường", "c3-s0"),
    line(2, "Chương 1. Bến sông", "c4-s0"),
    line(2, "Chương 2. Mùa nước nổi", "c6-s0"),
    line(1, "Phần Hai: Bờ bên kia", "c7-s0"),
    line(2, "Chương 3. Lên núi", "c8-s0"),
]


class ContentsRuleParityTests(unittest.TestCase):
    def test_a_title_says_chapter_or_part_the_way_the_column_reads_it(self) -> None:
        # The same titles as `app/tests/contents.test.ts`.
        self.assertEqual(contents_marker("Chương Mười Hai: Gió"), ("chapter", 12))
        self.assertEqual(contents_marker("Chương hai mươi mốt Sóng"), ("chapter", 21))
        self.assertEqual(contents_marker("Chapter IV — The Tide"), ("chapter", 4))
        self.assertEqual(contents_marker("Part Two: Harbours"), ("part", 2))
        self.assertEqual(contents_marker("PHẦN MỘT"), ("part", 1))
        self.assertIsNone(contents_marker("Phần mở đầu"))
        self.assertIsNone(contents_marker("Chương cuối"))
        self.assertIsNone(contents_marker("Phần lớn sản phẩm"))

    def test_the_column_s_tree_gets_the_column_s_roles(self) -> None:
        # The 16-line tree of `app/tests/contents.test.ts`.
        tree = [
            (1, "Lời bạt"), (1, "Phần mở đầu"), (2, "NHỮNG CÂU HỎI ĐẦU TIÊN"),
            (1, "Phần Một: NHỮNG CON ĐƯỜNG"), (2, "Chương 1 BẾN SÔNG"), (3, "CON THUYỀN"),
            (4, "Mái chèo"), (4, "Cánh buồm"), (3, "BỜ CÁT"), (2, "Chương 2 BỜ BÊN KIA"),
            (1, "Phần Hai BẦU TRỜI"), (2, "Chương 3 MÂY"), (3, "Phần Bốn CUỐI MÙA"), (3, "MƯA"),
            (1, "Phần kết"), (1, "Lời cảm ơn"),
        ]
        roles = contents_roles([line(level, title, str(index)) for index, (level, title) in enumerate(tree)])
        self.assertEqual(roles, [
            "chapter", "part", "chapter",
            "part", "chapter", "section",
            "section", "section", "section", "chapter",
            "part", "chapter", "section", "section",
            "chapter", "chapter",
        ])

    def test_a_tree_without_chapter_labels_stops_at_its_top(self) -> None:
        roles = contents_roles([
            line(1, "Lời nói đầu", "a"), line(1, "Những ngày đầu", "b"),
            line(2, "Buổi sáng", "c"), line(1, "Mùa mưa", "d"),
        ])
        # Without "Chương N" lines the top level IS the chapter level: a line
        # with lines under it there is a chapter with sections, not a part.
        self.assertEqual(roles, ["chapter", "chapter", "section", "chapter"])


class DivisionPlanTests(unittest.TestCase):
    def test_with_contents_the_chimes_follow_its_chapter_and_part_lines(self) -> None:
        plan = division_plan(book(SPINE), CONTENTS)
        # Not at the title, copyright or contents pages; not at the file the
        # converter split off chapter 1; one sound for a part and the chapter
        # that follows its title straight away.
        self.assertEqual(plan, {
            "c3-s0": "part",
            "c4-s0": "part-chapter",
            "c6-s0": "chapter",
            "c7-s0": "part",
            "c8-s0": "part-chapter",
        })

    def test_chapters_inside_one_file_are_found_by_the_contents(self) -> None:
        one_file = book([("Bến Sông Xa", [
            ("Chương 1. Bến sông", "heading"), (PARAGRAPH, "paragraph"),
            ("Chương 2. Mùa nước nổi", "heading"), (PARAGRAPH, "paragraph"),
            ("Chương 3. Lên núi", "heading"), (PARAGRAPH, "paragraph"),
        ])])
        plan = division_plan(one_file, [
            line(1, "Chương 1. Bến sông", "c0-s0"),
            line(1, "Chương 2. Mùa nước nổi", "c0-s2"),
            line(1, "Chương 3. Lên núi", "c0-s4"),
        ])
        self.assertEqual(plan, {"c0-s0": "chapter", "c0-s2": "chapter", "c0-s4": "chapter"})

    def test_sections_below_the_chapter_level_are_not_divisions(self) -> None:
        plan = division_plan(book(SPINE), CONTENTS + [line(3, "Buổi sáng", "c4-s2")])
        self.assertNotIn("c4-s2", plan)

    def test_two_lines_on_one_passage_count_as_the_higher_one(self) -> None:
        plan = division_plan(book(SPINE), [
            line(1, "Phần Một: Những con đường", "c4-s0"),
            line(2, "Chương 1. Bến sông", "c4-s0"),
            line(2, "Chương 2. Mùa nước nổi", "c6-s0"),
        ])
        self.assertEqual(plan, {"c4-s0": "part", "c6-s0": "chapter"})

    def test_a_part_that_opens_with_real_text_lets_its_first_chapter_chime(self) -> None:
        spine = [list(chapter) for chapter in SPINE]
        long_intro = " ".join(["lời"] * (PART_OPENING_WORDS + 1))
        spine[3] = ("PHẦN MỘT", [("PHẦN MỘT", "heading"), (long_intro, "paragraph")])
        plan = division_plan(book(spine), CONTENTS)
        self.assertEqual(plan["c4-s0"], "chapter")

    def test_without_contents_a_file_is_a_chapter_only_when_it_opens_with_a_heading(self) -> None:
        plan = division_plan(book(SPINE), [])
        self.assertEqual(plan, {
            "c0-s0": "chapter",
            "c2-s0": "chapter",
            "c3-s0": "part",
            "c4-s0": "part-chapter",
            "c6-s0": "chapter",
            "c7-s0": "part",
            "c8-s0": "part-chapter",
        })

    def test_the_pages_of_a_pdf_without_bookmarks_are_not_chapters(self) -> None:
        pages = book([
            ("Trang 1", [("Ông lão chèo thuyền và không nói", "paragraph")]),
            ("Trang 2", [("một lời nào suốt quãng đường.", "paragraph")]),
            ("Trang 4", [(PARAGRAPH, "paragraph")]),
        ], source_format="pdf")
        # No chapter anywhere; the sentence over the first page break reads
        # on, the one that ended at the second does not need to.
        self.assertEqual(division_plan(pages, []), {"c1-s0": "continue"})

    def test_the_bookmarks_of_a_pdf_are_chapters(self) -> None:
        bookmarked = book([
            ("Mở đầu", [(PARAGRAPH, "paragraph")]),
            ("Tiếp theo", [(PARAGRAPH, "paragraph")]),
        ], source_format="pdf")
        self.assertEqual(division_plan(bookmarked, []), {"c0-s0": "chapter", "c1-s0": "chapter"})

    def test_a_thematic_break_marks_the_passage_after_it(self) -> None:
        plan = division_plan(book(SPINE), CONTENTS, breaks=["c4-s2", "c6-s0"])
        self.assertEqual(plan["c4-s2"], "scene")
        # A chapter that opens after a break is still a chapter.
        self.assertEqual(plan["c6-s0"], "chapter")


if __name__ == "__main__":
    unittest.main()
