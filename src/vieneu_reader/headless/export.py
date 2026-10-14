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
import struct
import wave
from dataclasses import dataclass, field

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


def integrated_loudness(samples: np.ndarray, sample_rate: int) -> float:
    """Gated integrated loudness of mono audio, in LUFS (-inf for silence).

    400 ms blocks with 75 % overlap, an absolute gate at -70 LUFS and a
    relative gate 10 LU under the mean of what passed it (BS.1770-4). Each
    block's K-weighted energy is taken in the frequency domain (Parseval), so
    a long file costs a few FFTs per second rather than a Python loop per
    sample.
    """

    block = int(0.4 * sample_rate)
    hop = block // 4
    samples = np.asarray(samples, dtype=np.float64).reshape(-1)
    if samples.size < block:
        samples = np.pad(samples, (0, block - samples.size))
    weight = _k_weight_power(block, sample_rate)
    starts = range(0, samples.size - block + 1, hop)
    energies = []
    for start in starts:
        spectrum = np.fft.rfft(samples[start:start + block])
        power = np.abs(spectrum) ** 2 * weight
        # One-sided spectrum back to the mean square of the block: the bins
        # other than DC (and Nyquist, for an even size) stand for two.
        power[1:-1 if block % 2 == 0 else None] *= 2
        energies.append(power.sum() / (block * block))
    energies = np.asarray(energies)
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
# has sharp peaks - a voice model's sit some 15 dB over its loudness - so a
# single gain stops near -17 LUFS (measured on VieNeu, 14/10). A few dB off
# the loudest syllables is inaudible; more starts to flatten the voice, and
# then the file is left quieter rather than squashed.
MAX_LIMIT_DB = 6.0
_LIMIT_BLOCK_S = 0.005
_LIMIT_RELEASE_BLOCKS = 12


def _limited(samples: np.ndarray, sample_rate: int, ceiling: float) -> np.ndarray:
    """Peaks over `ceiling` pulled down by a smooth gain, block by block.

    5 ms blocks: each gets the gain its own peak needs; the gain then holds
    for the next 60 ms (release) and starts one block early (look-ahead),
    and moves linearly between block centres, so nothing clicks. A last hard
    clip at the ceiling catches what interpolation lets through - a few
    samples at most.
    """

    block = max(1, int(_LIMIT_BLOCK_S * sample_rate))
    count = -(-samples.size // block)
    padded = np.pad(np.abs(samples), (0, count * block - samples.size))
    peaks = padded.reshape(count, block).max(axis=1)
    need = np.minimum(1.0, ceiling / np.maximum(peaks, 1e-12))
    window = _LIMIT_RELEASE_BLOCKS + 2
    extended = np.pad(need, (1, window), constant_values=1.0)
    held = np.lib.stride_tricks.sliding_window_view(extended, window).min(axis=1)[:count]
    centres = (np.arange(count) + 0.5) * block
    gain = np.interp(np.arange(samples.size), centres, held)
    return np.clip(samples * gain, -ceiling, ceiling).astype(np.float32)


def normalised(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, float]:
    """The audio at TARGET_LUFS with its peaks under PEAK_CEILING_DBFS.

    One gain lifts the whole file; where that would push a peak over the
    ceiling, a limiter takes the peak down (`_limited`), never by more than
    MAX_LIMIT_DB. Returns the new samples and the loudness they measure.
    """

    measured = integrated_loudness(samples, sample_rate)
    if not math.isfinite(measured):
        return samples, measured
    ceiling = 10 ** (PEAK_CEILING_DBFS / 20)
    peak = float(np.max(np.abs(samples)))
    # The gain the target asks for, but no more than the limiter may absorb.
    gain_db = min(TARGET_LUFS - measured,
                  PEAK_CEILING_DBFS + MAX_LIMIT_DB - 20 * math.log10(peak))
    out = samples
    for _ in range(3):
        lifted = (samples * 10 ** (gain_db / 20)).astype(np.float32)
        out = _limited(lifted, sample_rate, ceiling)
        now = integrated_loudness(out, sample_rate)
        # Limiting took a little loudness away; give it back, within bounds.
        short = TARGET_LUFS - now
        if abs(short) < 0.1 or 20 * math.log10(peak) + gain_db + short > PEAK_CEILING_DBFS + MAX_LIMIT_DB:
            break
        gain_db += short
    return out, integrated_loudness(out, sample_rate)


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


def write_wav(path: str, samples: np.ndarray, sample_rate: int, tags: dict[str, str]) -> None:
    """16-bit mono PCM with the INFO chunk after the audio."""

    pcm = (np.clip(samples, -1.0, 1.0) * 32767).round().astype("<i2").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm)
    riff = bytearray(buffer.getvalue())
    if len(riff) % 2:
        riff += b"\0"
    riff += _info_chunk(tags)
    # The RIFF size counts everything after its own eight bytes.
    riff[4:8] = struct.pack("<I", len(riff) - 8)
    with open(path, "wb") as handle:
        handle.write(bytes(riff))


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


@dataclass
class ExportSink:
    """Where `_speak` puts a reading meant for a file.

    `begin` and `end` bracket each sentence the voice says, in samples of
    the output (after the stretcher), so a cue covers exactly the voice and
    not the rest that follows it.
    """

    sample_rate: int
    total: int = 0
    done: int = 0
    _chunks: list[np.ndarray] = field(default_factory=list)
    _samples: int = 0
    _open: tuple[int, str] | None = None
    cues: list[Cue] = field(default_factory=list)

    def add(self, pcm: bytes) -> None:
        samples = np.frombuffer(pcm, dtype=np.float32)
        self._chunks.append(samples)
        self._samples += samples.size

    def begin(self, text: str) -> None:
        self._open = (self._samples, text)

    def end(self) -> None:
        if self._open is None:
            return
        start, text = self._open
        self._open = None
        if self._samples > start and text.strip():
            self.cues.append(Cue(start, self._samples, text.strip()))

    def audio(self) -> np.ndarray:
        if not self._chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._chunks)


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
