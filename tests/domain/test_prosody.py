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
    speak_links,
    speak_roman_numerals,
    speak_with_notes,
    speakable_text,
    split_sentences,
    unshout,
    _text_without_labels,
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
        # The colon introducing the quote is its own break; what matters here
        # is that the question mark keeps its closing quote rather than
        # stranding it at the head of the next piece.
        self.assertEqual(
            split_sentences('Anh ấy hỏi: "Đi đâu?" Rồi im lặng.'),
            ("Anh ấy hỏi:", '"Đi đâu?"', "Rồi im lặng."),
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


class ClauseSplittingTests(unittest.TestCase):
    """A colon and a dash are breaks the voice will not take on its own."""

    def test_a_colon_introducing_something_is_a_break(self):
        self.assertEqual(
            split_sentences("Chú giải ảnh: Dòng biển báo cùng mũi tên."),
            ("Chú giải ảnh:", "Dòng biển báo cùng mũi tên."),
        )

    def test_a_dash_sets_an_aside_apart_even_with_no_spaces(self):
        self.assertEqual(
            split_sentences("sơn ngay mép đường—ngắn gọn, đúng lúc."),
            ("sơn ngay mép đường—", "ngắn gọn, đúng lúc."),
        )

    def test_a_colon_with_no_gap_after_it_is_not_a_break(self):
        for text in (
            "Chuyến bay lúc 10:30 sáng.",
            "Xem tại https://readease.vn nhé.",
            "Tỉ lệ 3:1 là hợp lý.",
        ):
            with self.subTest(text=text):
                self.assertEqual(split_sentences(text), (text,))

    def test_a_dash_before_a_number_is_still_an_aside(self):
        """'kể—99 xu': a letter before, a number after. The range guard used
        to refuse any dash that touched a digit, so the voice ran straight
        through this one (owner, 2026-09-02)."""
        self.assertEqual(
            split_sentences("Giá kể—99 xu, thế là xong."),
            ("Giá kể—", "99 xu, thế là xong."),
        )
        self.assertEqual(
            split_sentences("Chỉ 3 người—và họ đều đúng."),
            ("Chỉ 3 người—", "và họ đều đúng."),
        )

    def test_a_spaced_range_is_still_a_range(self):
        self.assertEqual(
            split_sentences("Giai đoạn 1975 — 1980 rất khó."),
            ("Giai đoạn 1975 — 1980 rất khó.",),
        )

    def test_a_spaced_hyphen_is_a_dash_but_a_tight_one_is_not(self):
        self.assertEqual(
            split_sentences("Anh - em cùng đi."), ("Anh -", "em cùng đi.")
        )
        self.assertEqual(split_sentences("Tháng 1-2 rất lạnh."), ("Tháng 1-2 rất lạnh.",))
        self.assertEqual(split_sentences("Quan hệ Anh-Mỹ bền."), ("Quan hệ Anh-Mỹ bền.",))

    def test_a_dash_between_numbers_is_a_range_not_an_aside(self):
        self.assertEqual(
            split_sentences("Giai đoạn 1975—1980 rất khó."),
            ("Giai đoạn 1975—1980 rất khó.",),
        )

    def test_a_dash_that_opens_the_line_has_nothing_before_it_to_end(self):
        self.assertEqual(
            split_sentences("—Anh đi đâu đấy?"), ("—Anh đi đâu đấy?",)
        )

    def test_full_stops_and_clause_marks_are_both_honoured_in_one_paragraph(self):
        self.assertEqual(
            split_sentences(
                "Chú giải ảnh: Dòng chữ nằm ở mép đường—rất khó bỏ qua. "
                "Nó từng cứu tôi."
            ),
            (
                "Chú giải ảnh:",
                "Dòng chữ nằm ở mép đường—",
                "rất khó bỏ qua.",
                "Nó từng cứu tôi.",
            ),
        )


class UnshoutTests(unittest.TestCase):
    """Capitals slow the voice down and make it less predictable."""

    def test_a_run_of_shouted_words_is_lowered(self):
        self.assertEqual(
            unshout('Dòng "LOOK RIGHT" (NHÌN BÊN PHẢI) cùng mũi tên.'),
            'Dòng "look right" (nhìn bên phải) cùng mũi tên.',
        )

    def test_a_shouted_opening_keeps_its_sentence_capital(self):
        self.assertEqual(unshout("CHƯƠNG MỘT: KHỞI ĐẦU"), "Chương một: khởi đầu")
        self.assertEqual(unshout('"LOOK RIGHT" là biển báo.'), '"Look right" là biển báo.')

    def test_a_lone_capitalised_word_is_left_alone(self):
        for text in (
            "Anh ấy làm ở NASA mỗi ngày.",
            "Tôi xem TV mỗi tối.",
            "Chỉ một từ ĐÚNG được nhấn.",
        ):
            with self.subTest(text=text):
                self.assertEqual(unshout(text), text)

    def test_abbreviations_without_vowels_keep_their_letters(self):
        # "tp hcm" would ask the voice to pronounce what should be spelled.
        self.assertEqual(unshout("Trụ sở ở TP HCM rất lớn."), "Trụ sở ở TP HCM rất lớn.")
        self.assertEqual(unshout("Xem BBC và CNN."), "Xem BBC và CNN.")

    def test_ordinary_text_is_returned_unchanged(self):
        for text in ("Câu thường không đổi gì cả.", "", "   "):
            with self.subTest(text=text):
                self.assertEqual(unshout(text), text)

    def test_the_voice_gets_the_lowered_text_but_the_page_does_not(self):
        shouted = 'Dòng "LOOK RIGHT" phía trước.'
        self.assertEqual(
            speakable_text(shouted), 'Dòng "look right" phía trước.'
        )
        self.assertEqual(shouted, 'Dòng "LOOK RIGHT" phía trước.')


class OrdinalMarkTests(unittest.TestCase):
    """'#1' is printed, 'thứ nhất' is said (owner, 2026-09-02)."""

    def test_the_irregular_ones_are_right(self) -> None:
        from vieneu_reader.domain.prosody import ordinal_words

        self.assertEqual(ordinal_words(1), "thứ nhất")
        self.assertEqual(ordinal_words(2), "thứ hai")
        self.assertEqual(ordinal_words(4), "thứ tư")
        self.assertEqual(ordinal_words(5), "thứ năm")
        self.assertEqual(ordinal_words(10), "thứ mười")
        self.assertEqual(ordinal_words(11), "thứ mười một")
        self.assertEqual(ordinal_words(14), "thứ mười bốn")
        self.assertEqual(ordinal_words(15), "thứ mười lăm")
        self.assertEqual(ordinal_words(21), "thứ hai mươi mốt")
        self.assertEqual(ordinal_words(24), "thứ hai mươi tư")
        self.assertEqual(ordinal_words(25), "thứ hai mươi lăm")
        self.assertEqual(ordinal_words(30), "thứ ba mươi")
        self.assertEqual(ordinal_words(120), "thứ 120")

    def test_marks_are_spoken_as_ordinals_wherever_they_sit(self) -> None:
        from vieneu_reader.domain.prosody import speakable_text

        # The two shapes found in the owner's library.
        self.assertEqual(
            speakable_text("#1. Nói thẳng nhé: Cuốn sách đã cũ"),
            "thứ nhất. Nói thẳng nhé: Cuốn sách đã cũ",
        )
        self.assertEqual(
            speakable_text("Sự thật #2: Chúng ta không chọn phương án tối ưu."),
            "Sự thật thứ hai: Chúng ta không chọn phương án tối ưu.",
        )

    def test_a_hash_that_is_not_an_ordinal_is_left_alone(self) -> None:
        from vieneu_reader.domain.prosody import speakable_text

        self.assertEqual(speakable_text("Tìm #hashtag trên mạng."), "Tìm #hashtag trên mạng.")
        self.assertEqual(speakable_text("Viết bằng C# nhé."), "Viết bằng C# nhé.")
        self.assertEqual(speakable_text("Mã ##12 nội bộ."), "Mã ##12 nội bộ.")


class NoteMarkTests(unittest.TestCase):
    """Footnote superscripts are read by the eye, never by the voice."""

    def test_a_note_mark_after_a_period_is_not_spoken(self) -> None:
        self.assertEqual(
            speakable_text("đã cho ta Tang.³ Developer và designer"),
            "đã cho ta Tang. Developer và designer",
        )

    def test_a_note_mark_glued_to_a_word_is_not_spoken(self) -> None:
        self.assertEqual(
            speakable_text("một số người³ cố nhờ practitioner"),
            "một số người cố nhờ practitioner",
        )

    def test_a_multi_digit_mark_goes_as_one(self) -> None:
        self.assertEqual(speakable_text("như đã nói.¹²"), "như đã nói.")

    def test_a_power_after_a_digit_is_arithmetic_and_stays(self) -> None:
        self.assertEqual(speakable_text("10³ lần"), "10³ lần")




class ZeroPaddedHeadingTests(unittest.TestCase):
    """A numbered heading says its number, never its padding."""

    def test_a_zero_padded_heading_drops_the_zero(self) -> None:
        self.assertEqual(speakable_text("01", "heading"), "1.")
        self.assertEqual(speakable_text("07. Ánh sáng", "heading"), "7. Ánh sáng.")

    def test_a_lone_zero_and_a_decimal_keep_their_zero(self) -> None:
        self.assertEqual(speakable_text("0", "heading"), "0.")
        self.assertEqual(speakable_text("0.5 giây", "heading"), "0.5 giây.")

    def test_a_paragraph_keeps_its_leading_zero(self) -> None:
        self.assertEqual(speakable_text("01/09 là ngày họp"), "01/09 là ngày họp")




class EnumeratorTests(unittest.TestCase):
    """The sentence from the owner's screenshot, spoken the way the ear chose."""

    def test_the_approved_render_is_what_the_voice_gets(self) -> None:
        self.assertEqual(
            speakable_text(
                "Giống Ginger, ta tập trung vào những từ và cụm từ có vẻ khớp với "
                "(a) nhiệm vụ hiện tại hoặc (b) sở thích cá nhân đang có."
            ),
            "Giống Ginger, ta tập trung vào những từ và cụm từ có vẻ khớp với "
            "a, nhiệm vụ hiện tại, hoặc b, sở thích cá nhân đang có.",
        )

    def test_a_reference_keeps_its_letter_without_a_pause(self) -> None:
        self.assertEqual(speakable_text("xem lại mục (b) ở trên"), "xem lại mục b ở trên")

    def test_an_existing_comma_before_the_conjunction_is_not_doubled(self) -> None:
        self.assertEqual(speakable_text("(a) đọc, hoặc (b) nghe"), "a, đọc, hoặc b, nghe")

    def test_a_plural_bracket_and_a_roman_numeral_are_left_alone(self) -> None:
        self.assertEqual(speakable_text("the book(s) in (ii) above"), "the book(s) in (ii) above")



class NoteSpeechTests(unittest.TestCase):
    """A footnote is written for an eye that can look down and come back.

    An ear cannot. Read at the number the note cuts a clause in half; read
    at the back of the book it arrives eighty times over, detached from
    every sentence that needed it; read not at all, the number is still
    spoken as a stray "sáu" glued to the word before it. So: finish the
    sentence, announce the note, read it, carry on.
    """

    def pieces(self, text, notes):
        return speak_with_notes(text, notes)

    def test_a_note_is_read_after_the_sentence_that_carries_it(self) -> None:
        # The owner's own example: the number sits mid-sentence, before a
        # dash clause, so the sentence finishes before the note starts.
        text = "Nên đọc thứ gì tiếp theo 6 - dù bị ép đọc. Câu sau."
        self.assertEqual(
            self.pieces(text, [(25, 1, "Benoit Mandelbrot đã viết vậy.")]),
            (
                ("Nên đọc thứ gì tiếp theo - dù bị ép đọc.", False),
                ("Benoit Mandelbrot đã viết vậy.", True),
                ("Câu sau.", False),
            ),
        )

    def test_the_number_never_reaches_the_voice(self) -> None:
        # It used to: `drop_note_marks` only ever removed the superscript
        # GLYPHS, and a book whose references are ordinary digits in a link
        # had the voice read "sáu" in the middle of the clause.
        spoken, _ = _text_without_labels("người 6 nói vậy", [(6, 1)])
        self.assertEqual(spoken, "người nói vậy")

    def test_punctuation_closes_up_behind_the_number(self) -> None:
        # "(tương lai) 2 ." has to end as "(tương lai)." - a space left
        # hanging in front of a full stop is a stumble in the voice.
        spoken, _ = _text_without_labels("hướng tới tương lai) 2 .", [(21, 1)])
        self.assertEqual(spoken, "hướng tới tương lai).")

    def test_a_note_at_the_end_of_a_paragraph_follows_it(self) -> None:
        self.assertEqual(
            self.pieces("Cả đoạn kết thúc ở đây. 7", [(24, 1, "Ghi chú cuối.")]),
            (("Cả đoạn kết thúc ở đây.", False), ("Ghi chú cuối.", True)),
        )

    def test_two_notes_in_one_sentence_come_out_in_the_printed_order(self) -> None:
        self.assertEqual(
            self.pieces(
                "Một câu 1 và 2 cùng một câu. Câu sau.",
                [(8, 1, "Ghi A."), (13, 1, "Ghi B.")],
            ),
            (
                ("Một câu và cùng một câu.", False),
                ("Ghi A.", True),
                ("Ghi B.", True),
                ("Câu sau.", False),
            ),
        )

    def test_two_notes_in_different_sentences_each_follow_their_own(self) -> None:
        self.assertEqual(
            self.pieces(
                "Câu một 1 xong. Câu hai 2 xong.",
                [(8, 1, "Ghi A."), (24, 1, "Ghi B.")],
            ),
            (
                ("Câu một xong.", False),
                ("Ghi A.", True),
                ("Câu hai xong.", False),
                ("Ghi B.", True),
            ),
        )

    def test_a_sentence_that_never_ends_still_finishes_before_the_note(self) -> None:
        # A heading, or a paragraph the publisher left without a full stop:
        # the note goes after all of it rather than after nothing.
        self.assertEqual(
            self.pieces("Tiêu đề có chú thích 3", [(21, 1, "Ghi chú.")]),
            (("Tiêu đề có chú thích", False), ("Ghi chú.", True)),
        )

    def test_a_segment_with_no_notes_is_left_exactly_as_it_was(self) -> None:
        self.assertEqual(
            self.pieces("Không có chú thích nào.", []),
            (("Không có chú thích nào.", False),),
        )

    def test_a_note_with_no_words_is_not_announced(self) -> None:
        # An unreadable note leaves a hole rather than a "Nói thêm," with
        # nothing after it.
        self.assertEqual(
            self.pieces("Câu có chú thích 4 rỗng.", [(17, 1, "  ")]),
            (("Câu có chú thích rỗng.", False),),
        )


class RomanNumeralTests(unittest.TestCase):
    """"Phần II" is a number the author wrote as a number.

    The shipped build read it as the letter - "phần y" (owner, 05/09). The
    library has 61 of them and every one is behind "Phần".
    """

    def test_a_division_word_makes_the_letters_a_number(self) -> None:
        self.assertEqual(
            speak_roman_numerals("Phần I và Phần II liên kết chặt chẽ với nhau."),
            "Phần một và Phần hai liên kết chặt chẽ với nhau.",
        )
        self.assertEqual(speak_roman_numerals("Chương XIV"), "Chương mười bốn")
        self.assertEqual(speak_roman_numerals("Phần XXI"), "Phần hai mươi mốt")

    def test_letters_without_a_division_word_stay_letters(self) -> None:
        # Both of these are in the owner's library, and both would become
        # numbers under a rule that only looked at the capitals.
        self.assertEqual(speak_roman_numerals("OS X là hệ điều hành"), "OS X là hệ điều hành")
        self.assertEqual(speak_roman_numerals("Catherine V của Nga"), "Catherine V của Nga")

    def test_a_run_that_is_not_a_numeral_is_left_alone(self) -> None:
        # "IIII" sums to 4 and "VV" to 10; neither is a numeral anyone wrote.
        self.assertEqual(speak_roman_numerals("Phần IIII"), "Phần IIII")
        self.assertEqual(speak_roman_numerals("Phần VV"), "Phần VV")

    def test_the_page_is_not_touched(self) -> None:
        text = "Phần II"
        speak_roman_numerals(text)
        self.assertEqual(text, "Phần II")


class LinkTests(unittest.TestCase):
    """A URL is written to be copied; spoken whole it is unusable."""

    def test_the_site_is_named_and_the_path_is_dropped(self) -> None:
        self.assertEqual(
            speak_links("Bạn có thể tìm chúng trên Flickr tại www.flickr.com/photos/rosenfeldmedia/sets/."),
            "Bạn có thể tìm chúng trên Flickr tại địa chỉ flickr chấm com.",
        )
        self.assertEqual(speak_links("rosenfeldmedia.com/books/"), "địa chỉ rosenfeldmedia chấm com")

    def test_the_scheme_and_every_www_go(self) -> None:
        self.assertEqual(
            speak_links("http://www.apa.org/pubs/journals/tra/index.aspx"),
            "địa chỉ apa chấm org",
        )
        # www8, in the library. Stripping only "www." leaves the digit behind.
        self.assertEqual(
            speak_links("https://www8.gsb.columbia.edu/newsroom/newsn/1957/x"),
            "địa chỉ gsb chấm columbia chấm edu",
        )

    def test_the_sentence_keeps_its_full_stop(self) -> None:
        self.assertEqual(speak_links("Xem svpg.com."), "Xem địa chỉ svpg chấm com.")

    def test_a_link_already_announced_is_not_announced_twice(self) -> None:
        self.assertEqual(
            speak_links("tại địa chỉ www.wiley.com/go/permissions."),
            "tại địa chỉ wiley chấm com.",
        )
        self.assertEqual(speak_links("ở trang svpg.com."), "ở trang svpg chấm com.")

    def test_things_that_only_look_like_addresses_are_left_alone(self) -> None:
        # Both of these appeared in the sweep the moment the top-level domain
        # was not checked: a price with a slash, and an abbreviation.
        self.assertEqual(speak_links("Giá là 1.000/năm."), "Giá là 1.000/năm.")
        self.assertEqual(speak_links("Anh ấy nói v.v. rồi đi."), "Anh ấy nói v.v. rồi đi.")
