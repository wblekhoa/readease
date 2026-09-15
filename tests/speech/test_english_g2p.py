"""The ported English G2P, against a tagger of its own and a lexicon of
a few words, so the rules can be checked without spaCy or the 6 MB lexicon.

The port was proved byte-identical to the original it was taken from on
1,787 segments of real English books (15/09/2026); what stays here is the
contract the voice depends on: digits never reach the model, an unknown
word goes to the fallback rather than being dropped, and the number speller
says what the original's did.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from vieneu_reader.speech.english import numbers
from vieneu_reader.speech.english.g2p import G2P, Lexicon, MToken, subtokenize

GOLD = {
    "the": "ði", "a": "A", "cat": "kˈæt", "sat": "sˈæt", "on": "ˈɑn", "mat": "mˈæt",
    "in": "ɪn", "read": {"DEFAULT": "ɹˈid", "VBD": "ɹˈɛd", "VBN": "ɹˈɛd", "ADJ": "ɹˈɛd"},
    "book": "bˈʊk", "it": "ˈɪt", "one": "wˈʌn", "two": "tˈu", "three": "θɹˈi",
    "four": "fˈɔɹ", "five": "fˈIv", "six": "sˈɪks", "seven": "sˈɛvən", "eight": "ˈAt",
    "nine": "nˈIn", "ten": "tˈɛn", "twenty": "twˈɛnti", "hundred": "hˈʌndɹɪd",
    "thousand": "θˈWzənd", "nineteen": "nˌIntˈin", "seventy": "sˈɛvənti",
    "first": "fˈɜɹst", "second": "sˈɛkənd", "third": "θˈɜɹd", "point": "pˈYnt",
    "percent": "pəɹsˈɛnt", "dollar": "dˈɑləɹ", "dollars": "dˈɑləɹz", "cent": "sˈɛnt",
    "cents": "sˈɛnts", "and": "ænd", "minus": "mˈInəs", "to": "tu", "am": "ˈæm",
    "used": {"DEFAULT": "jˈuzd", "VBD": "jˈust"}, "O": "ˈO", "zero": "zˈɪɹO",
    "fifty": "fˈɪfti", "pounds": "pˈWndz", "pound": "pˈWnd", "pence": "pˈɛns",
    "twelve": "twˈɛlv", "twenty-first": "twˌɛntifˈɜɹst",
}


def simple_tagger(text: str):
    """Whitespace tokens; tags by a tiny table, the way the real one would
    tag these words in these sentences."""
    tags = {
        "the": "DT", "a": "DT", "cat": "NN", "sat": "VBD", "on": "IN", "mat": "NN",
        "in": "IN", "read": "VBD", "book": "NN", "it": "PRP", "$": "$", "I": "PRP",
    }
    def tag_of(word: str) -> str:
        return tags.get(word, "CD" if word[0].isdigit() or word[0] == "-" else "NN")

    tokens = []
    for found in re.finditer(r"\S+", text):
        word = found.group()
        end = found.end()
        whitespace = " " if end < len(text) and text[end] == " " else ""
        mark = ""
        if word[-1] in ".,!?" and len(word) > 1:
            word, mark = word[:-1], word[-1]
        if word.startswith("$") and len(word) > 1:
            tokens.append(("$", "$", ""))
            word = word[1:]
        tokens.append((word, tag_of(word), "" if mark else whitespace))
        if mark:
            tokens.append((mark, ".", whitespace))
    return tokens


class G2PTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        (root / "gold.json").write_text(json.dumps(GOLD), encoding="utf-8")
        (root / "silver.json").write_text("{}", encoding="utf-8")
        cls.lexicon = Lexicon(root / "gold.json", root / "silver.json")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def g2p(self, fallback=None) -> G2P:
        return G2P(simple_tagger, self.lexicon, fallback=fallback, unk="")

    def test_a_sentence_reads_from_the_lexicon_with_the_tag_deciding(self) -> None:
        phonemes, _ = self.g2p()("The cat sat on the mat.")

        self.assertEqual(phonemes, "ðə kˈæt sˈæt ˈɑn ðə mˈæt.")

    def test_the_article_is_reduced_and_the_past_tense_is_read_as_red(self) -> None:
        phonemes, _ = self.g2p()("I read a book.")

        # "read" tagged VBD picks the past reading; "a" as DT is the schwa.
        self.assertEqual(phonemes, "ˌI ɹˈɛd ɐ bˈʊk.")

    def test_digits_never_reach_the_model(self) -> None:
        cases = {
            "It sat on 3 mats in 1975.": "nˌIntˈin sˈɛvənti fˈIv",
            "The 21st cat.": "twˈɛnti fˈɜɹst",
            "It cost $2.50.": "tˈu dˈɑləɹz ænd fˈɪfti sˈɛnts",
            "Read 3.5 books.": "θɹˈi pYnt fˈIv",
            "It is -4.": "mˈInəs fˈɔɹ",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                phonemes, _ = self.g2p()(text)
                self.assertNotRegex(phonemes, r"\d")
                self.assertIn(expected, phonemes)

    def test_an_unknown_word_goes_to_the_fallback_not_the_floor(self) -> None:
        asked: list[str] = []

        def fallback(token: MToken):
            asked.append(token.text)
            return "kˈOʃi", 1

        phonemes, _ = self.g2p(fallback)("The Koshi sat.")

        self.assertEqual(asked, ["Koshi"])
        self.assertEqual(phonemes, "ðə kˈOʃi sˈæt.")

    def test_without_a_fallback_an_unknown_word_is_left_out_not_marked(self) -> None:
        phonemes, _ = self.g2p()("The Koshi sat.")

        self.assertEqual(phonemes, "ðə  sˈæt.")

    def test_taps_and_glottal_stops_use_the_model_alphabet(self) -> None:
        # The lexicon writes ɾ and ʔ; the model was trained on T and t.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "gold.json").write_text(json.dumps({"butter": "bˈʌɾəɹ"}), encoding="utf-8")
            (root / "silver.json").write_text("{}", encoding="utf-8")
            g2p = G2P(simple_tagger, Lexicon(root / "gold.json", root / "silver.json"))

        phonemes, _ = g2p("butter")

        self.assertEqual(phonemes, "bˈʌTəɹ")

    def test_vietnamese_handed_to_the_english_reader_is_spoken_not_refused(self) -> None:
        # The owner's decision (15/09): a voice reads whatever it is handed,
        # and the shell suggests rather than the engine refusing. So the
        # English pipeline must SURVIVE a Vietnamese sentence - every word
        # outside its lexicon, most letters outside the fallback's alphabet -
        # and answer in the model's own alphabet, not raise from inside a
        # reading. What it sounds like is the reader's choice to make.
        from vieneu_reader.speech.english.fallback import Fallback
        from vieneu_reader.speech.english.g2p import US_VOCAB

        phonemes, _ = self.g2p(Fallback())("Xin chào các bạn, hẹn gặp lại ở Đà Nẵng năm 2026.")

        self.assertNotRegex(phonemes, r"\d")
        self.assertTrue(all(char in US_VOCAB or char in " ,." for char in phonemes), phonemes)
        # Something is left to say: the numbers alone guarantee that.
        self.assertIn("twˈɛnti", phonemes)

    def test_empty_text_is_empty_phonemes(self) -> None:
        self.assertEqual(self.g2p()("")[0], "")
        self.assertEqual(self.g2p()("   ")[0], "")

    def test_the_subword_splitter_separates_case_runs_and_digits(self) -> None:
        self.assertEqual(subtokenize("iPhone"), ["i", "Phone"])
        self.assertEqual(subtokenize("CD-ROM"), ["CD", "-", "ROM"])
        self.assertEqual(subtokenize("2.0-looking"), ["2.0", "-", "looking"])
        self.assertEqual(subtokenize("'tis"), ["'", "tis"])
        # A Vietnamese name keeps its letters together: the classes are built
        # from the Unicode tables, not typed as A-Z.
        self.assertEqual(subtokenize("Nguyễn"), ["Nguyễn"])
        self.assertEqual(subtokenize("Émile"), ["Émile"])


class NumberWordsTests(unittest.TestCase):
    def test_cardinals(self) -> None:
        self.assertEqual(numbers.cardinal(0), "zero")
        self.assertEqual(numbers.cardinal(21), "twenty-one")
        self.assertEqual(numbers.cardinal(105), "one hundred five")
        self.assertEqual(numbers.cardinal(1975), "one thousand nine hundred seventy-five")
        self.assertEqual(numbers.cardinal(1_200_000_000), "one billion two hundred million")
        self.assertEqual(numbers.cardinal(-7), "minus seven")

    def test_ordinals(self) -> None:
        self.assertEqual(numbers.ordinal(1), "first")
        self.assertEqual(numbers.ordinal(12), "twelfth")
        self.assertEqual(numbers.ordinal(20), "twentieth")
        self.assertEqual(numbers.ordinal(22), "twenty-second")
        self.assertEqual(numbers.ordinal(100), "one hundredth")
        self.assertEqual(numbers.ordinal(1003), "one thousand third")

    def test_years(self) -> None:
        self.assertEqual(numbers.year(1975), "nineteen seventy-five")
        self.assertEqual(numbers.year(1905), "nineteen oh five")
        self.assertEqual(numbers.year(1900), "nineteen hundred")
        self.assertEqual(numbers.year(2000), "two thousand")
        self.assertEqual(numbers.year(2005), "two thousand five")
        self.assertEqual(numbers.year(2020), "twenty twenty")
        self.assertEqual(numbers.year(1066), "ten sixty-six")

    def test_decimals(self) -> None:
        self.assertEqual(numbers.decimal("3.14"), "three point one four")
        self.assertEqual(numbers.decimal("2.0"), "two")
        self.assertEqual(numbers.decimal("3.50"), "three point five")
        self.assertEqual(numbers.decimal(".5"), "point five")
