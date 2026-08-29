import unittest

from vieneu_reader.domain.models import Segment
from vieneu_reader.domain.prosody import (
    BLOCK_PAUSE_MS,
    CHAPTER_PAUSE_MS,
    LINE_PAUSE_MS,
    SENTENCE_SPLIT_PAUSE_MS,
    ends_sentence,
    final_punctuation,
    pause_after_ms,
    selection_pause_ms,
    speakable_text,
)


def _segment(
    text: str,
    *,
    kind: str = "paragraph",
    joint: str = "block",
    chapter_id: str = "chapter-1",
    ordinal: int = 0,
) -> Segment:
    return Segment(
        id=f"segment-{chapter_id}-{ordinal}",
        chapter_id=chapter_id,
        ordinal=ordinal,
        text=text,
        kind=kind,
        joint=joint,
    )


class FinalPunctuationTests(unittest.TestCase):
    def test_reads_the_mark_through_closing_quotes_and_brackets(self):
        for text, expected in (
            ("Anh ấy hỏi.", "."),
            ("Anh ấy hỏi?”", "?"),
            ('Cô nói: "Được."', "."),
            ("Xong rồi…", "…"),
            ("(ghi chú),", ","),
            ("Tựa đề «Đất rừng»", ""),
            ("Không dấu", ""),
            ("", ""),
        ):
            with self.subTest(text=text):
                self.assertEqual(final_punctuation(text), expected)

    def test_sentence_detection_accepts_only_terminal_marks(self):
        self.assertTrue(ends_sentence("Hết câu.”"))
        self.assertFalse(ends_sentence("chưa hết,"))
        self.assertFalse(ends_sentence("giữa dòng"))


class PauseAfterTests(unittest.TestCase):
    def test_no_pause_after_the_last_segment(self):
        self.assertEqual(pause_after_ms(_segment("Hết."), None), 0)

    def test_chapter_change_wins_over_everything(self):
        current = _segment("Hết chương.", kind="paragraph")
        following = _segment(
            "Chương hai", kind="heading", chapter_id="chapter-2", ordinal=1
        )
        self.assertEqual(pause_after_ms(current, following), CHAPTER_PAUSE_MS)

    def test_split_boundary_depends_on_how_the_text_was_cut(self):
        for text, expected in (
            ("Câu đã trọn vẹn.", SENTENCE_SPLIT_PAUSE_MS),
            ("Anh ấy hỏi?”", SENTENCE_SPLIT_PAUSE_MS),
            ("mới nửa chừng,", 0),
            ("đứt giữa từ", 0),
        ):
            with self.subTest(text=text):
                current = _segment(text)
                following = _segment("phần sau", joint="split", ordinal=1)
                self.assertEqual(pause_after_ms(current, following), expected)

    def test_line_boundary_gets_a_short_breath(self):
        current = _segment("Dòng thơ thứ nhất")
        following = _segment("Dòng thơ thứ hai", joint="line", ordinal=1)
        self.assertEqual(pause_after_ms(current, following), LINE_PAUSE_MS)

    def test_block_boundaries_follow_the_kind_table(self):
        for current_kind, next_kind, expected in (
            ("paragraph", "paragraph", 450),
            ("paragraph", "heading", 800),
            ("heading", "paragraph", 700),
            ("heading", "heading", 800),
            ("list_item", "list_item", 300),
            ("list_item", "paragraph", 450),
            ("paragraph", "list_item", 450),
            ("quote", "paragraph", 550),
            ("paragraph", "quote", 550),
            ("caption", "paragraph", 450),
            ("paragraph", "caption", 450),
            ("preformatted", "paragraph", 450),
        ):
            with self.subTest(current=current_kind, following=next_kind):
                current = _segment("Một.", kind=current_kind)
                following = _segment("Hai.", kind=next_kind, ordinal=1)
                self.assertEqual(pause_after_ms(current, following), expected)

    def test_leaving_a_list_pauses_like_leaving_a_paragraph(self):
        current = _segment("Mục cuối.", kind="list_item")
        following = _segment("Đoạn văn tiếp.", kind="paragraph", ordinal=1)
        self.assertEqual(
            pause_after_ms(current, following), BLOCK_PAUSE_MS
        )


class SelectionPauseTests(unittest.TestCase):
    def test_each_joint_maps_to_its_pause(self):
        self.assertEqual(selection_pause_ms("Đoạn trước.", "block"), BLOCK_PAUSE_MS)
        self.assertEqual(selection_pause_ms("Dòng trước", "line"), LINE_PAUSE_MS)
        self.assertEqual(
            selection_pause_ms("Câu trọn.", "split"), SENTENCE_SPLIT_PAUSE_MS
        )
        self.assertEqual(selection_pause_ms("nửa chừng,", "split"), 0)


class SpeakableTextTests(unittest.TestCase):
    def test_bullet_glyphs_are_not_spoken(self):
        for text, expected in (
            ("• Táo đỏ", "Táo đỏ"),
            ("●▪ Táo", "Táo"),
            ("* Gạch markdown", "Gạch markdown"),
            ("- Gạch đầu dòng vẫn đọc ổn", "- Gạch đầu dòng vẫn đọc ổn"),
        ):
            with self.subTest(text=text):
                self.assertEqual(speakable_text(text), expected)

    def test_a_lone_bullet_keeps_its_original_text(self):
        self.assertEqual(speakable_text("•"), "•")

    def test_headings_are_spoken_with_a_final_period(self):
        self.assertEqual(
            speakable_text("Chương một Khởi đầu", kind="heading"),
            "Chương một Khởi đầu.",
        )
        self.assertEqual(
            speakable_text("Tựa «Đất rừng»", kind="heading"),
            "Tựa «Đất rừng».",
        )

    def test_headings_with_their_own_punctuation_stay_untouched(self):
        for text in ("Chương một.", "Vì sao?", "Phần mở:", "Đợi đã…"):
            with self.subTest(text=text):
                self.assertEqual(speakable_text(text, kind="heading"), text)

    def test_paragraphs_never_gain_a_period(self):
        self.assertEqual(speakable_text("không dấu cuối"), "không dấu cuối")
