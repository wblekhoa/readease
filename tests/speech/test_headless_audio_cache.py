"""A sentence already spoken is never bought twice - and never half-kept.

The cache existed (speech/cache.py, atomic + LRU) but only the Qt shell used
it; the headless server re-synthesised every re-read. That was merely slow
while the voice was a local model. It stops being merely slow the moment a
voice bills by the character.
"""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from vieneu_reader.domain.models import AudioChunk, Voice  # noqa: E402
from vieneu_reader.speech.cache import AudioCache  # noqa: E402
from vieneu_reader.speech.contracts import SynthesisSettings  # noqa: E402


def _tone(seconds: float = 0.05) -> AudioChunk:
    samples = np.zeros(int(48_000 * seconds), dtype=np.float32) + 0.25
    return AudioChunk(pcm=samples.tobytes())


class CountingEngine:
    """A real-shaped engine that says how many times it was asked."""

    engine_version = "counting-1"
    model_revision = "rev-1"

    def __init__(self, chunks_per_sentence: int = 2):
        self.calls: list[str] = []
        self._chunks = chunks_per_sentence

    def voices(self) -> tuple[Voice, ...]:
        return (Voice(id="V", label="V"),)

    def stream(self, text, voice_id, settings=SynthesisSettings()):
        self.calls.append(text)
        for _ in range(self._chunks):
            yield _tone()


class HeadlessCacheTests(unittest.TestCase):
    def _run(self, engine, cache, requests):
        from tests.headless.test_server import run_server

        return run_server(requests, engine, audio_cache=cache)

    def test_a_second_reading_of_the_same_text_asks_the_engine_nothing(self) -> None:
        with TemporaryDirectory() as directory:
            cache = AudioCache(Path(directory))
            engine = CountingEngine()
            request = {
                "id": 1, "method": "read",
                "params": {"text": "Một câu.", "voice_id": "V", "rate": 1.0},
            }
            first = self._run(engine, cache, [request])
            self.assertTrue(first[-1]["ok"])
            asked_first = len(engine.calls)
            self.assertGreater(asked_first, 0)

            second = self._run(engine, cache, [dict(request, id=2)])
            self.assertTrue(second[-1]["ok"])
            # The seam itself is watched: not "it was fast", but "it never
            # asked".
            self.assertEqual(len(engine.calls), asked_first)

    def test_the_same_words_at_another_speed_reuse_what_was_bought(self) -> None:
        # The rate is applied on the way OUT, so 1.5x must not re-synthesise.
        with TemporaryDirectory() as directory:
            cache = AudioCache(Path(directory))
            engine = CountingEngine()
            self._run(engine, cache, [{
                "id": 1, "method": "read",
                "params": {"text": "Một câu.", "voice_id": "V", "rate": 1.0},
            }])
            asked = len(engine.calls)
            self._run(engine, cache, [{
                "id": 2, "method": "read",
                "params": {"text": "Một câu.", "voice_id": "V", "rate": 1.5},
            }])
            self.assertEqual(len(engine.calls), asked)

    def test_another_voice_is_another_purchase(self) -> None:
        with TemporaryDirectory() as directory:
            cache = AudioCache(Path(directory))
            engine = CountingEngine()
            for voice in ("V", "W"):
                self._run(engine, cache, [{
                    "id": 1, "method": "read",
                    "params": {"text": "Một câu.", "voice_id": voice, "rate": 1.0},
                }])
            self.assertEqual(len(engine.calls), 2)

    def test_a_reading_stopped_mid_sentence_keeps_nothing(self) -> None:
        # Half a sentence in the cache would be served as a whole one for
        # ever after - the reader would hear the text cut off and never know
        # why. Better to have bought it and kept nothing.
        with TemporaryDirectory() as directory:
            cache = AudioCache(Path(directory))
            engine = CountingEngine(chunks_per_sentence=6)
            # The stop rides in behind the read, which is how the shell's
            # own stop arrives: queued while the audio is streaming.
            self._run(engine, cache, [
                {"id": 1, "method": "read",
                 "params": {"text": "Một câu dài.", "voice_id": "V", "rate": 1.0}},
                {"id": 2, "method": "stop"},
            ])
            self.assertEqual(list(Path(directory).glob("*.f32")), [])

            # And the next full reading does buy it, then keeps it.
            engine2 = CountingEngine()
            self._run(engine2, cache, [{
                "id": 2, "method": "read",
                "params": {"text": "Một câu dài.", "voice_id": "V", "rate": 1.0},
            }])
            self.assertEqual(len(list(Path(directory).glob("*.f32"))), 1)

    def test_an_engine_with_no_identity_is_never_cached_under_an_empty_name(self) -> None:
        # Two different stub engines must not collide in one cache.
        with TemporaryDirectory() as directory:
            cache = AudioCache(Path(directory))

            class Anonymous(CountingEngine):
                engine_version = ""

            engine = Anonymous()
            for identifier in (1, 2):
                self._run(engine, cache, [{
                    "id": identifier, "method": "read",
                    "params": {"text": "Một câu.", "voice_id": "V", "rate": 1.0},
                }])
            self.assertEqual(list(Path(directory).glob("*.f32")), [])
            self.assertEqual(len(engine.calls), 2)


if __name__ == "__main__":
    unittest.main()
