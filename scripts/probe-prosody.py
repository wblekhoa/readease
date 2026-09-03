#!/usr/bin/env python3
"""Render one passage three ways and measure how much the voice moves.

"The voice sounds flat" is a judgement only ears can make, but the thing that
causes it can be measured: an autoregressive TTS restarts its pitch contour on
every call, so feeding it one sentence at a time produces a fresh, identical
arc per sentence and no shape across the paragraph.

This renders the SAME text through the REAL engine under three grouping
strategies, writes a .wav for the ear and a JSON of measures for the argument.
It changes nothing in the product; it exists so a change can be chosen instead
of guessed.

    python3 scripts/probe-prosody.py            # measure-only self-check
    python3 scripts/probe-prosody.py --render   # + synthesise through the model
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 48_000
ENGINE = Path.home() / "Applications/ReadEase.app/Contents/Resources/engine/readease-engine"
OUT = Path(__file__).resolve().parent.parent / "output" / "prosody-probe"

# Mixed sentence lengths on purpose: grouping can only show its hand when some
# sentences are short enough to be worth grouping.
PASSAGE = (
    "Năm nào họ cũng chú ý rất tốt đến tính dễ sử dụng, nội dung và chức năng. "
    "Nhưng họ bỏ qua phần giá trị cộng thêm. "
    "Vì thế những phương án đầu tiên đều nhanh chóng chìm vào quên lãng. "
    "Chỉ khi học cách nhìn vấn đề từ một góc khác, họ mới tạo ra được điều đặc biệt. "
    "Đừng hiểu lầm ý tôi. "
    "Trước hết, sản phẩm phải hoạt động."
)


# ---------------------------------------------------------------- measuring

def fundamental_frequencies(
    samples: np.ndarray,
    rate: int = SAMPLE_RATE,
    frame_ms: int = 40,
    floor_hz: int = 70,
    ceiling_hz: int = 400,
) -> np.ndarray:
    """Pitch per voiced frame, by autocorrelation.

    Deliberately plain: the question is whether pitch MOVES, and a simple
    estimator answers that as long as it is checked against signals whose
    answer is known - which `self_check` does before any speech is measured.
    """
    frame = int(rate * frame_ms / 1000)
    if samples.size < frame * 2:
        return np.array([])
    energy_floor = float(np.sqrt(np.mean(samples**2))) * 0.35
    lag_low, lag_high = rate // ceiling_hz, rate // floor_hz
    pitches: list[float] = []
    for start in range(0, samples.size - frame, frame):
        window = samples[start : start + frame]
        if float(np.sqrt(np.mean(window**2))) < energy_floor:
            continue  # silence or a breath: no pitch to speak of
        window = window - window.mean()
        correlation = np.correlate(window, window, mode="full")[frame - 1 :]
        segment = correlation[lag_low:lag_high]
        if segment.size == 0 or correlation[0] <= 0:
            continue
        lag = int(np.argmax(segment)) + lag_low
        if correlation[lag] / correlation[0] < 0.3:
            continue  # unvoiced
        pitches.append(rate / lag)
    return np.array(pitches)


def movement(pitches: np.ndarray) -> dict[str, float | int]:
    """How much the voice moves, in the two ways that matter to the ear."""
    if pitches.size < 4:
        return {"frames": int(pitches.size)}
    semitones = 12 * np.log2(pitches / statistics.median(pitches))
    # Slope over the whole passage: a paragraph read as one arc drifts down
    # (declination); sentences read in isolation reset and average to nothing.
    slope = float(np.polyfit(np.arange(semitones.size), semitones, 1)[0]) * 100
    return {
        "frames": int(pitches.size),
        "median_hz": round(float(statistics.median(pitches)), 1),
        "spread_semitones": round(float(np.percentile(semitones, 90) - np.percentile(semitones, 10)), 2),
        "drift_semitones_per_100_frames": round(slope, 3),
    }


def self_check() -> bool:
    """Prove the ruler before measuring anything with it."""
    duration, t = 3.0, np.arange(int(SAMPLE_RATE * 3.0)) / SAMPLE_RATE
    flat = np.sin(2 * np.pi * 200 * t).astype(np.float32)
    sweep_hz = np.linspace(150, 250, t.size)
    swept = np.sin(2 * np.pi * np.cumsum(sweep_hz) / SAMPLE_RATE).astype(np.float32)

    flat_m = movement(fundamental_frequencies(flat))
    swept_m = movement(fundamental_frequencies(swept))
    checks = {
        "flat tone reads ~200 Hz": abs(flat_m.get("median_hz", 0) - 200) < 6,
        "flat tone barely spreads": flat_m.get("spread_semitones", 9) < 0.6,
        "sweep spreads a lot": swept_m.get("spread_semitones", 0) > 3.0,
        "sweep drifts upward": swept_m.get("drift_semitones_per_100_frames", 0) > 0.3,
        "sweep drifts more than flat": abs(swept_m.get("drift_semitones_per_100_frames", 0))
        > abs(flat_m.get("drift_semitones_per_100_frames", 0)) * 5,
    }
    print(f"  đơn âm phẳng : {flat_m}")
    print(f"  quét 150→250 : {swept_m}")
    for name, ok in checks.items():
        print(f"  [{'OK ' if ok else 'SAI'}] {name}")
    print(f"  duration used: {duration}s")
    return all(checks.values())


# ---------------------------------------------------------------- rendering

def groups_per_sentence(sentences: list[str]) -> list[str]:
    """What the product does today: one call per sentence."""
    return list(sentences)


def groups_up_to(sentences: list[str], budget: int) -> list[str]:
    """Merge consecutive sentences while they fit, so one contour spans more
    than one sentence. `budget` stays under the model's own max_chars."""
    merged: list[str] = []
    for sentence in sentences:
        if merged and len(merged[-1]) + 1 + len(sentence) <= budget:
            merged[-1] = f"{merged[-1]} {sentence}"
        else:
            merged.append(sentence)
    return merged


VARIANTS = {
    "a-per-sentence": ("Mỗi câu một lượt (hiện tại)", lambda s: groups_per_sentence(s)),
    "b-grouped-180": ("Gom câu tới 180 ký tự", lambda s: groups_up_to(s, 180)),
    "c-grouped-240": ("Gom câu tới 240 ký tự (trần model)", lambda s: groups_up_to(s, 240)),
}


def render(engine, voice_id: str, groups: list[str]) -> tuple[np.ndarray, float]:
    """Synthesise each group, seam them with the product's own 100 ms rest."""
    from vieneu_reader.domain.prosody import SENTENCE_PAUSE_MS

    rest = np.zeros(int(SAMPLE_RATE * SENTENCE_PAUSE_MS / 1000), dtype=np.float32)
    pieces: list[np.ndarray] = []
    first_audio_at = None
    began = time.monotonic()
    for index, group in enumerate(groups):
        if index:
            pieces.append(rest)
        for chunk in engine.stream(group, voice_id):
            if first_audio_at is None:
                first_audio_at = time.monotonic() - began
            pieces.append(np.frombuffer(chunk.pcm, dtype=np.float32))
    audio = np.concatenate(pieces) if pieces else np.array([], dtype=np.float32)
    return audio, float(first_audio_at or 0.0)


def write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes((clipped * 32767).astype("<i2").tobytes())


def run_render() -> dict:
    from vieneu_reader.config import AppPaths, default_app_root
    from vieneu_reader.domain.prosody import split_sentences
    from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore
    from vieneu_reader.speech.vieneu import VieNeuSpeechEngine

    paths = AppPaths.create(default_app_root())
    precision = VoiceQualityPreferenceStore(paths.root / "settings.json").load()
    engine = VieNeuSpeechEngine(paths.models, precision=precision)
    voice_id = engine.voices()[0].id
    sentences = [s for s in split_sentences(PASSAGE) if s.strip()]
    print(f"  giọng: {voice_id} · bản: {precision} · {len(sentences)} câu")

    report = {"passage": PASSAGE, "voice": voice_id, "precision": precision,
              "sentences": len(sentences), "variants": {}}
    for key, (label, grouper) in VARIANTS.items():
        groups = grouper(sentences)
        audio, first = render(engine, voice_id, groups)
        path = OUT / f"{key}.wav"
        write_wav(path, audio)
        measures = movement(fundamental_frequencies(audio))
        report["variants"][key] = {
            "label": label,
            "calls_to_model": len(groups),
            "seconds": round(audio.size / SAMPLE_RATE, 2),
            "first_audio_seconds": round(first, 2),
            "file": str(path),
            **measures,
        }
        print(f"  [{key}] {len(groups)} lượt gọi · {measures}")
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    print("Kiểm định thước đo trước khi dùng:")
    ok = self_check()
    if not ok:
        print("THƯỚC ĐO SAI - không đo giọng bằng nó.")
        sys.exit(1)
    print("Thước đo đạt.")
    if args.render:
        print("Dựng ba biến thể bằng model thật (chậm, kiên nhẫn):")
        run_render()
        print(f"Xong. Nghe ở: {OUT}")
