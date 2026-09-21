"""How long the rest of a reading takes to hear (HIG 3.24)."""

from __future__ import annotations

import unittest

from vieneu_reader.playback.pace import (
    DEFAULT_CHARS_PER_SECOND,
    SETTLED_SECONDS,
    Pace,
)


class PaceTests(unittest.TestCase):
    def test_the_default_is_the_measured_pace_of_each_language(self) -> None:
        # 1 450 Vietnamese characters at 14.5 a second is 100 s; English
        # reads a touch faster (probe 21/09: 14.66/14.45 and 16.33/16.00).
        self.assertEqual(Pace().seconds_for(1450, language="vi"), 100)
        self.assertEqual(Pace().seconds_for(1600, language="en"), 100)
        self.assertEqual(DEFAULT_CHARS_PER_SECOND["vi"], 14.5)

    def test_an_unknown_language_falls_back_to_vietnamese(self) -> None:
        self.assertEqual(Pace().seconds_for(1450, language="fr"), 100)

    def test_the_rate_shortens_the_forecast(self) -> None:
        self.assertEqual(Pace().seconds_for(1450, rate=2.0, language="vi"), 50)
        self.assertEqual(Pace().seconds_for(1450, rate=0.5, language="vi"), 200)

    def test_a_measurement_outranks_the_default_once_settled(self) -> None:
        pace = Pace()
        # Ten characters a second, heard for exactly the settling time.
        pace.add(chars=int(10 * SETTLED_SECONDS), seconds=SETTLED_SECONDS)
        self.assertTrue(pace.settled)
        self.assertEqual(pace.seconds_for(300), 30)

    def test_too_little_heard_still_uses_the_default(self) -> None:
        pace = Pace()
        pace.add(chars=5, seconds=SETTLED_SECONDS / 2)
        self.assertFalse(pace.settled)
        self.assertEqual(pace.seconds_for(1450, language="vi"), 100)

    def test_a_measurement_is_kept_at_rate_one(self) -> None:
        # Heard at 2×: 100 characters took 5 s, which is 10 s at 1×.
        pace = Pace()
        pace.add(chars=100, seconds=5.0, rate=2.0)
        self.assertTrue(pace.settled)
        self.assertEqual(pace.seconds_for(100, rate=1.0), 10)
        self.assertEqual(pace.seconds_for(100, rate=2.0), 5)

    def test_nothing_and_nonsense_count_for_nothing(self) -> None:
        pace = Pace()
        pace.add(chars=0, seconds=3.0)
        pace.add(chars=10, seconds=0.0)
        self.assertEqual((pace.chars, pace.seconds), (0, 0.0))
        self.assertEqual(pace.seconds_for(0), 0)
        self.assertEqual(Pace().seconds_for(145, rate=0.0, language="vi"), 10)


if __name__ == "__main__":
    unittest.main()
