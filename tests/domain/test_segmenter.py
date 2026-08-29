import dataclasses
import unittest
from unittest.mock import patch

from vieneu_reader.domain.models import Segment, stable_id
from vieneu_reader.domain.segmenter import (
    MAX_PASTED_TEXT_CHARS,
    TransientPart,
    normalize_paragraph,
    prepare_pasted_text,
    split_paragraph,
    split_transient_parts,
    split_transient_text,
)


class ParagraphNormalizationTests(unittest.TestCase):
    def test_normalization_composes_unicode_and_collapses_internal_whitespace(self):
        self.assertEqual(
            normalize_paragraph("  To\u0302i\t yêu\n  Việt Nam  "),
            "Tôi yêu Việt Nam",
        )

    def test_normalization_drops_empty_content(self):
        self.assertEqual(normalize_paragraph(" \n\t "), "")

    def test_pasted_text_accepts_the_limit_and_rejects_larger_input(self):
        at_limit = "a" * MAX_PASTED_TEXT_CHARS

        self.assertEqual(prepare_pasted_text(at_limit), at_limit)
        with self.assertRaisesRegex(ValueError, "too long"):
            prepare_pasted_text(at_limit + "b")

    def test_pasted_text_preserves_real_paragraphs_and_qt_separators(self):
        self.assertEqual(
            prepare_pasted_text("  Đoạn một.\n\n Đoạn hai.\u2029Đoạn ba.  "),
            "Đoạn một.\n\nĐoạn hai.\n\nĐoạn ba.",
        )


class ParagraphSegmentationTests(unittest.TestCase):
    def test_long_paragraph_prefers_a_vietnamese_sentence_boundary(self):
        parts = split_paragraph(
            "Câu đầu khá dài. Câu thứ hai cũng dài.",
            max_chars=24,
        )

        self.assertEqual(parts, ("Câu đầu khá dài.", "Câu thứ hai cũng dài."))

    def test_clause_boundary_wins_before_an_earlier_plain_space(self):
        parts = split_paragraph("Một hai ba, bốn năm sáu bảy", max_chars=13)

        self.assertEqual(parts, ("Một hai ba,", "bốn năm sáu", "bảy"))

    def test_whitespace_is_used_when_no_punctuation_fits(self):
        parts = split_paragraph("alpha beta gamma", max_chars=10)

        self.assertEqual(parts, ("alpha beta", "gamma"))

    def test_hard_cut_keeps_an_unbroken_word_within_the_limit(self):
        parts = split_paragraph("abcdefghijkl", max_chars=5)

        self.assertEqual(parts, ("abcde", "fghij", "kl"))

    def test_empty_input_produces_no_segments(self):
        self.assertEqual(split_paragraph(" \n ", max_chars=20), ())

    def test_every_segment_is_nonempty_and_within_the_limit(self):
        parts = split_paragraph(
            "Đây là câu một. Đây là câu hai, rồi còn phần tiếp theo rất dài.",
            max_chars=18,
        )

        self.assertTrue(parts)
        self.assertTrue(all(part and len(part) <= 18 for part in parts))

    def test_nonpositive_limit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "max_chars"):
            split_paragraph("Nội dung", max_chars=0)

    def test_transient_text_keeps_short_paragraphs_as_separate_parts(self):
        self.assertEqual(
            split_transient_text("Đoạn một.\n\nĐoạn hai.", max_chars=240),
            ("Đoạn một.", "Đoạn hai."),
        )

    def test_unbroken_text_does_not_copy_the_remaining_suffix_each_iteration(self):
        class SliceTrackingText(str):
            copied_suffix_chars = 0

            def __getitem__(self, key):
                result = super().__getitem__(key)
                if isinstance(key, slice) and key.start and key.stop is None:
                    type(self).copied_suffix_chars += len(result)
                return type(self)(result) if isinstance(result, str) else result

            def lstrip(self, chars=None):
                return type(self)(super().lstrip(chars))

        text = SliceTrackingText("a" * 10_000)
        with patch(
            "vieneu_reader.domain.segmenter.normalize_paragraph",
            return_value=text,
        ):
            parts = split_paragraph(text, max_chars=100)

        self.assertEqual("".join(parts), text)
        self.assertLessEqual(SliceTrackingText.copied_suffix_chars, len(text) * 2)


class StableDomainIdentityTests(unittest.TestCase):
    def test_stable_id_uses_ordered_nul_separated_utf8_components(self):
        self.assertEqual(
            stable_id("book", "chapter", "1"),
            "1f14eb493e4b33788b10c45d4495f1c348548a46a024988c9776f2c2412a4389",
        )

    def test_segment_is_immutable(self):
        segment = Segment(
            id="segment-id",
            chapter_id="chapter-id",
            ordinal=0,
            text="Nội dung",
        )

        with self.assertRaises(dataclasses.FrozenInstanceError):
            segment.text = "Đã đổi"


class TransientPartTests(unittest.TestCase):
    """One-off text keeps its authored line structure for the voice."""

    def test_paragraphs_lines_and_wrapped_lines_get_their_joints(self):
        parts = split_transient_parts(
            "Đoạn văn đầu tiên.\n\n"
            "Dòng thơ thứ nhất\n"
            "Dòng thơ thứ hai\n"
            "và một mẩu nối tiếp thường"
        )

        self.assertEqual(
            parts,
            (
                TransientPart("Đoạn văn đầu tiên.", "block"),
                TransientPart("Dòng thơ thứ nhất", "block"),
                # The lowercase continuation folds back into the line above
                # because that line never finished its sentence.
                TransientPart("Dòng thơ thứ hai và một mẩu nối tiếp thường", "line"),
            ),
        )

    def test_hard_wrapped_prose_folds_back_into_one_part(self):
        parts = split_transient_parts(
            "dòng một chưa trọn câu\nnên vẫn nói tiếp ở đây."
        )

        self.assertEqual(
            parts,
            (TransientPart("dòng một chưa trọn câu nên vẫn nói tiếp ở đây.", "block"),),
        )

    def test_a_new_line_after_a_finished_sentence_keeps_its_break(self):
        parts = split_transient_parts("Câu trước đã trọn.\nxuống dòng vẫn giữ")

        self.assertEqual(
            [part.joint for part in parts],
            ["block", "line"],
        )

    def test_a_long_line_still_splits_with_split_joints(self):
        long_line = "Một câu khá dài được lặp lại để vượt qua cửa sổ đọc. " * 6
        parts = split_transient_parts(long_line)

        self.assertGreater(len(parts), 1)
        self.assertEqual(parts[0].joint, "block")
        self.assertEqual({part.joint for part in parts[1:]}, {"split"})

    def test_split_transient_text_returns_the_same_texts(self):
        text = "Đoạn một.\n\nDòng A\nDòng B"
        self.assertEqual(
            split_transient_text(text),
            tuple(part.text for part in split_transient_parts(text)),
        )

    def test_transient_parts_enforce_the_pasted_size_limit(self):
        with self.assertRaises(ValueError):
            split_transient_parts("a" * (MAX_PASTED_TEXT_CHARS + 1))


if __name__ == "__main__":
    unittest.main()
