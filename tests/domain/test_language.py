"""Which language a book is in, decided by the book rather than by a setting.

This exists because of one rule (owner, 07/09/2026): never read English with
the Vietnamese model. A guard that only fires when somebody has switched the
INTERFACE to English leaves the rule unenforced for the reader most likely to
hit it - a Vietnamese speaker with an English book.
"""

from __future__ import annotations

import unittest

from vieneu_reader.domain.language import (
    language_of_text,
    language_of_texts,
    vietnamese_share,
)


VIETNAMESE = (
    "Hôm nay trời trong xanh, gió nhẹ thổi qua hàng cây bên đường, và tôi "
    "nghĩ về những ngày đã cũ, về những người đã đi qua đời mình."
)
ENGLISH = (
    "Reading is the art of listening with your eyes. This chapter explains "
    "why the market changed after the war, and what the survivors did next."
)


class TextTests(unittest.TestCase):
    def test_the_two_languages_are_told_apart(self) -> None:
        self.assertEqual(language_of_text(VIETNAMESE), "vi")
        self.assertEqual(language_of_text(ENGLISH), "en")

    def test_vietnamese_names_do_not_make_an_english_book_vietnamese(self) -> None:
        # The case that has to work: an English book that mentions Vietnam.
        text = (
            "He met Nguyễn Văn A in Hà Nội and they discussed the project for "
            "several hours that afternoon, then walked back along the river "
            "and talked about everything except the thing that mattered."
        )
        self.assertEqual(language_of_text(text), "en")

    def test_english_terms_do_not_make_a_vietnamese_book_english(self) -> None:
        text = (
            "Chúng ta dùng design system và component library của công ty, gọi "
            "là DS-Token, để dựng giao diện cho mọi sản phẩm."
        )
        self.assertEqual(language_of_text(text), "vi")

    def test_too_little_text_is_not_evidence(self) -> None:
        # A page number, a caption of digits, an empty segment: these decide
        # nothing, and must not flip a book's language.
        for nothing in ("12", "", "   ", "3.1"):
            with self.subTest(nothing=nothing):
                self.assertEqual(language_of_text(nothing, "vi"), "vi")
                self.assertEqual(language_of_text(nothing, "en"), "en")

    def test_the_share_is_zero_for_text_with_no_vietnamese_orthography(self) -> None:
        self.assertEqual(vietnamese_share(ENGLISH), 0.0)
        self.assertGreater(vietnamese_share(VIETNAMESE), 0.2)


class BookTests(unittest.TestCase):
    def test_an_english_opening_does_not_decide_a_vietnamese_book(self) -> None:
        # Books open with title pages, dedications and English epigraphs. The
        # sample is spread across the whole book for exactly this reason.
        segments = [ENGLISH] * 5 + [VIETNAMESE] * 300
        self.assertEqual(language_of_texts(segments), "vi")

    def test_a_vietnamese_dedication_does_not_decide_an_english_book(self) -> None:
        segments = [VIETNAMESE] * 3 + [ENGLISH] * 300
        self.assertEqual(language_of_texts(segments), "en")

    def test_the_second_half_of_a_long_book_is_sampled_too(self) -> None:
        # A book long enough that its first 20,000 letters are all one
        # language. Reading whole parts until the budget ran out never got
        # past that front matter, so this book came back English.
        halves = [ENGLISH] * 300 + [VIETNAMESE] * 300
        self.assertEqual(language_of_texts(halves), "vi")

    def test_a_book_that_really_is_mostly_english_reads_as_english(self) -> None:
        # The other side of the same coin: sampling the whole book means a
        # book that is five-sixths English is English, whatever its last
        # chapters are. This is a judgement about volume, not about order.
        self.assertEqual(
            language_of_texts([ENGLISH] * 1000 + [VIETNAMESE] * 200), "en"
        )

    def test_a_book_with_nothing_to_read_falls_back(self) -> None:
        self.assertEqual(language_of_texts([], "en"), "en")
        self.assertEqual(language_of_texts(["", "  "], "vi"), "vi")

    def test_a_generator_is_read_once_and_still_answers(self) -> None:
        # The server hands this a generator over every segment in the book.
        segments = (text for text in [VIETNAMESE] * 40)
        self.assertEqual(language_of_texts(segments), "vi")
