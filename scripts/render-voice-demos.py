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
    "vi": ("Để chữ cất lời. ReadEase đọc tài liệu, bài viết hay đoạn bạn vừa chọn, ngay trên máy Mac của bạn. "
           "Giọng đọc ngắt nghỉ theo dấu câu, nhấn nhẹ ở tiêu đề, và chờ bạn một nhịp khi sang chương mới. "
           "Mọi thứ chạy ngay trên máy, không cần mạng, không cần tài khoản."),
    "en": ("Let words speak. ReadEase reads your documents, articles, or any passage you select, right on your Mac. "
           "The voice pauses where the punctuation asks, leans a little on headings, and takes a breath before each new chapter. "
           "Everything runs on your Mac, with no account and no connection needed."),
}
VOICE = {"vi": "Ngọc Linh", "en": "af_heart"}
# Paid voices (--api): the providers' own stock voices, never a library or
# cloned voice. Keys are read from the app's settings and never printed.
API_VOICE = {"openai": ("marin", "Marin"), "elevenlabs": ("EXAVITQu4vr4xnSDxMaL", "Sarah")}
API_RATE = 24_000


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


def encode(audio: np.ndarray, rate: int, name: str) -> None:
    with tempfile.TemporaryDirectory() as scratch:
        wav = Path(scratch) / "demo.wav"
        with wave.open(str(wav), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(rate)
            handle.writeframes((audio * 32767).astype("<i2").tobytes())
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000",
                        str(wav), str(OUT / f"{name}.m4a")], check=True)


def render_api(shapes: dict) -> None:
    """Spends a few cents of the owner's own credit; sends only the demo text."""
    from vieneu_reader.speech.external.elevenlabs import ElevenLabsVoiceProvider
    from vieneu_reader.speech.external.openai import OpenAIVoiceProvider
    settings = json.loads((Path.home() / "Library/Application Support/VieNeu Reader/settings.json").read_text())
    makers = {"openai": lambda: OpenAIVoiceProvider(settings["openai_api_key"]),
              "elevenlabs": lambda: ElevenLabsVoiceProvider(settings["elevenlabs_api_key"])}
    for provider, make in makers.items():
        voice, label = API_VOICE[provider]
        for language, text in TEXT.items():
            pcm = b"".join(make().synthesize(text, voice))
            audio = level(np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768)
            name = f"{provider}-{language}"
            shapes[name] = bars(audio)
            encode(audio, API_RATE, name)
            print(f"VOICE_DEMO {name} {label} {audio.size / API_RATE:.2f}s")


def write_bars(shapes: dict) -> None:
    target = ROOT / "site/src/voiceBars.js"
    if target.exists():
        import re
        found = re.search(r"= (\{.*\});", target.read_text())
        shapes = {**(json.loads(found.group(1)) if found else {}), **shapes}
    target.write_text(
        "/* Peak heights (%) of the voice demos, written by\n"
        "   scripts/render-voice-demos.py from the same render as the .m4a files. */\n"
        f"export const voiceBars = {json.dumps(shapes)};\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path)
    parser.add_argument("--api", action="store_true", help="render the paid-voice demos instead")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "src"))
    OUT.mkdir(parents=True, exist_ok=True)
    shapes = {}
    if args.api:
        render_api(shapes)
        write_bars(shapes)
        return
    if not args.models:
        parser.error("--models is required for the local demos")
    for language, text in TEXT.items():
        audio = level(render(engine_for(language, args.models), VOICE[language], text))
        shapes[language] = bars(audio)
        encode(audio, RATE, language)
        print(f"VOICE_DEMO {language} {VOICE[language]} {audio.size / RATE:.2f}s")
    write_bars(shapes)


if __name__ == "__main__":
    main()
