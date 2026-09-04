"""One question, one answer, asked by every caller."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vieneu_reader.speech.external.route import pick_voice_route, provider_of  # noqa: E402

KEYS = {"openai_api_key": "sk-something-long-enough"}


class RouteTests(unittest.TestCase):
    def test_a_bare_name_is_the_local_model(self) -> None:
        self.assertIsNone(provider_of("Minh Đức"))
        self.assertEqual(pick_voice_route("Minh Đức", keys={}).kind, "local")

    def test_a_namespaced_voice_with_a_key_goes_outside(self) -> None:
        route = pick_voice_route("openai:tts-1:alloy", keys=KEYS)
        self.assertEqual((route.kind, route.provider), ("external", "openai"))

    def test_no_key_is_a_named_refusal_not_a_silent_fallback(self) -> None:
        # Falling back to the local voice without saying so would have the
        # reader hear a different voice than the one they picked and never
        # learn why.
        route = pick_voice_route("openai:tts-1:alloy", keys={})
        self.assertEqual((route.kind, route.reason), ("blocked", "no_key"))

    def test_the_budget_blocks_before_anything_is_sent(self) -> None:
        route = pick_voice_route("openai:tts-1:alloy", keys=KEYS, would_exceed_budget=True)
        self.assertEqual((route.kind, route.reason), ("blocked", "budget"))

    def test_an_unknown_prefix_is_a_local_voice_with_a_colon_in_its_name(self) -> None:
        # A local voice could be called anything; only known providers claim
        # a namespace.
        self.assertIsNone(provider_of("someone:else"))
        self.assertEqual(pick_voice_route("someone:else", keys={}).kind, "local")

    def test_the_model_rides_in_the_id_because_it_sets_the_price(self) -> None:
        from vieneu_reader.speech.external.route import model_of

        self.assertEqual(model_of("openai:tts-1-hd:nova"), "tts-1-hd")
        self.assertIsNone(model_of("Minh Đức"))
        self.assertIsNone(model_of("openai:alloy"))

    def test_the_other_provider_reads_its_own_key(self) -> None:
        self.assertEqual(
            pick_voice_route("elevenlabs:eleven_v3:rachel", keys=KEYS).reason, "no_key"
        )
        self.assertEqual(
            pick_voice_route(
                "elevenlabs:eleven_v3:rachel", keys={"elevenlabs_api_key": "xi-long-enough"}
            ).kind,
            "external",
        )


if __name__ == "__main__":
    unittest.main()
