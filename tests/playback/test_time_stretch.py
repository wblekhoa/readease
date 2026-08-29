"""Reading faster must not raise the voice.

The app used to change speed by declaring a higher sample rate on the audio
device, which plays the same samples sooner and lifts the pitch with them: at
1.25x, about a minor third. These pin the replacement.
"""

import math
import unittest

import numpy as np

from vieneu_reader.playback.time_stretch import (
    SAMPLE_RATE,
    TimeStretcher,
)


def tone(hertz: float, seconds: float) -> np.ndarray:
    t = np.arange(int(SAMPLE_RATE * seconds)) / SAMPLE_RATE
    # A few harmonics, so this behaves like a voiced sound rather than a pure
    # sine that any resampler would keep intact by accident.
    return (
        0.5 * np.sin(2 * math.pi * hertz * t)
        + 0.25 * np.sin(4 * math.pi * hertz * t)
        + 0.12 * np.sin(6 * math.pi * hertz * t)
    )


def dominant_hertz(samples: np.ndarray) -> float:
    window = samples[: 1 << int(math.log2(len(samples)))] * np.hanning(
        1 << int(math.log2(len(samples)))
    )
    spectrum = np.abs(np.fft.rfft(window))
    return float(np.fft.rfftfreq(len(window), 1 / SAMPLE_RATE)[np.argmax(spectrum)])


def stretch_all(source: np.ndarray, rate: float, chunk: int = 4800) -> np.ndarray:
    stretcher = TimeStretcher(rate)
    pieces = [stretcher.feed(source[index : index + chunk])
              for index in range(0, len(source), chunk)]
    pieces.append(stretcher.drain())
    return np.concatenate([piece for piece in pieces if len(piece)])


class TimeStretcherTests(unittest.TestCase):
    def test_normal_speed_hands_the_samples_straight_back(self):
        source = tone(120, 0.5)

        self.assertTrue(np.array_equal(TimeStretcher(1.0).feed(source), source))

    def test_the_pitch_survives_every_speed_the_player_offers(self):
        source = tone(120, 2.0)
        original = dominant_hertz(source)

        for rate in (0.5, 0.75, 1.0, 1.15, 1.2, 1.25, 1.5, 2.0):
            with self.subTest(rate=rate):
                shifted = dominant_hertz(stretch_all(source, rate))
                semitones = 12 * math.log2(shifted / original)
                # The old mechanism moved this by 12*log2(rate): +3.9 at 1.25x,
                # +7.0 at 1.5x, -12 at 0.5x.
                self.assertLess(abs(semitones), 0.5, f"{rate}x moved the pitch")

    def test_the_duration_is_what_the_speed_asks_for(self):
        source = tone(120, 2.0)

        for rate in (0.5, 0.75, 1.15, 1.2, 1.25, 1.5, 2.0):
            with self.subTest(rate=rate):
                produced = len(stretch_all(source, rate))
                self.assertAlmostEqual(produced / (len(source) / rate), 1.0, delta=0.02)

    def test_arriving_in_pieces_gives_the_same_audio_as_arriving_at_once(self):
        """Anything else would put a seam wherever a chunk boundary fell."""
        source = tone(120, 1.5)

        whole = stretch_all(source, 1.25, chunk=len(source))
        for chunk in (256, 1024, 4801):
            with self.subTest(chunk=chunk):
                piecemeal = stretch_all(source, 1.25, chunk=chunk)
                self.assertEqual(len(whole), len(piecemeal))
                self.assertTrue(np.array_equal(whole, piecemeal))

    def test_the_output_never_jumps_further_than_the_source_does(self):
        """A click is a discontinuity - a step the waveform itself never takes.

        The first version of this left exactly one, on the very last sample,
        where the overlap-add window tapers to nothing and dividing by it
        turned the taper into a step.
        """
        source = tone(120, 1.5)
        natural = float(np.max(np.abs(np.diff(source))))

        for rate in (0.75, 1.15, 1.2, 1.25, 1.5):
            for chunk in (1024, 4800):
                with self.subTest(rate=rate, chunk=chunk):
                    produced = stretch_all(source, rate, chunk=chunk)
                    biggest = float(np.max(np.abs(np.diff(produced))))
                    self.assertLess(biggest, natural * 1.1)

    def test_a_speed_the_player_cannot_reach_is_refused(self):
        for rate in (0.4, 2.1, 0.0, -1.0):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    TimeStretcher(rate)

    def test_the_speed_can_change_part_way_through(self):
        source = tone(120, 2.0)
        stretcher = TimeStretcher(1.0)

        first = stretcher.feed(source[: len(source) // 2])
        stretcher.set_rate(2.0)
        second = np.concatenate(
            [stretcher.feed(source[len(source) // 2 :]), stretcher.drain()]
        )

        # First half at normal speed, second half at double: about three
        # quarters of the original length overall.
        total = len(first) + len(second)
        self.assertAlmostEqual(total / len(source), 0.75, delta=0.05)

    def test_silence_in_gives_silence_out(self):
        produced = stretch_all(np.zeros(SAMPLE_RATE), 1.25)

        self.assertTrue(np.all(np.abs(produced) < 1e-9))


if __name__ == "__main__":
    unittest.main()
