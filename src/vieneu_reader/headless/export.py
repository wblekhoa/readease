"""A reading written to a file instead of the speakers: audio plus subtitles.

The voice, the rests and the stretcher are the reading's own - `_speak` runs
exactly as it does for the speakers and hands every frame to an
`ExportSink` instead of the pipe. What this module adds is only what a file
needs and a speaker does not:

- the loudness a video editor expects (`integrated_loudness`, ITU-R BS.1770
  K-weighted and gated, numpy only - no new dependency for one meter);
- a WAV that says, in its own metadata, that the speech in it was made by
  a voice model (`write_wav`). Both Vietnam's AI law (in force 01/03/2026)
  and Article 50(2) of the EU AI Act ask the provider of a tool that makes
  synthetic audio for a machine-readable mark on its output. A LIST/INFO
  chunk is that mark in the plainest form every editor keeps: it is not
  heard, and it stops nobody from using the file however they choose;
- subtitles timed by the sentences the voice actually said (`write_srt`).
"""

from __future__ import annotations

import io
import math
import os
import struct
import tempfile
import wave
from dataclasses import dataclass

import numpy as np

# YouTube plays everything back near -14 LUFS; a file delivered there is the
# one that needs no further gain in the editor. Peaks stay a decibel under
# full scale so a lossy re-encode does not clip them.
TARGET_LUFS = -14.0
PEAK_CEILING_DBFS = -1.0

# A cue longer than this is split, by characters, into pieces shown one after
# another - two short lines on a phone, not a paragraph.
CUE_MAX_CHARS = 84

# BS.1770-4 K-weighting at 48 kHz: the "pre-filter" shelf, then the RLB
# high-pass. Coefficients from the recommendation's own table.
_SHELF = ((1.53512485958697, -2.69169618940638, 1.19839281085285),
          (1.0, -1.69065929318241, 0.73248077421585))
_HIGHPASS = ((1.0, -2.0, 1.0),
             (1.0, -1.99004745483398, 0.99007225036621))
_K_RATE = 48000


def _k_weight_power(size: int, sample_rate: int) -> np.ndarray:
    """|H(f)|^2 of the K-weighting filter at the bins of an rfft of `size`."""

    if sample_rate != _K_RATE:
        raise ValueError(f"K-weighting is defined here for {_K_RATE} Hz, not {sample_rate}")
    omega = 2 * np.pi * np.fft.rfftfreq(size, d=1.0 / sample_rate) / sample_rate
    z = np.exp(-1j * omega)
    power = np.ones_like(omega)
    for b, a in (_SHELF, _HIGHPASS):
        numerator = b[0] + b[1] * z + b[2] * z * z
        denominator = a[0] + a[1] * z + a[2] * z * z
        power = power * np.abs(numerator / denominator) ** 2
    return power


# Blocks measured per FFT batch, and samples per write: a few MB of working
# memory whatever the length of the file. A paste may be 100 000 characters -
# an hour and more of audio - and the reading engine shares an 8 GB Mac.
_BATCH_BLOCKS = 32
_WRITE_SAMPLES = 1 << 18


def _block_energies(samples, sample_rate: int, transform=None, checkpoint=lambda: None) -> np.ndarray:
    """Mean-square K-weighted energy of each 400 ms block, 75 % overlap.

    Taken in the frequency domain (Parseval), a batch of blocks per FFT, so
    a long file costs a few FFTs per second and never more than one batch
    in memory. `transform(segment, start)` changes the samples on the way
    in - the gain a file will be written with, measured before it is.
    """

    block = int(0.4 * sample_rate)
    hop = block // 4
    total = len(samples)
    if total < block:
        samples = np.pad(np.asarray(samples, dtype=np.float64), (0, block - total))
        total = block
    weight = _k_weight_power(block, sample_rate)
    count = (total - block) // hop + 1
    energies = np.empty(count)
    for first in range(0, count, _BATCH_BLOCKS):
        checkpoint()
        last = min(count, first + _BATCH_BLOCKS)
        start, stop = first * hop, (last - 1) * hop + block
        segment = np.asarray(samples[start:stop], dtype=np.float64)
        if transform is not None:
            segment = transform(segment, start)
        frames = np.lib.stride_tricks.sliding_window_view(segment, block)[::hop]
        power = np.abs(np.fft.rfft(frames, axis=1)) ** 2 * weight
        # One-sided spectrum back to the mean square: every bin but DC and
        # Nyquist (the block is an even size) stands for two.
        power[:, 1:-1] *= 2
        energies[first:last] = power.sum(axis=1) / (block * block)
    return energies


def integrated_loudness(samples, sample_rate: int, transform=None, checkpoint=lambda: None) -> float:
    """Gated integrated loudness of mono audio, in LUFS (-inf for silence).

    ITU-R BS.1770-4: K-weighted 400 ms blocks, an absolute gate at -70 LUFS
    and a relative gate 10 LU under the mean of what passed it.
    """

    energies = _block_energies(samples, sample_rate, transform, checkpoint)
    loudness = -0.691 + 10 * np.log10(np.maximum(energies, 1e-20))
    passed = energies[loudness > -70.0]
    if passed.size == 0:
        return float("-inf")
    relative = -0.691 + 10 * math.log10(passed.mean()) - 10.0
    passed = energies[(loudness > -70.0) & (loudness > relative)]
    if passed.size == 0:
        return float("-inf")
    return float(-0.691 + 10 * math.log10(passed.mean()))


# The most a peak may be pulled down to let the rest reach the target. Speech
# has sharp peaks - VieNeu's sat 15.7 dB over its loudness (14/10) - so one
# gain alone stops near -17 LUFS. A few dB off the loudest syllables is not
# heard; more starts to flatten the voice, and then the file is left quieter
# rather than squashed.
MAX_LIMIT_DB = 6.0
_LIMIT_BLOCK_S = 0.005
# How long a reduction holds after the peak that asked for it (12 blocks,
# 60 ms) before the gain comes back. It starts one block early.
_LIMIT_RELEASE_BLOCKS = 12


def _block_peaks(samples, sample_rate: int, checkpoint=lambda: None) -> np.ndarray:
    block = max(1, int(_LIMIT_BLOCK_S * sample_rate))
    total = len(samples)
    count = -(-total // block)
    peaks = np.empty(count, dtype=np.float32)
    step = block * 4096
    for start in range(0, total, step):
        checkpoint()
        segment = np.abs(np.asarray(samples[start:start + step], dtype=np.float32))
        blocks = -(-segment.size // block)
        segment = np.pad(segment, (0, blocks * block - segment.size))
        peaks[start // block:start // block + blocks] = segment.reshape(blocks, block).max(axis=1)
    return peaks


def _held_gain(peaks: np.ndarray, ceiling: float) -> np.ndarray:
    """Each block's gain: the least any block from 60 ms before it to one
    after it needs to stay under the ceiling - one block of look-ahead, a
    60 ms hold before it lets go."""

    need = np.minimum(1.0, ceiling / np.maximum(peaks.astype(np.float64), 1e-12))
    window = _LIMIT_RELEASE_BLOCKS + 2
    extended = np.pad(need, (_LIMIT_RELEASE_BLOCKS, 1), constant_values=1.0)
    return np.lib.stride_tricks.sliding_window_view(extended, window).min(axis=1)[:need.size]


@dataclass(frozen=True)
class _Gain:
    """One lift for the whole file, then the limiter's gain moving linearly
    between 5 ms block centres, then a hard clip at the ceiling for the few
    samples interpolation lets through."""

    lift: float
    held: np.ndarray
    block: int
    ceiling: float

    def __call__(self, segment: np.ndarray, start: int) -> np.ndarray:
        # Only the nearby limiter blocks: allocating every block centre
        # again for every batch made long-book normalisation quadratic.
        first = max(0, start // self.block - 1)
        last = min(self.held.size, (start + segment.size) // self.block + 2)
        centres = (np.arange(first, last) + 0.5) * self.block
        gain = np.interp(np.arange(start, start + segment.size), centres, self.held[first:last])
        return np.clip(segment * (self.lift * gain), -self.ceiling, self.ceiling)


def _plan(samples, sample_rate: int, checkpoint=lambda: None) -> tuple[_Gain | None, float]:
    """The gain that puts the file at TARGET_LUFS with its peaks under
    PEAK_CEILING_DBFS, never limiting more than MAX_LIMIT_DB; and the
    loudness the file will then measure."""

    measured = integrated_loudness(samples, sample_rate, checkpoint=checkpoint)
    if not math.isfinite(measured):
        return None, measured
    ceiling = 10 ** (PEAK_CEILING_DBFS / 20)
    peaks = _block_peaks(samples, sample_rate, checkpoint)
    peak_db = 20 * math.log10(float(peaks.max()))
    most = PEAK_CEILING_DBFS + MAX_LIMIT_DB - peak_db
    gain_db = min(TARGET_LUFS - measured, most)
    block = max(1, int(_LIMIT_BLOCK_S * sample_rate))
    for attempt in range(4):
        lift = 10 ** (gain_db / 20)
        plan = _Gain(lift, _held_gain(peaks * lift, ceiling), block, ceiling)
        now = integrated_loudness(samples, sample_rate, plan, checkpoint)
        # Limiting took a little loudness away; give it back, within bounds.
        short = TARGET_LUFS - now
        if abs(short) < 0.1 or gain_db >= most or attempt == 3:
            return plan, now
        gain_db = min(gain_db + short, most)
    return plan, now


def normalised(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, float]:
    """The audio at TARGET_LUFS with its peaks under PEAK_CEILING_DBFS (in
    memory - `write_wav` does the same a batch at a time)."""

    plan, loudness = _plan(samples, sample_rate)
    if plan is None:
        return samples, loudness
    return plan(np.asarray(samples, dtype=np.float64), 0).astype(np.float32), loudness


def _info_chunk(tags: dict[str, str]) -> bytes:
    """A RIFF LIST/INFO chunk: four-letter ids, NUL-terminated, even-padded."""

    body = b"INFO"
    for key, value in tags.items():
        if len(key) != 4:
            raise ValueError(f"INFO ids are four letters: {key!r}")
        data = value.encode("utf-8") + b"\0"
        if len(data) % 2:
            data += b"\0"
        body += key.encode("ascii") + struct.pack("<I", len(data)) + data
    return b"LIST" + struct.pack("<I", len(body)) + body


def write_wav(path: str, samples, sample_rate: int, tags: dict[str, str], *, checkpoint=lambda: None) -> float:
    """16-bit mono PCM at the export loudness, the INFO chunk after the audio.

    Returns the loudness written (-inf for silence). The samples may be a
    memory map: they are read, gained and written a batch at a time.
    """

    plan, loudness = _plan(samples, sample_rate, checkpoint)
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for start in range(0, len(samples), _WRITE_SAMPLES):
            checkpoint()
            segment = np.asarray(samples[start:start + _WRITE_SAMPLES], dtype=np.float64)
            if plan is not None:
                segment = plan(segment, start)
            handle.writeframes((np.clip(segment, -1.0, 1.0) * 32767).round().astype("<i2").tobytes())
    with open(path, "r+b") as handle:
        handle.seek(0, io.SEEK_END)
        if handle.tell() % 2:
            handle.write(b"\0")
        handle.write(_info_chunk(tags))
        size = handle.tell()
        # The RIFF size counts everything after its own eight bytes.
        handle.seek(4)
        handle.write(struct.pack("<I", size - 8))
    return loudness


def read_wav_info(path: str) -> dict[str, str]:
    """The INFO tags of a WAV this module wrote - for tests and probes."""

    with open(path, "rb") as handle:
        data = handle.read()
    tags: dict[str, str] = {}
    position = 12
    while position + 8 <= len(data):
        kind = data[position:position + 4]
        size = struct.unpack("<I", data[position + 4:position + 8])[0]
        body = data[position + 8:position + 8 + size]
        if kind == b"LIST" and body[:4] == b"INFO":
            inner = 4
            while inner + 8 <= len(body):
                key = body[inner:inner + 4].decode("ascii")
                length = struct.unpack("<I", body[inner + 4:inner + 8])[0]
                tags[key] = body[inner + 8:inner + 8 + length].rstrip(b"\0").decode("utf-8")
                inner += 8 + length + (length % 2)
        position += 8 + size + (size % 2)
    return tags


@dataclass
class Cue:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Said:
    """One sentence as the voice said it, and how - enough to say it again."""

    spoken: str
    shown: str
    rate: float
    gain: float


class _Pieces:
    """The export's audio as an ordered list of pieces of one file: slices
    like an array, read with `pread`, never mapped (a mapping keeps every
    page it touched resident - an hour of audio measured twice touched a
    gigabyte, 14/10)."""

    def __init__(self, descriptor: int, pieces: list[tuple[int, int]]) -> None:
        self._descriptor = descriptor
        self._pieces = pieces
        lengths = np.fromiter((length for _, length in pieces), dtype=np.int64, count=len(pieces))
        self._starts = np.concatenate(([0], np.cumsum(lengths)))

    def __len__(self) -> int:
        return int(self._starts[-1])

    def __getitem__(self, where: slice) -> np.ndarray:
        start, stop, _ = where.indices(len(self))
        if stop <= start:
            return np.zeros(0, dtype=np.float32)
        first = int(np.searchsorted(self._starts, start, side="right")) - 1
        last = int(np.searchsorted(self._starts, stop, side="left")) - 1
        parts = []
        for index in range(first, last + 1):
            offset, length = self._pieces[index]
            begin = max(start, int(self._starts[index]))
            end = min(stop, int(self._starts[index]) + length)
            if end > begin:
                skip = begin - int(self._starts[index])
                data = os.pread(self._descriptor, (end - begin) * 4, (offset + skip) * 4)
                parts.append(np.frombuffer(data, dtype=np.float32))
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)


class ExportSink:
    """Where `_speak` puts a reading meant for a file - kept by SENTENCE.

    The audio goes to an anonymous temporary file, not memory: an hour of
    float32 is 700 MB. The file has no name from the start, so it is gone
    when the sink closes or the process dies.

    Every piece of audio is tagged with the sentence it belongs to (-1 for a
    rest or a chime), so one sentence can be said again (`replace`) without
    touching the others, and the subtitles are timed from where the pieces
    lie when the file is written - a longer new take moves every cue after
    it. A cue covers a run of sentences: one, when the written and the spoken
    split the same way, or a whole part when they do not.
    """

    def __init__(self, sample_rate: int, total: int = 0) -> None:
        self.sample_rate = sample_rate
        self.total = total
        self.done = 0
        self.said: list[Said] = []
        self._file = tempfile.TemporaryFile()
        self._end = 0
        self._pieces: list[list[int]] = []  # [offset, length, sentence]
        self._sentence = -1
        self._cues: list[tuple[int, int, str]] = []
        self._cue: tuple[int, str] | None = None
        # Chapter marks for an audiobook (RE-PLAY-020): the utterance a
        # chapter starts at -> its title, and, once reached, the sentence it
        # starts with - timed like a cue, so a retake moves it too.
        self.chapter_titles: dict[int, str] = {}
        self._marks: list[tuple[int, str]] = []

    # -- recording, as `_speak` goes ------------------------------------------
    def add(self, pcm: bytes) -> None:
        self._file.seek(0, io.SEEK_END)
        self._file.write(pcm)
        count = len(pcm) // 4
        self._pieces.append([self._end, count, self._sentence])
        self._end += count

    def at_utterance(self, position: int) -> None:
        """The reading reached utterance `position`: a chapter starts here?"""
        title = self.chapter_titles.get(position)
        if title is not None:
            self._marks.append((len(self.said), title))

    def open_sentence(self, said: Said) -> None:
        self.said.append(said)
        self._sentence = len(self.said) - 1

    def close_sentence(self) -> None:
        self._sentence = -1

    def begin(self, text: str) -> None:
        """A cue starts with the next sentence opened."""
        self._cue = (len(self.said), text)

    def end(self) -> None:
        if self._cue is None:
            return
        first, text = self._cue
        self._cue = None
        last = len(self.said) - 1
        if last >= first and text.strip():
            self._cues.append((first, last, text.strip()))

    # -- reading back ----------------------------------------------------------
    def audio(self) -> _Pieces:
        self._file.flush()
        return _Pieces(self._file.fileno(), [(offset, length) for offset, length, _ in self._pieces])

    @property
    def cues(self) -> list[Cue]:
        """Cues in samples of the audio as it now stands."""
        spans: dict[int, list[int]] = {}
        at = 0
        for _, length, sentence in self._pieces:
            if sentence >= 0 and length:
                span = spans.setdefault(sentence, [at, at + length])
                span[1] = at + length
            at += length
        cues = []
        for first, last, text in self._cues:
            if first in spans and last in spans:
                cues.append(Cue(spans[first][0], spans[last][1], text))
        return cues

    @property
    def marks(self) -> list[tuple[int, str]]:
        """(sample, title) for each chapter that got at least one sentence."""
        starts: dict[int, int] = {}
        at = 0
        for _, length, sentence in self._pieces:
            if sentence >= 0 and length and sentence not in starts:
                starts[sentence] = at
            at += length
        return [(starts[first], title) for first, title in self._marks if first in starts]

    def take(self, sentence: int) -> np.ndarray:
        """One sentence's audio, as it stands."""
        self._file.flush()
        parts = [
            np.frombuffer(os.pread(self._file.fileno(), length * 4, offset * 4), dtype=np.float32)
            for offset, length, tag in self._pieces if tag == sentence and length
        ]
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def replace(self, sentence: int, pcm: bytes) -> None:
        """A new take of one sentence, in the place of the old one."""
        where = [index for index, piece in enumerate(self._pieces) if piece[2] == sentence]
        if not where:
            raise IndexError(f"no sentence {sentence}")
        self._file.seek(0, io.SEEK_END)
        self._file.write(pcm)
        count = len(pcm) // 4
        new = [self._end, count, sentence]
        self._end += count
        self._pieces[where[0]:where[-1] + 1] = [new]

    def close(self) -> None:
        self._file.close()


def split_cue(cue: Cue, limit: int = CUE_MAX_CHARS) -> list[Cue]:
    """A long sentence as several cues, each a run of whole words, timed by
    its share of the characters."""

    words = cue.text.split()
    if len(cue.text) <= limit or len(words) < 2:
        return [cue]
    pieces: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > limit:
            pieces.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        pieces.append(" ".join(current))
    total = sum(len(piece) for piece in pieces)
    # Even pieces, not a full line and a stub: as many lines as the greedy
    # cut made, each aiming at the same share of the characters.
    if len(pieces) > 1:
        aim = len(cue.text) / len(pieces)
        balanced: list[str] = []
        current = []
        for word in words:
            current.append(word)
            if len(" ".join(current)) >= aim and len(balanced) < len(pieces) - 1:
                balanced.append(" ".join(current))
                current = []
        if current:
            balanced.append(" ".join(current))
        if all(len(piece) <= limit for piece in balanced):
            pieces = balanced
        total = sum(len(piece) for piece in pieces)
    span = cue.end - cue.start
    cues: list[Cue] = []
    at = cue.start
    for index, piece in enumerate(pieces):
        end = cue.end if index == len(pieces) - 1 else at + round(span * len(piece) / total)
        cues.append(Cue(at, end, piece))
        at = end
    return cues


def _timestamp(sample: int, sample_rate: int) -> str:
    milliseconds = round(sample * 1000 / sample_rate)
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def srt_text(cues: list[Cue], sample_rate: int) -> str:
    lines: list[str] = []
    numbered = [piece for cue in cues for piece in split_cue(cue)]
    for index, cue in enumerate(numbered, start=1):
        lines += [
            str(index),
            f"{_timestamp(cue.start, sample_rate)} --> {_timestamp(cue.end, sample_rate)}",
            cue.text,
            "",
        ]
    return "\n".join(lines)


def write_srt(path: str, cues: list[Cue], sample_rate: int) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(srt_text(cues, sample_rate))
