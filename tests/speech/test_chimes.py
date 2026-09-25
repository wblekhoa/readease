"""The sounds that open a chapter and a section (HIG 5.1, 25/09).

"Chương dài, mục ngắn": a chapter opens with the family's long sound and a
first-level section with a short, soft one - cut from the family's own
chime at read time, not a file of its own.
"""

import unittest

import numpy as np

from vieneu_reader.speech.chimes import (
    CHIME_NAMES,
    SAMPLE_RATE,
    load_chime,
    load_part_chime,
    load_section_chime,
)


class SectionSoundTests(unittest.TestCase):
    def test_a_section_sound_is_the_chime_s_first_moment_softer(self) -> None:
        for name in CHIME_NAMES:
            with self.subTest(name=name):
                chime, section = load_chime(name), load_section_chime(name)
                # 0.45 s: marimba's one strike, piano's first chord (its
                # second comes at 0.45 s), harp's two plucks.
                self.assertEqual(section.size, int(SAMPLE_RATE * 0.45))
                # The chime's own shape, one gain for all of it, until the
                # fade begins - and a peak at -20 dBFS in every family (a fixed
                # -6 dB left piano's soft first chord at -26).
                steady = int(SAMPLE_RATE * 0.37)
                gain = float(np.abs(section).max() / np.abs(chime[:section.size]).max())
                np.testing.assert_allclose(section[:steady], chime[:steady] * gain, atol=1e-6)
                self.assertAlmostEqual(20 * np.log10(float(np.abs(section).max())), -20.0, places=2)
                # Faded to nothing, so the cut is not a click.
                self.assertLess(abs(float(section[-1])), 1e-4)

    def test_a_section_sound_is_shorter_than_a_chapter_s(self) -> None:
        for name in CHIME_NAMES:
            with self.subTest(name=name):
                self.assertLess(load_section_chime(name).size, load_part_chime(name).size)

    def test_an_unknown_family_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            load_section_chime("gong")


if __name__ == "__main__":
    unittest.main()
