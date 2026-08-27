"""Immutable data exchanged by import, storage, speech, playback, and UI."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal


def stable_id(*parts: str) -> str:
    """Return a deterministic identifier for ordered UTF-8 components."""

    payload = "\0".join(parts).encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class Segment:
    id: str
    chapter_id: str
    ordinal: int
    text: str


@dataclass(frozen=True, slots=True)
class Chapter:
    id: str
    title: str
    ordinal: int
    segments: tuple[Segment, ...]


@dataclass(frozen=True, slots=True)
class BookDocument:
    id: str
    title: str
    source_format: Literal["pdf", "epub"]
    source_hash: str
    chapters: tuple[Chapter, ...]


@dataclass(frozen=True, slots=True)
class Voice:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class AudioChunk:
    pcm: bytes
    sample_rate: int = 48_000
    channels: int = 1
    sample_format: Literal["float32"] = "float32"
