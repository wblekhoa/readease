#!/usr/bin/env python3
"""Render the landing page's two voice demos through the real local engines.

    .venv/bin/python scripts/render-voice-demos.py --models <a COPY of Models/>

Point --models at a clone of the app's Models/ (`cp -cR`), never the live
one: the engines may write readiness files there. Nothing else is touched -
no library, no settings. Writes, into assets/voice-demos/:

  vi.m4a, en.m4a   AAC 64 kb/s mono, levelled to the same loudness
and site/src/voiceBars.js: 34 peak heights per demo, so the page draws the
real wave of the very audio it plays.

The audit pins both .m4a files by hash; a re-render must update those pins
(scripts/audit-public-release.py) and README.md beside the files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/voice-demos"
RATE = 48_000
BARS = 34
TEXT = {
    "vi": "Để chữ cất lời. ReadEase đọc tài liệu, bài viết hay đoạn bạn vừa chọn, ngay trên máy Mac của bạn.",
    "en": "Let words speak. ReadEase reads your documents, articles, or any passage you select, right on your Mac.",
}
VOICE = {"vi": "Ngọc Linh", "en": "af_heart"}


def engine_for(language: str, models: Path):
    if language == "vi":
        from vieneu_reader.speech.vieneu import VieNeuSpeechEngine
        return VieNeuSpeechEngine(models, precision="fp32")
    from vieneu_reader.speech.kokoro import KokoroSpeechEngine
    return KokoroSpeechEngine(models)


def render(engine, voice: str, text: str) -> np.ndarray:
    from vieneu_reader.domain.prosody import SENTENCE_PAUSE_MS, split_sentences
    rest = np.zeros(int(RATE * max(SENTENCE_PAUSE_MS, 260) / 1000), dtype=np.float32)
    pieces: list[np.ndarray] = []
    for index, sentence in enumerate(s for s in split_sentences(text) if s.strip()):
        if index:
            pieces.append(rest)
        for chunk in engine.stream(sentence, voice):
            if chunk.sample_rate != RATE:
                raise SystemExit(f"unexpected sample rate {chunk.sample_rate}")
            pieces.append(np.frombuffer(chunk.pcm, dtype=np.float32))
    return np.concatenate(pieces)


def level(audio: np.ndarray, target_db: float = -19.0) -> np.ndarray:
    rms = float(np.sqrt(np.mean(audio ** 2))) or 1.0
    gain = min(10 ** (target_db / 20) / rms, 0.9 / float(np.max(np.abs(audio))))
    return np.clip(audio * gain, -1.0, 1.0)


def bars(audio: np.ndarray) -> list[int]:
    peaks = np.array([np.abs(part).max() for part in np.array_split(audio, BARS)])
    return [int(round(22 + 72 * p / peaks.max())) for p in peaks]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "src"))
    OUT.mkdir(parents=True, exist_ok=True)
    shapes = {}
    for language, text in TEXT.items():
        audio = level(render(engine_for(language, args.models), VOICE[language], text))
        shapes[language] = bars(audio)
        with tempfile.TemporaryDirectory() as scratch:
            wav = Path(scratch) / "demo.wav"
            with wave.open(str(wav), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(RATE)
                handle.writeframes((audio * 32767).astype("<i2").tobytes())
            subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000",
                            str(wav), str(OUT / f"{language}.m4a")], check=True)
        print(f"VOICE_DEMO {language} {VOICE[language]} {audio.size / RATE:.2f}s")
    (ROOT / "site/src/voiceBars.js").write_text(
        "/* Peak heights (%) of the two voice demos, written by\n"
        "   scripts/render-voice-demos.py from the same render as the .m4a files. */\n"
        f"export const voiceBars = {json.dumps(shapes)};\n", encoding="utf-8")


if __name__ == "__main__":
    main()
