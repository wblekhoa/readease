"""The number in the button, and the scope it is a number FOR."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vieneu_reader.speech.external.estimate import (  # noqa: E402
    ScopeEstimate, estimate_scope, scope_end, scope_start,
)
from vieneu_reader.speech.external.pricing import PRICES, price_for  # noqa: E402


# Three chapters: 2, 3 and 2 utterances.
CHAPTER_OF = (0, 0, 1, 1, 1, 2, 2)
TEXTS = ("a" * 100, "b" * 200, "c" * 300, "d" * 400, "e" * 500, "f" * 600, "g" * 700)


class ScopeTests(unittest.TestCase):
    def test_this_chapter_means_the_rest_of_the_chapter_you_are_in(self) -> None:
        # Resuming in the MIDDLE of chapter two and asking for "chương này"
        # buys what is left of it, not a chapter's worth from here.
        self.assertEqual(scope_end(CHAPTER_OF, 3, 1), 5)
        self.assertEqual(scope_end(CHAPTER_OF, 2, 1), 5)

    def test_two_chapters_reaches_the_end_of_the_next_one(self) -> None:
        self.assertEqual(scope_end(CHAPTER_OF, 3, 2), 7)

    def test_asking_for_more_chapters_than_the_book_has_stops_at_the_end(self) -> None:
        self.assertEqual(scope_end(CHAPTER_OF, 0, 99), len(CHAPTER_OF))

    def test_the_whole_book_and_the_empty_scope(self) -> None:
        self.assertEqual(scope_end(CHAPTER_OF, 0, None), len(CHAPTER_OF))
        self.assertEqual(scope_end(CHAPTER_OF, 2, 0), 2)

    def test_a_start_past_the_end_buys_nothing(self) -> None:
        self.assertEqual(scope_end(CHAPTER_OF, 99, None), len(CHAPTER_OF))


class CeilingTests(unittest.TestCase):
    """The quote covers the whole scope, wherever inside it a reading starts."""

    def test_it_backs_up_to_the_start_of_the_chapter_you_are_in(self) -> None:
        # Chapter two is utterances 2..4. Resuming at 4 still quotes from 2,
        # because a click on utterance 2 costs that much and carries the very
        # same scope.
        self.assertEqual(scope_start(CHAPTER_OF, 4, 1), 2)
        self.assertEqual(scope_start(CHAPTER_OF, 2, 1), 2)

    def test_more_chapters_still_start_at_the_one_you_are_in(self) -> None:
        self.assertEqual(scope_start(CHAPTER_OF, 4, 2), 2)

    def test_the_whole_book_starts_at_the_whole_book(self) -> None:
        # With no ceiling on chapters, a click on the first paragraph reads
        # everything - so everything is what the figure has to cover.
        self.assertEqual(scope_start(CHAPTER_OF, 5, None), 0)

    def test_a_ceiling_is_never_smaller_than_what_resuming_would_cost(self) -> None:
        price = price_for("tts-1")
        for start in range(len(CHAPTER_OF)):
            for chapters in (1, 2, None):
                resume = estimate_scope(TEXTS, CHAPTER_OF, start, chapters, price)
                ceiling = estimate_scope(
                    TEXTS, CHAPTER_OF,
                    scope_start(CHAPTER_OF, start, chapters), chapters, price,
                )
                self.assertGreaterEqual(
                    ceiling.chars, resume.chars,
                    f"start={start} chapters={chapters}",
                )

    def test_the_ten_times_gap_this_was_written_for(self) -> None:
        # A ten-paragraph chapter: resuming at the last one quoted $0.018
        # while clicking the first cost $0.180 - the same scope, ten times
        # the money, and only one of those numbers was ever on screen.
        texts = ["x" * 1200] * 10
        chapters = [0] * 10
        price = price_for("tts-1")
        self.assertEqual(estimate_scope(texts, chapters, 9, 1, price).usd, 0.018)
        self.assertEqual(
            estimate_scope(
                texts, chapters, scope_start(chapters, 9, 1), 1, price
            ).usd,
            0.18,
        )


class EstimateTests(unittest.TestCase):
    def test_it_counts_the_characters_actually_in_scope(self) -> None:
        price = price_for("tts-1")
        assert price is not None
        result = estimate_scope(TEXTS, CHAPTER_OF, 2, 1, price)
        self.assertEqual(result.chars, 300 + 400 + 500)
        self.assertEqual(result.utterances, 3)
        self.assertEqual(result.chapters, 1)

    def test_the_price_is_the_provider_s_own_arithmetic(self) -> None:
        # 1200 characters at $15 per 1M is 1.8 cents. A reader deciding
        # whether to spend it deserves the real number, not a rounded one.
        price = price_for("tts-1")
        assert price is not None
        result = estimate_scope(("x" * 1200,), (0,), 0, None, price)
        self.assertEqual(result.usd, 0.018)
        self.assertEqual(result.units, 1200)
        self.assertEqual(result.unit, "characters")

    def test_elevenlabs_counts_in_the_unit_its_own_dashboard_uses(self) -> None:
        price = price_for("eleven_flash_v2_5")
        assert price is not None
        result = estimate_scope(("x" * 10_000,), (0,), 0, None, price)
        self.assertEqual(result.usd, 0.5)
        self.assertEqual(result.unit, "credits")

    def test_a_chapter_of_a_real_size_lands_where_the_planning_said(self) -> None:
        # ~12k characters is an ordinary chapter. The plan quoted ~$0.18 on
        # tts-1 and ~$1.20 on ElevenLabs v3; if either drifts, the figure in
        # the button drifts with it and this test says so.
        chapter = "x" * 12_000
        cheap = estimate_scope((chapter,), (0,), 0, None, price_for("tts-1"))
        dear = estimate_scope((chapter,), (0,), 0, None, price_for("eleven_v3"))
        self.assertEqual(cheap.usd, 0.18)
        self.assertEqual(dear.usd, 1.2)

    def test_every_price_carries_the_day_it_was_quoted(self) -> None:
        for price in PRICES:
            result = estimate_scope(("x",), (0,), 0, None, price)
            self.assertEqual(result.price_dated, "2026-09-04")
            self.assertGreater(price.usd_per_1k_chars, 0)

    def test_mismatched_inputs_are_refused_rather_than_guessed(self) -> None:
        with self.assertRaises(ValueError):
            estimate_scope(("a", "b"), (0,), 0, None, price_for("tts-1"))

    def test_nothing_in_scope_costs_nothing(self) -> None:
        result = estimate_scope(TEXTS, CHAPTER_OF, 2, 0, price_for("tts-1"))
        self.assertEqual((result.chars, result.usd, result.utterances), (0, 0.0, 0))
        self.assertIsInstance(result, ScopeEstimate)


if __name__ == "__main__":
    unittest.main()
