import time
import unittest

from vieneu_reader.domain.markdown import markdown_speech_parts
from vieneu_reader.domain.segmenter import split_transient_parts


def spoken(text: str, max_chars: int = 240) -> tuple[str, ...]:
    """What each transient part says after the Markdown pass."""
    parts = split_transient_parts(text, max_chars)
    return markdown_speech_parts(
        tuple(part.text for part in parts),
        tuple(part.joint for part in parts),
    )


def said(text: str) -> str:
    return " | ".join(spoken(text))


class InlineMarkdownTests(unittest.TestCase):
    def test_emphasis_of_every_strength_reads_its_words(self):
        for text, expected in (
            ("**đậm** và *nghiêng* và ***cả hai***", "đậm và nghiêng và cả hai"),
            ("__đậm__ và _nghiêng_ và ___cả hai___", "đậm và nghiêng và cả hai"),
            ("**đậm *lồng* trong**", "đậm lồng trong"),
            ("_**lồng ngoài**_ và ~~**gạch**~~", "lồng ngoài và gạch"),
            ("(*nghiêng*), “*trích*” và *cuối*.", "(nghiêng), “trích” và cuối."),
            ("~~bỏ đi~~ rồi", "bỏ đi rồi"),
            ("Năm **2026** và *3* lần", "Năm 2026 và 3 lần"),
        ):
            with self.subTest(text=text):
                self.assertEqual(said(text), expected)

    def test_literal_stars_and_underscores_stay(self):
        for text in (
            "5*3 = 15 và 2*4 = 8",
            "a * b * c",
            "giá 100k* và 200k*",
            "snake_case_name và other_name",
            "_private và _other",
            "Tính 2**10 rồi 3**4.",
            "x**2 + y**2",
            "**chưa đóng",
            "** cách **",
        ):
            with self.subTest(text=text):
                self.assertEqual(said(text), text)

    def test_code_keeps_its_content_without_delimiters(self):
        self.assertEqual(said("Gõ `**npm** run` rồi `_x_`"), "Gõ **npm** run rồi _x_")
        self.assertEqual(said("Dùng ``a ` b`` nhé"), "Dùng a ` b nhé")

    def test_escapes_keep_the_literal_character(self):
        self.assertEqual(said(r"\*không nghiêng\* và \_x\_"), "*không nghiêng* và _x_")

    def test_links_images_and_notes_read_their_words(self):
        for text, expected in (
            ("[Tên](https://a.vn/c) và [khác](b.html \"tiêu đề\")", "Tên và khác"),
            ("Xem [mục này][1] và [kia][]", "Xem mục này và kia"),
            ("Ảnh ![một con mèo](meo.png) đây", "Ảnh một con mèo đây"),
            ("Câu có chú thích[^1] và[^ghi-chu].", "Câu có chú thích và."),
            ("Tại <https://x.vn/a> nhé", "Tại https://x.vn/a nhé"),
            ("[**Đậm trong link**](https://a.vn)", "Đậm trong link"),
        ):
            with self.subTest(text=text):
                self.assertEqual(said(text), expected)

    def test_bare_addresses_keep_their_underscores(self):
        self.assertEqual(said("https://a.vn/_x_/y và www.b.vn/_z_"), "https://a.vn/_x_/y và www.b.vn/_z_")

    def test_inline_html_tags_go_and_comparisons_stay(self):
        for text, expected in (
            ("<b>đậm</b> và <em>nhấn</em>", "đậm và nhấn"),
            ("dòng một<br>dòng hai", "dòng một dòng hai"),
            ("a < b > c", "a < b > c"),
            ("<span class=\"x\">chữ</span>", "chữ"),
        ):
            with self.subTest(text=text):
                self.assertEqual(said(text), expected)

    def test_every_kind_at_once_in_one_sentence(self):
        text = ("![ảnh](a.png) [link](b.vn) chú[^1] [ref][1] ~~gạch~~ ***a*** _b_ "
                "<b>c</b> **d *e* f** __g _h_ i__")
        self.assertEqual(said(text), "ảnh link chú ref gạch a b c d e f g h i")

    def test_pairs_split_across_parts_still_resolve(self):
        text = "*" + "nghiêng dài " * 30 + "kết.*"
        parts = spoken(text, max_chars=60)
        self.assertGreater(len(parts), 1)
        self.assertNotIn("*", " ".join(parts))


class LineMarkdownTests(unittest.TestCase):
    def test_headings_lose_their_marks_and_end_as_a_sentence(self):
        self.assertEqual(spoken("# Giới thiệu\nNội dung."), ("Giới thiệu.", "Nội dung."))
        self.assertEqual(spoken("## Tiêu đề ##\nA."), ("Tiêu đề.", "A."))
        self.assertEqual(spoken("### Câu hỏi?"), ("Câu hỏi?",))
        self.assertEqual(spoken("#hashtag và # giữa câu"), ("#hashtag và # giữa câu",))

    def test_a_heading_or_fence_never_absorbs_the_line_below(self):
        # A lowercase line normally folds into an unfinished line above (a
        # hard wrap); a heading or a fence opener is never unfinished prose.
        self.assertEqual(spoken("# Tiêu đề\nnội dung thường."), ("Tiêu đề.", "nội dung thường."))
        self.assertEqual(spoken("```\nprint(x)\n```"), ("", "print(x)", ""))

    def test_a_hard_line_break_backslash_is_not_spoken(self):
        self.assertEqual(spoken("Dòng một\\\nhai"), ("Dòng một hai",))
        self.assertEqual(spoken("Dòng một\\\nDòng hai"), ("Dòng một", "Dòng hai"))

    def test_setext_underlines_and_rules_are_silent(self):
        self.assertEqual(spoken("Tiêu đề\n====\nThân bài."), ("Tiêu đề.", "", "Thân bài."))
        self.assertEqual(spoken("A.\n\n---\n\nB."), ("A.", "", "B."))
        self.assertEqual(spoken("Mục hai\n---\nThân."), ("Mục hai.", "", "Thân."))
        self.assertEqual(spoken("A.\n\n___\n\nB."), ("A.", "", "B."))

    def test_a_rule_under_a_list_quote_or_table_is_a_rule(self):
        # Only a plain line can be underlined into a heading; "- b" above
        # "---" is a list item followed by a rule.
        self.assertEqual(spoken("- a\n- b\n---\nC"), ("a", "b", "", "C"))
        self.assertEqual(spoken("> trích\n---\nC"), ("trích", "", "C"))
        self.assertEqual(spoken("| a | b |\n---\nC"), ("a, b", "", "C"))

    def test_a_rule_never_absorbs_the_line_below(self):
        self.assertEqual(spoken("Ý một.\n\n---\nthân bài"), ("Ý một.", "", "thân bài"))
        self.assertEqual(spoken("Đoạn\n---\nthân"), ("Đoạn.", "", "thân"))

    def test_quotes_lists_and_tasks_lose_their_markers(self):
        self.assertEqual(spoken("> Trích dẫn\n> > lồng\n>không cách"), ("Trích dẫn", "lồng", "không cách"))
        self.assertEqual(spoken("- Một\n+ Hai\n* *Ba*"), ("Một", "Hai", "Ba"))
        self.assertEqual(spoken("- [x] Xong\n- [ ] Chưa"), ("Xong", "Chưa"))
        self.assertEqual(spoken("Có [x] giữa câu"), ("Có [x] giữa câu",))
        self.assertEqual(spoken("1. Mở đầu\n2) Tiếp"), ("1. Mở đầu", "2) Tiếp"))

    def test_pasted_dialogue_dash_is_a_list_marker_too(self):
        # Decision (06/10): "- " opening a pasted line is dropped whether it
        # is a list or dialogue; the line break already carries the pause.
        self.assertEqual(spoken("- Chào anh.\n- Chào em."), ("Chào anh.", "Chào em."))

    def test_tables_read_as_comma_separated_rows(self):
        self.assertEqual(
            spoken("| Tên | Tuổi |\n|---|:--:|\n| An | 7 |"),
            ("Tên, Tuổi", "", "An, 7"),
        )

    def test_reference_definitions_are_silent_and_footnotes_read(self):
        self.assertEqual(spoken("Xem [a][1].\n\n[1]: https://a.vn \"A\""), ("Xem a.", ""))
        self.assertEqual(spoken("Ý[^1].\n\n[^1]: Ghi chú thêm."), ("Ý.", "Ghi chú thêm."))

    def test_fenced_code_reads_its_content_without_fences(self):
        out = spoken("Ví dụ:\n\n```python\nIn ra **x**\n```\n\nHết.")
        self.assertNotIn("`", " ".join(out))
        self.assertNotIn("python", " ".join(out))
        self.assertIn("In ra **x**", " ".join(out))
        self.assertEqual(out[-1], "Hết.")


class InvariantTests(unittest.TestCase):
    def test_hostile_input_stays_linear(self):
        # 90,000 "[" took 27 s while a link's words could hold a "[".
        for text in ("[" * 90000, "[^" * 45000, "![" * 45000, "*a" * 45000, "<b " * 30000):
            with self.subTest(text=text[:4]):
                started = time.monotonic()
                spoken(text)
                self.assertLess(time.monotonic() - started, 5.0)

    def test_one_spoken_text_per_part(self):
        for text in ("# A\n- b\n| c | d |", "**x** " * 80, "plain", "```\ncode\n```"):
            with self.subTest(text=text[:20]):
                parts = split_transient_parts(text, 50)
                self.assertEqual(len(spoken(text, 50)), len(parts))


if __name__ == "__main__":
    unittest.main()
