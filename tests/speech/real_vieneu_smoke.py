"""Explicit online-then-offline smoke for the real VieNeu 3.3.0 engine."""

from __future__ import annotations

from array import array
import os
from pathlib import Path
import sys

from vieneu_reader.config import AppPaths
from vieneu_reader.speech.vieneu import VieNeuSpeechEngine


def _assert_non_silent(engine: VieNeuSpeechEngine, voice_id: str) -> tuple[int, float]:
    chunks = tuple(
        engine.stream(
            "Xin chào. Đây là ReadEase đang đọc sách tiếng Việt.",
            voice_id,
        )
    )
    if not chunks or any(chunk.sample_rate != 48_000 for chunk in chunks):
        raise AssertionError("VieNeu did not produce 48 kHz audio chunks")
    pcm = b"".join(chunk.pcm for chunk in chunks)
    samples = array("f")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max((abs(sample) for sample in samples), default=0.0)
    if len(samples) < 4_800 or peak <= 1e-5:
        raise AssertionError("VieNeu audio is empty, too short, or silent")
    return len(samples), peak


def main() -> int:
    if os.environ.get("VIENEU_READER_REAL_TTS") != "1":
        print("REAL_VIENEU_SMOKE SKIP (set VIENEU_READER_REAL_TTS=1)")
        return 0

    paths = AppPaths.create(
        Path.home() / "Library" / "Application Support" / "VieNeu Reader"
    )
    engine = VieNeuSpeechEngine(paths.models)
    engine.prepare_model(
        lambda progress, message: print(f"MODEL {progress:.0%} {message}", flush=True)
    )
    voices = engine.voices()
    if not voices:
        raise AssertionError("VieNeu did not expose a preset voice")
    online_samples, online_peak = _assert_non_silent(engine, voices[0].id)

    os.environ["HF_HUB_OFFLINE"] = "1"
    offline_engine = VieNeuSpeechEngine(paths.models)
    offline_voices = offline_engine.voices()
    offline_samples, offline_peak = _assert_non_silent(
        offline_engine,
        offline_voices[0].id,
    )
    print(
        "REAL_VIENEU_SMOKE PASS "
        f"online_samples={online_samples} online_peak={online_peak:.6f} "
        f"offline_samples={offline_samples} offline_peak={offline_peak:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
