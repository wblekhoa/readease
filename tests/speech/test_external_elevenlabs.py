"""ElevenLabs, over a fake transport.

The thing worth testing here is not that a POST goes out - it is the two
places this provider does NOT behave like the OpenAI one, because both are
places where copying the first provider would produce an app that lies:

  * 401 means "wrong key" and also "out of credit", so the BODY has to
    decide; reading the status alone tells someone who has run out that
    their key is bad, and they go and replace a key that was fine.
  * the catalogue is a live, paged call, so it can fail and it can be long.

Every request is asserted against the documented shape [fetched 2026-09-04]:
a wrong query parameter or a body field in the wrong place is a request that
works in a test and 400s on a reader's machine.
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import unittest
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from vieneu_reader.speech.external.elevenlabs import (  # noqa: E402
    MAX_VOICES,
    ElevenLabsVoiceProvider,
)
from vieneu_reader.speech.external.provider import ExternalVoiceError  # noqa: E402

KEY = "sk_elevenlabs_secret_value"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()
        return False


def refuse(status: int, payload: dict):
    def handler(request):
        raise urllib.error.HTTPError(
            request.full_url, status, "refused", {}, io.BytesIO(json.dumps(payload).encode())
        )

    return handler


def page(names: list[str], *, token: str = "", more: bool = False) -> dict:
    return {
        "voices": [{"voice_id": f"id-{name}", "name": name} for name in names],
        "has_more": more,
        "next_page_token": token,
    }


class RequestShapeTests(unittest.TestCase):
    def test_the_request_matches_the_documented_endpoint(self) -> None:
        seen = {}

        def handler(request):
            seen["url"] = request.full_url
            seen["headers"] = dict(request.headers)
            seen["body"] = json.loads(request.data)
            return FakeResponse(b"\x01\x02\x03\x04")

        provider = ElevenLabsVoiceProvider(KEY, opener=handler)
        list(provider.synthesize("Một câu.", "voice-42"))

        self.assertIn(
            "https://api.elevenlabs.io/v1/text-to-speech/voice-42/stream", seen["url"]
        )
        # output_format is a QUERY parameter here, not a body field - putting
        # it in the body silently returns mp3 and the player then plays noise.
        self.assertIn("output_format=pcm_24000", seen["url"])
        # Zero retention, asked for per request.
        self.assertIn("enable_logging=false", seen["url"])
        self.assertEqual(seen["body"]["text"], "Một câu.")
        self.assertEqual(seen["body"]["model_id"], "eleven_flash_v2_5")
        # The words and the model. Nothing about the book or the reader.
        self.assertEqual(set(seen["body"]), {"text", "model_id"})
        self.assertIn("Xi-api-key", seen["headers"])

    def test_the_default_model_is_the_one_that_speaks_vietnamese(self) -> None:
        # eleven_flash_v2_5 is the model whose language list names Vietnamese
        # [fetched 2026-09-04]; it is also half the price of v3. A default
        # that cannot say the language the app exists for is not a default.
        self.assertEqual(ElevenLabsVoiceProvider(KEY).model, "eleven_flash_v2_5")


class RefusalTests(unittest.TestCase):
    def _synth(self, handler):
        return list(ElevenLabsVoiceProvider(KEY, opener=handler).synthesize("x", "v"))

    def test_out_of_credit_is_not_a_bad_key_even_though_both_are_401(self) -> None:
        handler = refuse(401, {"detail": {"status": "quota_exceeded", "message": "no credit"}})
        with self.assertRaises(ExternalVoiceError) as caught:
            self._synth(handler)
        self.assertEqual(caught.exception.code, "quota")

    def test_a_wrong_key_is_named_as_one(self) -> None:
        handler = refuse(401, {"detail": {"status": "invalid_api_key", "message": "nope"}})
        with self.assertRaises(ExternalVoiceError) as caught:
            self._synth(handler)
        self.assertEqual(caught.exception.code, "bad_key")

    def test_every_documented_refusal_gets_a_name_a_person_can_act_on(self) -> None:
        cases = {
            "detected_unusual_activity": "refused",
            "max_character_limit_exceeded": "refused",
            "voice_not_found": "refused",
        }
        for word, code in cases.items():
            with self.subTest(status=word):
                with self.assertRaises(ExternalVoiceError) as caught:
                    self._synth(refuse(400, {"detail": {"status": word, "message": "m"}}))
                self.assertEqual(caught.exception.code, code)

    def test_a_body_that_says_nothing_falls_back_to_the_status(self) -> None:
        for status, code in ((429, "rate_limit"), (503, "provider_down"), (400, "refused")):
            with self.subTest(status=status):
                with self.assertRaises(ExternalVoiceError) as caught:
                    self._synth(refuse(status, {"nothing": "useful"}))
                self.assertEqual(caught.exception.code, code)

    def test_an_error_that_quotes_the_key_never_reaches_the_caller(self) -> None:
        handler = refuse(401, {"detail": {"status": "invalid_api_key", "message": f"key {KEY} bad"}})
        with self.assertRaises(ExternalVoiceError) as caught:
            self._synth(handler)
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn(KEY, caught.exception.message)

    def test_a_network_that_never_arrived_says_so(self) -> None:
        def handler(request):
            raise urllib.error.URLError("nodename nor servname provided")

        with self.assertRaises(ExternalVoiceError) as caught:
            self._synth(handler)
        self.assertEqual(caught.exception.code, "network")


class CatalogueTests(unittest.TestCase):
    def test_it_reads_the_account_and_names_the_provider_in_the_label(self) -> None:
        seen = {}

        def handler(request):
            seen["url"] = request.full_url
            seen["headers"] = dict(request.headers)
            return FakeResponse(json.dumps(page(["Rachel", "Adam"])).encode())

        voices = ElevenLabsVoiceProvider(KEY, opener=handler).voices()
        self.assertIn("https://api.elevenlabs.io/v2/voices", seen["url"])
        self.assertIn("Xi-api-key", seen["headers"])
        self.assertEqual([voice.id for voice in voices], ["id-Rachel", "id-Adam"])
        self.assertEqual(voices[0].label, "Rachel · ElevenLabs")
        # The model rides along, because the id built from it carries the price.
        self.assertEqual(voices[0].model, "eleven_flash_v2_5")

    def test_it_follows_the_pages(self) -> None:
        pages = [page(["A"], token="t1", more=True), page(["B"], more=False)]
        asked: list[str] = []

        def handler(request):
            asked.append(request.full_url)
            return FakeResponse(json.dumps(pages[len(asked) - 1]).encode())

        voices = ElevenLabsVoiceProvider(KEY, opener=handler).voices()
        self.assertEqual([voice.id for voice in voices], ["id-A", "id-B"])
        self.assertIn("next_page_token=t1", asked[1])

    def test_a_huge_library_stops_rather_than_paging_forever(self) -> None:
        def handler(request):
            return FakeResponse(
                json.dumps(page([f"v{n}" for n in range(100)], token="t", more=True)).encode()
            )

        voices = ElevenLabsVoiceProvider(KEY, opener=handler).voices()
        self.assertEqual(len(voices), MAX_VOICES)

    def test_a_refused_key_surfaces_from_the_catalogue_too(self) -> None:
        handler = refuse(401, {"detail": {"status": "invalid_api_key", "message": "nope"}})
        with self.assertRaises(ExternalVoiceError) as caught:
            ElevenLabsVoiceProvider(KEY, opener=handler).voices()
        self.assertEqual(caught.exception.code, "bad_key")

    def test_a_reply_that_is_not_json_is_the_network_not_the_provider(self) -> None:
        def handler(request):
            return FakeResponse(b"<html>captive portal</html>")

        with self.assertRaises(ExternalVoiceError) as caught:
            ElevenLabsVoiceProvider(KEY, opener=handler).voices()
        self.assertEqual(caught.exception.code, "network")


class VerifyTests(unittest.TestCase):
    def test_elevenlabs_checks_the_key_by_listing_voices(self) -> None:
        asked: list[str] = []

        def handler(request):
            asked.append(request.full_url)
            return FakeResponse(json.dumps(page(["Rachel"])).encode())

        ElevenLabsVoiceProvider(KEY, opener=handler).verify()
        self.assertTrue(asked)

    def test_a_bad_key_is_refused_at_the_moment_it_is_typed(self) -> None:
        handler = refuse(401, {"detail": {"status": "invalid_api_key", "message": "nope"}})
        with self.assertRaises(ExternalVoiceError) as caught:
            ElevenLabsVoiceProvider(KEY, opener=handler).verify()
        self.assertEqual(caught.exception.code, "bad_key")


class OpenAIVerifyTests(unittest.TestCase):
    """The one that used to accept anything.

    `OpenAIVoiceProvider.voices()` is a constant, so the app's "we checked
    your key" was true of ElevenLabs and false of OpenAI - any non-empty
    string passed. These pin the real probe.
    """

    def _provider(self, handler):
        from vieneu_reader.speech.external.openai import OpenAIVoiceProvider

        return OpenAIVoiceProvider(KEY, opener=handler)

    def test_it_asks_the_service_rather_than_believing_the_string(self) -> None:
        asked: list[str] = []

        def handler(request):
            asked.append(request.full_url)
            return FakeResponse(b'{"data": []}')

        self._provider(handler).verify()
        self.assertEqual(asked, ["https://api.openai.com/v1/models"])

    def test_a_key_the_service_refuses_is_refused_here(self) -> None:
        handler = refuse(401, {"error": {"message": "Incorrect API key provided"}})
        with self.assertRaises(ExternalVoiceError) as caught:
            self._provider(handler).verify()
        self.assertEqual(caught.exception.code, "bad_key")

    def test_being_offline_is_not_the_same_as_a_bad_key(self) -> None:
        def handler(request):
            raise urllib.error.URLError("offline")

        with self.assertRaises(ExternalVoiceError) as caught:
            self._provider(handler).verify()
        self.assertEqual(caught.exception.code, "network")


if __name__ == "__main__":
    unittest.main()
