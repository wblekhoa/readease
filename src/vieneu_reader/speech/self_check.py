"""Offline speech probe executed by the packaged application."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
import sys
from typing import Callable, Protocol

from vieneu_reader.config import AppPaths, default_app_root
from vieneu_reader.domain.models import AudioChunk, Voice

from .preferences import VoiceQualityPreferenceStore
from .vieneu import VieNeuSpeechEngine


class _SelfCheckEngine(Protocol):
    @property
    def is_model_ready(self) -> bool: ...

    @property
    def precision(self) -> str: ...

    def voices(self) -> tuple[Voice, ...]: ...

    def stream(self, text: str, voice_id: str): ...


def run_tts_self_check(
    app_data_root: Path | None = None,
    *,
    engine_factory: Callable[..., _SelfCheckEngine] = VieNeuSpeechEngine,
) -> int:
    """Synthesize a short preset-voice sample without downloading assets."""

    paths = AppPaths.create(app_data_root or default_app_root())
    # Probe the build this Mac will actually read with, not whichever one
    # happens to be the default.
    precision = VoiceQualityPreferenceStore(paths.root / "settings.json").load()
    engine = engine_factory(paths.models, precision=precision)
    if not engine.is_model_ready:
        raise RuntimeError("VieNeu model is not prepared; self-check will not download it")

    voices = engine.voices()
    if not voices:
        raise RuntimeError("VieNeu exposes no preset voice")

    samples = array("f")
    sample_rate: int | None = None
    for chunk in engine.stream(
        "Xin chào. ReadEase đang kiểm tra giọng đọc tiếng Việt.",
        voices[0].id,
    ):
        _validate_chunk(chunk, sample_rate)
        sample_rate = chunk.sample_rate
        values = array("f")
        values.frombytes(chunk.pcm)
        if sys.byteorder != "little":
            values.byteswap()
        samples.extend(values)

    if sample_rate != 48_000 or len(samples) < 4_800:
        raise RuntimeError("VieNeu returned insufficient 48 kHz audio")
    if not all(math.isfinite(value) for value in samples):
        raise RuntimeError("VieNeu returned non-finite audio")
    peak = max((abs(value) for value in samples), default=0.0)
    if peak <= 1e-5:
        raise RuntimeError("VieNeu returned silent audio")

    print(
        "TTS_SELF_CHECK PASS "
        f"precision={getattr(engine, 'precision', 'unknown')} "
        f"sample_rate={sample_rate} samples={len(samples)} peak={peak:.6f}"
    )
    return 0


def _validate_chunk(chunk: AudioChunk, expected_rate: int | None) -> None:
    if chunk.channels != 1 or chunk.sample_format != "float32":
        raise RuntimeError("VieNeu returned an unsupported audio format")
    if chunk.sample_rate != 48_000:
        raise RuntimeError("VieNeu returned audio at an unexpected sample rate")
    if expected_rate is not None and chunk.sample_rate != expected_rate:
        raise RuntimeError("VieNeu changed sample rate during synthesis")
    if not chunk.pcm or len(chunk.pcm) % 4:
        raise RuntimeError("VieNeu returned an incomplete audio chunk")
