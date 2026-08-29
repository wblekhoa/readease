import unittest

from vieneu_reader.domain.models import Segment
from vieneu_reader.domain.prosody import (
    BLOCK_PAUSE_MS,
    CHAPTER_PAUSE_MS,
    LINE_PAUSE_MS,
    SENTENCE_PAUSE_MS,
    ends_sentence,
    final_punctuation,
    pause_after_ms,
    selection_pause_ms,
    speakable_text,
    split_sentences,
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
            ("Câu đã trọn vẹn.", SENTENCE_PAUSE_MS),
            ("Anh ấy hỏi?”", SENTENCE_PAUSE_MS),
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
            selection_pause_ms("Câu trọn.", "split"), SENTENCE_PAUSE_MS
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


class SentenceSplittingTests(unittest.TestCase):
    """A paragraph is read one sentence at a time, so the cuts must be right."""

    def test_a_full_stop_between_sentences_is_a_cut(self):
        self.assertEqual(
            split_sentences(
                "Tôi tin nó đã cứu mạng rất nhiều du khách vốn quen xe chạy "
                "đến từ hướng ngược lại. (Ít nhất nó từng cứu tôi một lần.)"
            ),
            (
                "Tôi tin nó đã cứu mạng rất nhiều du khách vốn quen xe chạy "
                "đến từ hướng ngược lại.",
                "(Ít nhất nó từng cứu tôi một lần.)",
            ),
        )

    def test_question_and_exclamation_marks_also_end_sentences(self):
        self.assertEqual(
            split_sentences("Anh đi đâu? Tôi về nhà! Thế thôi."),
            ("Anh đi đâu?", "Tôi về nhà!", "Thế thôi."),
        )

    def test_a_closing_quote_stays_with_the_sentence_it_closes(self):
        self.assertEqual(
            split_sentences('Anh ấy hỏi: "Đi đâu?" Rồi im lặng.'),
            ('Anh ấy hỏi: "Đi đâu?"', "Rồi im lặng."),
        )

    def test_titles_and_initials_are_not_mistaken_for_full_stops(self):
        for text in (
            "TS. Nguyễn Văn A đã tới.",
            "T. P. Hồ Chí Minh rất đông.",
            "Gặp Dr. Watson ở đó.",
        ):
            with self.subTest(text=text):
                self.assertEqual(split_sentences(text), (text,))

    def test_a_decimal_point_is_not_a_full_stop(self):
        self.assertEqual(
            split_sentences("Giá là 3.5 triệu. Rẻ thật!"),
            ("Giá là 3.5 triệu.", "Rẻ thật!"),
        )

    def test_a_lowercase_continuation_is_not_a_new_sentence(self):
        self.assertEqual(
            split_sentences("Táo, cam, v.v. rồi thì mít."),
            ("Táo, cam, v.v. rồi thì mít.",),
        )

    def test_text_without_a_full_stop_is_one_piece(self):
        self.assertEqual(
            split_sentences("Không có dấu chấm nào ở đây"),
            ("Không có dấu chấm nào ở đây",),
        )

    def test_empty_text_yields_nothing(self):
        self.assertEqual(split_sentences("   "), ())

    def test_a_dash_opens_a_line_of_dialogue(self):
        self.assertEqual(
            split_sentences("Cô ấy gật đầu. - Vâng, em hiểu."),
            ("Cô ấy gật đầu.", "- Vâng, em hiểu."),
        )

