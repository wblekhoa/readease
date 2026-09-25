"""The short sounds that mark a chapter's start (owner, 16/09: "nhạc chờ
ngắn giữa các chương").

Three of them, chosen by ear from a batch generated with ElevenLabs'
sound-effects model, then downmixed to mono at the pipe's 48 kHz, trimmed
of silence and levelled to -14 dBFS so they sit under speech (which peaks
around -3 to -6) rather than over it. They are package data - about 730 KB
with the part sound - not something the engine synthesises, so the reader
hears the same sound every time and nothing is fetched.

A chime is played as a plain frame, the way the silence between paragraphs
is: not through the time-stretcher (a chime should not speed up with the
reading), not into the sentence cache, and never billed to a paid voice.

Since 25/09 ("Chương dài, mục ngắn") a chapter opens with the family's LONG
sound - the one parts had - and a first-level section with a short, soft
one cut from the family's own chime at read time (`load_section_chime`).
"""

from __future__ import annotations

import wave
from importlib import resources

import numpy as np

CHIME_NAMES: tuple[str, ...] = ("marimba", "harp", "piano")
DEFAULT_CHIME = "marimba"
# The family's LONG sound (HIG 5.1, owner 25/09): made for parts, and since
# "Chương dài, mục ngắn" the sound that opens a chapter too. Only the
# families named here have one; the others open parts and chapters with
# their chime, which is already two seconds long.
PART_SOUNDS: dict[str, str] = {"marimba": "part-marimba"}
# The sound that opens a first-level SECTION (1.1, 1.2 ...): short and soft,
# because a document can hold hundreds of them (owner, 25/09). Cut from the
# family's own chime rather than a file of its own - the same instrument as
# the chapter's sound, nothing to download, no credits. 0.45 s holds
# marimba's one strike, piano's first chord (its second comes at 0.45 s)
# and harp's two plucks; the last 80 ms fade to nothing so the cut is not a
# click; 6 dB under the chime. Provisional until the owner hears it.
SECTION_SECONDS = 0.45
SECTION_FADE_SECONDS = 0.08
SECTION_GAIN_DB = -6.0
SAMPLE_RATE = 48000

_loaded: dict[str, np.ndarray] = {}


def chime_choice(value: object) -> str | None:
    """The chime a stored setting names, `None` for off - and for anything
    the setting could not mean, the default rather than silence: a setting
    that has never been written is not a request for no sound."""

    if value is None or value == "":
        return DEFAULT_CHIME
    name = str(value).strip().lower()
    if name == "off":
        return None
    return name if name in CHIME_NAMES else DEFAULT_CHIME


def _load(stem: str) -> np.ndarray:
    cached = _loaded.get(stem)
    if cached is not None:
        return cached
    source = resources.files("vieneu_reader.speech") / "chimes" / f"{stem}.wav"
    with source.open("rb") as handle, wave.open(handle) as sound:
        if (sound.getnchannels(), sound.getsampwidth(), sound.getframerate()) != (1, 2, SAMPLE_RATE):
            raise ValueError(f"chime {stem} is not mono 16-bit {SAMPLE_RATE} Hz")
        raw = sound.readframes(sound.getnframes())
    samples = (np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32767.0).copy()
    _loaded[stem] = samples
    return samples


def load_chime(name: str) -> np.ndarray:
    """The chime's samples: float32 mono at 48 kHz, read once and kept."""

    if name not in CHIME_NAMES:
        raise ValueError(f"unknown chime: {name!r}")
    return _load(name)


def load_part_chime(name: str) -> np.ndarray:
    """The long sound that opens a part - and since 25/09 a chapter - for
    this chime family: its own part sound, or its chime where it has none."""

    if name not in CHIME_NAMES:
        raise ValueError(f"unknown chime: {name!r}")
    stem = PART_SOUNDS.get(name)
    return _load(name) if stem is None else _load(stem)


def load_section_chime(name: str) -> np.ndarray:
    """The short sound that opens a first-level section for this family:
    the first `SECTION_SECONDS` of its chime, softer, faded out."""

    if name not in CHIME_NAMES:
        raise ValueError(f"unknown chime: {name!r}")
    key = f"section-{name}"
    cached = _loaded.get(key)
    if cached is not None:
        return cached
    length = int(SAMPLE_RATE * SECTION_SECONDS)
    fade = int(SAMPLE_RATE * SECTION_FADE_SECONDS)
    cut = _load(name)[:length].copy()
    if cut.size < length:
        cut = np.pad(cut, (0, length - cut.size))
    cut *= np.float32(10 ** (SECTION_GAIN_DB / 20))
    cut[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    _loaded[key] = cut
    return cut
