"""The short sounds that mark a chapter's start (owner, 16/09: "nhạc chờ
ngắn giữa các chương").

Three of them, chosen by ear from a batch generated with ElevenLabs'
sound-effects model, then downmixed to mono at the pipe's 48 kHz, trimmed
of silence and levelled to -14 dBFS so they sit under speech (which peaks
around -3 to -6) rather than over it. They are package data - about 470 KB
for the three - not something the engine synthesises, so the reader hears
the same sound every time and nothing is fetched.

A chime is played as a plain frame, the way the silence between paragraphs
is: not through the time-stretcher (a chime should not speed up with the
reading), not into the sentence cache, and never billed to a paid voice.
"""

from __future__ import annotations

import wave
from importlib import resources

import numpy as np

CHIME_NAMES: tuple[str, ...] = ("marimba", "harp", "piano")
DEFAULT_CHIME = "marimba"
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


def load_chime(name: str) -> np.ndarray:
    """The chime's samples: float32 mono at 48 kHz, read once and kept."""

    cached = _loaded.get(name)
    if cached is not None:
        return cached
    if name not in CHIME_NAMES:
        raise ValueError(f"unknown chime: {name!r}")
    source = resources.files("vieneu_reader.speech") / "chimes" / f"{name}.wav"
    with source.open("rb") as handle, wave.open(handle) as sound:
        if (sound.getnchannels(), sound.getsampwidth(), sound.getframerate()) != (1, 2, SAMPLE_RATE):
            raise ValueError(f"chime {name} is not mono 16-bit {SAMPLE_RATE} Hz")
        raw = sound.readframes(sound.getnframes())
    samples = (np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32767.0).copy()
    _loaded[name] = samples
    return samples
