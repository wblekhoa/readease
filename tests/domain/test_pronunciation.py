"""The reader's own pronunciations (RE-VOICE dictionary)."""

import unittest

from vieneu_reader.domain.pronunciation import (
    MAX_SPOKEN,
    Pronunciations,
    entries_of,
    pronunciations_of,
)


def make(*pairs):
    return Pronunciations(entries_of([{"written": w, "spoken": s} for w, s in pairs]))


class PronunciationTests(unittest.TestCase):
    # RE-PLAY-015
    def test_whole_words_only_any_case(self):
        say = make(("AI", "ây ai"))
        self.assertEqual(say.apply("Dùng AI và ai cũng được."), "Dùng ây ai và ây ai cũng được.")
        # Never inside another word.
        self.assertEqual(say.apply("SAI rồi, AIDS khác."), "SAI rồi, AIDS khác.")

    # RE-PLAY-015
    def test_longest_written_form_wins(self):
        say = make(("Google", "gu gồ"), ("Google Docs", "gu gồ đốc"))
        self.assertEqual(say.apply("Mở Google Docs rồi Google."), "Mở gu gồ đốc rồi gu gồ.")

    # RE-PLAY-015
    def test_vietnamese_letters_count_as_word_letters(self):
        say = make(("Đà", "Đà Nẵng"))
        self.assertEqual(say.apply("Đàn và Đà."), "Đàn và Đà Nẵng.")

    # RE-PLAY-015
    def test_bad_rows_are_skipped_and_the_last_spelling_wins(self):
        entries = entries_of([
            {"written": "ReadEase", "spoken": "rít ít"},
            {"written": "", "spoken": "x"},
            {"written": "y", "spoken": "z" * (MAX_SPOKEN + 1)},
            "not a row",
            {"written": "readease", "spoken": "rít-ít"},
        ])
        self.assertEqual([(e.written, e.spoken) for e in entries], [("readease", "rít-ít")])
        self.assertEqual(entries_of("not json"), ())
        self.assertEqual(entries_of('[{"written": "a", "spoken": "b"}]')[0].spoken, "b")

    def test_nothing_set_changes_nothing(self):
        say = pronunciations_of({})
        self.assertFalse(say)
        self.assertEqual(say.apply("ReadEase"), "ReadEase")


if __name__ == "__main__":
    unittest.main()
