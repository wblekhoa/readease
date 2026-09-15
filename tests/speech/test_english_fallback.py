"""The out-of-lexicon reader that ships in the package: two small ONNX
graphs and an alphabet, exported once from the network the original G2P
falls back to. Checked here as shipped, since the bundle carries them."""

from __future__ import annotations

import unittest

from vieneu_reader.speech.english import fallback
from vieneu_reader.speech.english.g2p import MToken, US_VOCAB, Underscore


class ShippedFallbackTests(unittest.TestCase):
    def test_the_assets_are_present_and_small(self) -> None:
        for path in (fallback.ENCODER, fallback.DECODER, fallback.ALPHABET):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
        total = fallback.ENCODER.stat().st_size + fallback.DECODER.stat().st_size
        # A network that is 3 MB is a package asset; one that is not, is not.
        self.assertLess(total, 4_000_000)

    def test_a_name_comes_back_in_the_lexicon_alphabet_and_deterministically(self) -> None:
        reader = fallback.Fallback()

        first = reader.phonemes("Kowalczyk")
        second = reader.phonemes("Kowalczyk")

        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertTrue(all(char in US_VOCAB for char in first), first)

    def test_it_answers_the_g2p_with_a_rating_below_the_lexicon(self) -> None:
        token = MToken(text="Brockmann", tag="NNP", whitespace=" ", _=Underscore(is_head=True))

        phonemes, rating = fallback.Fallback()(token)

        self.assertTrue(phonemes)
        self.assertEqual(rating, fallback.RATING)
        self.assertLess(fallback.RATING, 3)
