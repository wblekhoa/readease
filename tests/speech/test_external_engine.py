"""A paid provider wearing the local model's face - and failing in words.

No network anywhere here: the HTTP call is injected, so the request shape,
the header, the error mapping and the redaction are all checked without a
key and without spending anything.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import unittest
import urllib.error

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vieneu_reader.speech.external.engine import (  # noqa: E402
    ExternalSpeechEngine,
    to_float32_48k,
)
from vieneu_reader.speech.external.openai import OpenAIVoiceProvider  # noqa: E402
from vieneu_reader.speech.external.provider import ExternalVoiceError  # noqa: E402
from vieneu_reader.speech.external.spend import SpendMeter  # noqa: E402

KEY = "sk-proj-0123456789abcdefghijklmnopqrstuvwxyz"


def s16(*values: int) -> bytes:
    return np.array(values, dtype="<i2").tobytes()


class ResampleTests(unittest.TestCase):
    def test_it_doubles_the_rate_and_lands_between_the_samples(self) -> None:
        out = to_float32_48k(s16(0, 16384, -16384, 32767))
        self.assertEqual(out.size, 8)
        # value, midpoint, value, midpoint...
        self.assertAlmostEqual(float(out[0]), 0.0, places=4)
        self.assertAlmostEqual(float(out[1]), 0.25, places=4)
        self.assertAlmostEqual(float(out[2]), 0.5, places=4)
        self.assertAlmostEqual(float(out[3]), 0.0, places=4)
        self.assertEqual(out.dtype, np.float32)

    def test_two_chunks_resample_to_exactly_what_one_would_have(self) -> None:
        # This is the test that found the click. Resampling each chunk on its
        # own has to invent a successor for its last sample, so the boundary
        # got a held value and lost a midpoint. Holding one sample back until
        # the next chunk arrives makes the seam disappear entirely - the two
        # halves now equal the whole, sample for sample.
        from vieneu_reader.speech.external.engine import Upsampler

        whole = to_float32_48k(s16(1000, 2000, 3000, 4000))
        upsampler = Upsampler()
        joined = np.concatenate((
            upsampler.feed(s16(1000, 2000)),
            upsampler.feed(s16(3000, 4000)),
            upsampler.drain(),
        ))
        self.assertEqual(joined.size, whole.size)
        np.testing.assert_allclose(joined, whole, atol=1e-6)

    def test_a_chunk_that_arrives_one_sample_at_a_time_still_matches(self) -> None:
        from vieneu_reader.speech.external.engine import Upsampler

        values = (500, -700, 900, -1100, 1300)
        whole = to_float32_48k(s16(*values))
        upsampler = Upsampler()
        pieces = [upsampler.feed(s16(value)) for value in values]
        pieces.append(upsampler.drain())
        np.testing.assert_allclose(np.concatenate(pieces), whole, atol=1e-6)

    def test_silence_and_emptiness_survive(self) -> None:
        self.assertEqual(to_float32_48k(b"").size, 0)
        self.assertTrue(np.all(to_float32_48k(s16(0, 0, 0)) == 0))

    def test_half_a_sample_is_refused_rather_than_guessed(self) -> None:
        with self.assertRaises(ValueError):
            to_float32_48k(b"\x01")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()
        return False


class ProviderTests(unittest.TestCase):
    def _provider(self, handler):
        return OpenAIVoiceProvider(KEY, opener=handler)

    def test_it_sends_the_words_and_nothing_about_the_reader(self) -> None:
        seen = {}

        def handler(request):
            seen["url"] = request.full_url
            seen["headers"] = dict(request.headers)
            seen["body"] = json.loads(request.data)
            return FakeResponse(s16(1, 2, 3, 4))

        list(self._provider(handler).synthesize("Một câu.", "alloy"))
        self.assertEqual(seen["url"], "https://api.openai.com/v1/audio/speech")
        self.assertEqual(seen["body"]["input"], "Một câu.")
        self.assertEqual(seen["body"]["response_format"], "pcm")
        self.assertEqual(seen["body"]["voice"], "alloy")
        # The payload is the text and the voice. Nothing identifies the book,
        # the reader or the machine.
        self.assertEqual(
            set(seen["body"]), {"model", "voice", "input", "response_format"}
        )
        self.assertIn("Bearer", str(seen["headers"]))

    def _refuse(self, status: int, payload: dict):
        def handler(request):
            raise urllib.error.HTTPError(
                "https://api.openai.com/v1/audio/speech",
                status,
                "refused",
                {},
                io.BytesIO(json.dumps(payload).encode("utf-8")),
            )

        return handler

    def test_each_refusal_gets_a_name_a_person_can_act_on(self) -> None:
        cases = {
            401: ("bad_key", {"error": {"message": "Incorrect API key"}}),
            429: ("rate_limit", {"error": {"message": "Slow down"}}),
            500: ("provider_down", {"error": {"message": "server error"}}),
            400: ("refused", {"error": {"message": "input too long"}}),
        }
        for status, (code, payload) in cases.items():
            with self.subTest(status=status):
                with self.assertRaises(ExternalVoiceError) as caught:
                    list(self._provider(self._refuse(status, payload)).synthesize("x", "alloy"))
                self.assertEqual(caught.exception.code, code)

    def test_out_of_credit_is_not_the_same_as_going_too_fast(self) -> None:
        handler = self._refuse(
            429, {"error": {"message": "You exceeded your quota", "code": "insufficient_quota"}}
        )
        with self.assertRaises(ExternalVoiceError) as caught:
            list(self._provider(handler).synthesize("x", "alloy"))
        self.assertEqual(caught.exception.code, "quota")

    def test_an_error_that_quotes_the_key_never_reaches_the_caller(self) -> None:
        handler = self._refuse(401, {"error": {"message": f"Incorrect API key provided: {KEY}"}})
        with self.assertRaises(ExternalVoiceError) as caught:
            list(self._provider(handler).synthesize("x", "alloy"))
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn(KEY, caught.exception.message)

    def test_a_network_that_never_arrived_says_so(self) -> None:
        def handler(request):
            raise urllib.error.URLError("nodename nor servname provided")

        with self.assertRaises(ExternalVoiceError) as caught:
            list(self._provider(handler).synthesize("x", "alloy"))
        self.assertEqual(caught.exception.code, "network")


class EngineTests(unittest.TestCase):
    def _engine(self, pieces):
        def handler(request):
            return FakeResponse(b"".join(pieces))

        return ExternalSpeechEngine(OpenAIVoiceProvider(KEY, opener=handler))

    def test_it_answers_the_same_protocol_the_local_model_does(self) -> None:
        engine = self._engine([s16(0, 1000)])
        self.assertEqual(engine.engine_version, "external:openai")
        self.assertEqual(engine.model_revision, "tts-1")
        voices = engine.voices()
        self.assertTrue(voices)
        # Namespaced so a provider voice can never collide with a local one
        # in a shortlist or a cache key.
        self.assertTrue(all(voice.id.startswith("openai:tts-1:") for voice in voices))

    def test_the_chunks_it_yields_are_what_the_cache_and_player_accept(self) -> None:
        chunks = list(self._engine([s16(*range(200))]).stream("Một câu.", "openai:tts-1:alloy"))
        self.assertTrue(chunks)
        for chunk in chunks:
            self.assertEqual(chunk.sample_rate, 48_000)
            self.assertEqual(chunk.channels, 1)
            self.assertEqual(chunk.sample_format, "float32")
            self.assertEqual(len(chunk.pcm) % 4, 0)
        total = sum(len(chunk.pcm) // 4 for chunk in chunks)
        self.assertEqual(total, 400)

    def test_a_byte_split_across_two_reads_is_not_dropped(self) -> None:
        # An odd-length read would otherwise shift every later sample by half
        # a sample and turn the rest of the sentence into noise.
        raw = s16(*range(100))

        def handler(request):
            return FakeResponse(raw)

        engine = ExternalSpeechEngine(OpenAIVoiceProvider(KEY, opener=handler))
        chunks = list(engine.stream("x", "openai:tts-1:alloy"))
        self.assertEqual(sum(len(chunk.pcm) // 4 for chunk in chunks), 200)


class SpendTests(unittest.TestCase):
    def test_it_adds_up_and_stops_at_the_ceiling(self) -> None:
        meter = SpendMeter(limit_usd=0.10)
        self.assertFalse(meter.would_exceed(0.05))
        meter.add(1000, 0.05)
        meter.add(1000, 0.05)
        snapshot = meter.snapshot()
        self.assertEqual(snapshot.chars, 2000)
        self.assertEqual(snapshot.usd, 0.10)
        self.assertTrue(snapshot.exhausted)
        self.assertTrue(meter.would_exceed(0.01))

    def test_no_ceiling_means_no_ceiling(self) -> None:
        meter = SpendMeter()
        meter.add(100_000, 15.0)
        self.assertFalse(meter.snapshot().exhausted)
        self.assertFalse(meter.would_exceed(1000.0))

    def test_the_limit_is_asked_BEFORE_spending_not_after(self) -> None:
        # A ceiling noticed after the request is not a ceiling.
        meter = SpendMeter(limit_usd=1.00)
        meter.add(0, 0.99)
        self.assertTrue(meter.would_exceed(0.02))
        self.assertFalse(meter.snapshot().exhausted)

    def test_cents_do_not_drift_over_a_chapter(self) -> None:
        meter = SpendMeter()
        for _ in range(1000):
            meter.add(1, 0.000015)
        self.assertAlmostEqual(meter.snapshot().usd, 0.015, places=4)


if __name__ == "__main__":
    unittest.main()
