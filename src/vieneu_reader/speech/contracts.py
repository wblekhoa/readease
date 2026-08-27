"""Typed speech synthesis port consumed by playback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol

from vieneu_reader.domain.models import AudioChunk, Voice


@dataclass(frozen=True, slots=True)
class SynthesisSettings:
    temperature: float = 0.8
    top_k: int = 25
    top_p: float = 0.95
    max_chars: int = 240
    repetition_penalty: float = 1.2


class SpeechEngine(Protocol):
    @property
    def engine_version(self) -> str: ...

    @property
    def model_revision(self) -> str: ...

    def voices(self) -> tuple[Voice, ...]: ...

    def stream(
        self,
        text: str,
        voice_id: str,
        settings: SynthesisSettings = SynthesisSettings(),
    ) -> Iterator[AudioChunk]: ...

    def cancel(self) -> None: ...
