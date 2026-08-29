"""Change how fast speech plays without changing its pitch.

Playing 48 kHz samples out at a higher sample rate is faster, but it raises the
voice with it: at 1.25x a reader hears roughly a minor third of extra pitch.
This stretches time instead, by overlap-adding waveform segments at the spacing
the new speed needs and picking each segment where it continues the last one
most smoothly (WSOLA).

It is fed a stream, so it holds the overlap across chunk boundaries: a stretcher
that restarted at every chunk would put a click at every seam.
"""

from __future__ import annotations

import numpy as np


SAMPLE_RATE = 48_000

# About 43 ms per segment at 48 kHz, hopped at half a segment, which is where a
# Hann window sums back to a flat one. The search either way is ~5 ms, enough to
# find a matching pitch period for a voice down to about 190 Hz.
_FRAME = 2048
_HOP_OUT = _FRAME // 2
_SEARCH = 256
_SEARCH_STEP = 4

# Below this the overlap-add is reconstructing from one tapering window
# only, which is the stream's first and last few milliseconds.
_WEIGHT_FLOOR = 0.1

MINIMUM_RATE = 0.5
MAXIMUM_RATE = 2.0


class TimeStretcher:
    """Stream in samples at one speed, stream them out at another."""

    def __init__(self, rate: float = 1.0):
        self._window = np.hanning(_FRAME).astype(np.float64)
        self.reset(rate)

    @property
    def rate(self) -> float:
        return self._rate

    def reset(self, rate: float = 1.0) -> None:
        self.set_rate(rate)
        self._input = np.zeros(0, dtype=np.float64)
        self._read = 0
        self._output = np.zeros(0, dtype=np.float64)
        self._weight = np.zeros(0, dtype=np.float64)
        self._write = 0
        self._emitted = 0

    def set_rate(self, rate: float) -> None:
        if not MINIMUM_RATE <= rate <= MAXIMUM_RATE:
            raise ValueError("playback rate must be between 0.5 and 2.0")
        # Taking effect on the next segment is what lets the speed change
        # mid-sentence without restarting the audio device.
        self._rate = float(rate)

    def feed(self, samples: np.ndarray) -> np.ndarray:
        """Take more input; return whatever output is finished."""

        block = np.asarray(samples, dtype=np.float64).reshape(-1)
        if self._rate == 1.0 and self._input.size == 0 and self._output.size == 0:
            # Nothing to do at normal speed, and nothing half-processed to
            # disturb: hand the samples straight back.
            return block
        self._input = np.concatenate((self._input, block))
        self._grind()
        return self._take()

    def drain(self) -> np.ndarray:
        """Finish the tail once the stream has ended."""

        if self._output.size == 0:
            tail = self._take()
            self._input = self._input[len(self._input) :]
            return tail
        finished = self._normalised(len(self._output))[self._emitted :]
        self.reset(self._rate)
        return finished

    def _grind(self) -> None:
        hop_in = max(1, int(round(_HOP_OUT * self._rate)))
        while self._read + _SEARCH + _FRAME <= len(self._input):
            start = self._read + self._best_shift()
            segment = self._input[start : start + _FRAME]
            if len(segment) < _FRAME:
                break
            self._place(segment)
            self._read += hop_in
        self._trim_input()

    def _best_shift(self) -> int:
        """Where near the read head does the wave continue what was written?"""

        half = _FRAME // 2
        if self._write == 0 or self._write + half > len(self._output):
            return 0
        target = self._output[self._write : self._write + half]
        target_energy = float(np.dot(target, target))
        if target_energy <= 0.0:
            return 0
        low = max(-_SEARCH, -self._read)
        best_shift, best_score = 0, -np.inf
        for shift in range(low, _SEARCH + 1, _SEARCH_STEP):
            start = self._read + shift
            candidate = self._input[start : start + half]
            if len(candidate) < half:
                break
            energy = float(np.dot(candidate, candidate))
            if energy <= 0.0:
                continue
            # Normalised, so a loud stretch of speech cannot win on volume
            # alone when a quieter one lines up better.
            score = float(np.dot(candidate, target)) / np.sqrt(energy)
            if score > best_score:
                best_score, best_shift = score, shift
        return best_shift

    def _place(self, segment: np.ndarray) -> None:
        end = self._write + _FRAME
        if end > len(self._output):
            growth = end - len(self._output)
            self._output = np.concatenate((self._output, np.zeros(growth)))
            self._weight = np.concatenate((self._weight, np.zeros(growth)))
        self._output[self._write : end] += segment * self._window
        self._weight[self._write : end] += self._window
        self._write += _HOP_OUT

    def _normalised(self, upto: int) -> np.ndarray:
        # At the two ends of a stream only one window covers the samples, and
        # its taper runs to zero. Dividing by a vanishing weight turns that
        # taper into a step - one click, on the last sample. Holding the
        # divisor at a floor lets the ends fade instead.
        weight = self._weight[:upto]
        return self._output[:upto] / np.maximum(weight, _WEIGHT_FLOOR)

    def _take(self) -> np.ndarray:
        # Everything before the next segment's start is final: no later segment
        # reaches back that far.
        if self._write <= self._emitted:
            return np.zeros(0, dtype=np.float64)
        ready = self._normalised(self._write)[self._emitted :]
        self._emitted = self._write
        return ready

    def _trim_input(self) -> None:
        # Keep only what the search can still reach behind the read head.
        keep_from = max(0, self._read - _SEARCH)
        if keep_from > 0:
            self._input = self._input[keep_from:]
            self._read -= keep_from
