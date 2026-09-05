"""What a paid reading may spend, and where it must stop.

No provider is contacted anywhere here: a fake one stands in, so the scope
ceiling, the budget, the spend meter and the named refusals are all proved
without a key.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from vieneu_reader.speech.external.provider import ExternalVoiceError, ProviderVoice  # noqa: E402

KEY = "sk-proj-0123456789abcdefghijklmnopqrstuvwxyz"

VOICE = "openai:tts-1:alloy"


class FakeProvider:
    """Counts what it was asked to say, and can refuse on cue."""

    asked: list[str] = []

    def __init__(self, key: str, model: str = "tts-1", fail: ExternalVoiceError | None = None):
        self._model = model
        self._fail = fail

    name = "openai"

    @property
    def model(self) -> str:
        return self._model

    def voices(self):
        return (ProviderVoice(id="alloy", label="Alloy", model=self._model),)

    def synthesize(self, text, voice_id):
        FakeProvider.asked.append(text)
        if self._fail is not None:
            raise self._fail
        yield np.array([0, 1000, -1000, 0] * 20, dtype="<i2").tobytes()

    def cancel(self) -> None:
        pass


def _book(chapters=3, per_chapter=2):
    """Three chapters of two paragraphs, built the way the importers do."""

    from tests.headless.test_server import build_book

    return build_book([
        (f"Chương {index}", [
            (f"Câu {index}-{position}. " + "Chữ " * 12, "paragraph")
            for position in range(per_chapter)
        ])
        for index in range(chapters)
    ])


def _first_segment(book, chapter=0, position=0):
    return book.chapters[chapter].segments[position].id


_BOOK = _book()


class PaidReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeProvider.asked = []
        self._patched = []

    def tearDown(self) -> None:
        for module, name, original in self._patched:
            setattr(module, name, original)

    def _patch_provider(self, **kwargs):
        from vieneu_reader.headless import server

        original = server._external_provider
        self._patched.append((server, "_external_provider", original))

        def factory(provider, voice_id, settings):
            if provider != "openai" or not settings.get("openai_api_key"):
                return None
            return FakeProvider(str(settings["openai_api_key"]), **kwargs)

        server._external_provider = factory

    def _session(self, directory: Path, settings: dict):
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService
        from vieneu_reader.storage.repository import LibraryRepository

        path = directory / "settings.json"
        path.write_text(json.dumps(settings), encoding="utf-8")
        repository = LibraryRepository(directory / "reader.sqlite3")
        source = directory / "book.epub"
        source.write_bytes(b"fixture")
        repository.add_book(_BOOK, source)
        service = LibraryService(AppPaths.create(directory / "app"), repository)
        return repository, service, path

    def _run(self, requests, directory, settings):
        from tests.headless.test_server import FakeEngine, run_server

        repository, service, path = self._session(Path(directory), settings)
        return run_server(requests, FakeEngine(), repository=repository,
                          service=service, settings_path=path)

    def test_a_scope_of_one_chapter_never_sends_the_next_one(self) -> None:
        self._patch_provider()
        with TemporaryDirectory() as directory:
            replies = self._run([{
                "id": 1, "method": "read.book",
                "params": {"book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
                           "voice_id": VOICE, "rate": 1.0, "chapters": 1},
            }], directory, {"openai_api_key": KEY})
            self.assertTrue(replies[-1]["ok"], replies[-1])
            said = " ".join(FakeProvider.asked)
            self.assertIn("Câu 0-0", said)
            self.assertIn("Câu 0-1", said)
            # The ceiling is the point: chapter two was never sent, so it was
            # never charged for.
            self.assertNotIn("Câu 1-", said)

    def test_the_whole_book_is_still_the_default(self) -> None:
        self._patch_provider()
        with TemporaryDirectory() as directory:
            self._run([{
                "id": 1, "method": "read.book",
                "params": {"book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
                           "voice_id": VOICE, "rate": 1.0},
            }], directory, {"openai_api_key": KEY})
            said = " ".join(FakeProvider.asked)
            self.assertIn("Câu 2-1", said)

    def test_a_paid_voice_with_no_key_is_refused_by_name(self) -> None:
        # NOT silently answered by the local model: hearing a voice you did
        # not choose, with no reason given, is the worse outcome.
        self._patch_provider()
        with TemporaryDirectory() as directory:
            replies = self._run([{
                "id": 1, "method": "read.book",
                "params": {"book_id": _BOOK.id, "voice_id": VOICE, "rate": 1.0},
            }], directory, {})
            self.assertFalse(replies[-1]["ok"])
            self.assertIn("no_key", replies[-1]["error"])
            self.assertEqual(FakeProvider.asked, [])

    def test_the_budget_stops_it_before_the_characters_leave(self) -> None:
        self._patch_provider()
        with TemporaryDirectory() as directory:
            replies = self._run([{
                "id": 1, "method": "read.book",
                "params": {"book_id": _BOOK.id, "voice_id": VOICE, "rate": 1.0},
            }], directory, {"openai_api_key": KEY, "external_voice_budget": 0.000001})
            self.assertFalse(replies[-1]["ok"])
            self.assertIn("budget", replies[-1]["error"])
            self.assertEqual(FakeProvider.asked, [])

    def test_it_says_what_it_has_spent_as_it_goes(self) -> None:
        self._patch_provider()
        with TemporaryDirectory() as directory:
            replies = self._run([{
                "id": 1, "method": "read.book",
                "params": {"book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
                           "voice_id": VOICE, "rate": 1.0, "chapters": 1},
            }], directory, {"openai_api_key": KEY})
            spend = [r for r in replies if r.get("event") == "spend"]
            self.assertTrue(spend)
            self.assertGreater(spend[-1]["chars"], 0)
            self.assertGreater(spend[-1]["usd"], 0)
            # Running totals, so the last one is the session's figure.
            self.assertEqual(spend[-1]["chars"], max(s["chars"] for s in spend))

    def test_a_refusal_from_the_provider_keeps_its_name(self) -> None:
        self._patch_provider(fail=ExternalVoiceError("quota", "out of credit"))
        with TemporaryDirectory() as directory:
            replies = self._run([{
                "id": 1, "method": "read.book",
                "params": {"book_id": _BOOK.id, "voice_id": VOICE, "rate": 1.0},
            }], directory, {"openai_api_key": KEY})
            self.assertFalse(replies[-1]["ok"])
            self.assertIn("quota", replies[-1]["error"])

    def test_a_local_voice_is_untouched_by_any_of_this(self) -> None:
        self._patch_provider()
        with TemporaryDirectory() as directory:
            replies = self._run([{
                "id": 1, "method": "read.book",
                "params": {"book_id": _BOOK.id, "voice_id": "Minh Đức", "rate": 1.0},
            }], directory, {"openai_api_key": KEY})
            self.assertTrue(replies[-1]["ok"])
            self.assertEqual(FakeProvider.asked, [])
            self.assertEqual([r for r in replies if r.get("event") == "spend"], [])


class EstimateMethodTests(unittest.TestCase):
    def _run(self, params, settings=None):
        from tests.headless.test_server import FakeEngine, run_server
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService
        from vieneu_reader.storage.repository import LibraryRepository

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(_BOOK, source)
            service = LibraryService(AppPaths.create(root / "app"), repository)
            path = root / "settings.json"
            path.write_text(json.dumps(settings or {}), encoding="utf-8")
            return run_server(
                [{"id": 1, "method": "estimate", "params": params}],
                FakeEngine(), repository=repository, service=service,
                settings_path=path,
            )[0]

    def test_it_prices_a_scope_without_asking_anybody(self) -> None:
        reply = self._run({
            "book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
            "voice_id": VOICE, "chapters": 1,
        })
        self.assertTrue(reply["ok"])
        result = reply["result"]
        self.assertTrue(result["paid"])
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["chapters"], 1)
        self.assertGreater(result["chars"], 0)
        self.assertGreater(result["usd"], 0)
        self.assertEqual(result["unit"], "characters")
        self.assertEqual(result["price_dated"], "2026-09-04")

    def test_the_number_counts_the_same_strings_the_reading_will_send(self) -> None:
        # The whole reason the utterance builder is shared. If the estimate
        # counted `segment.text` instead of what `speakable_text` produces,
        # the button would quote one number and the bill would be another.
        from vieneu_reader.domain.models import Segment
        from vieneu_reader.domain.prosody import speakable_text

        estimate = self._run({
            "book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
            "voice_id": VOICE, "chapters": 1,
        })["result"]
        book = _book()
        spoken = sum(
            len(speakable_text(segment.text, segment.kind))
            for segment in book.chapters[0].segments
        )
        self.assertEqual(estimate["chars"], spoken)

    def test_the_quote_covers_the_chapter_even_when_you_resume_at_its_end(self) -> None:
        # The whole point of the ceiling. Resuming at the LAST paragraph of a
        # chapter used to quote that paragraph alone - and then a click back
        # at the top of the same chapter, carrying the very same scope, spent
        # several times the figure the person had been shown.
        last = _BOOK.chapters[0].segments[-1].id
        first = _BOOK.chapters[0].segments[0].id
        at_end = self._run({"book_id": _BOOK.id, "segment_id": last,
                            "voice_id": VOICE, "chapters": 1})["result"]
        at_start = self._run({"book_id": _BOOK.id, "segment_id": first,
                              "voice_id": VOICE, "chapters": 1})["result"]
        self.assertEqual(at_end["chars"], at_start["chars"])
        self.assertEqual(at_end["usd"], at_start["usd"])
        self.assertEqual(at_end["chapters"], 1)

    def test_the_whole_book_scope_quotes_the_whole_book_from_anywhere(self) -> None:
        middle = _BOOK.chapters[1].segments[-1].id
        start = _BOOK.chapters[0].segments[0].id
        from_middle = self._run({"book_id": _BOOK.id, "segment_id": middle,
                                 "voice_id": VOICE})["result"]
        from_start = self._run({"book_id": _BOOK.id, "segment_id": start,
                                "voice_id": VOICE})["result"]
        self.assertEqual(from_middle["chars"], from_start["chars"])
        self.assertEqual(from_middle["chapters"], 3)

    def test_more_chapters_costs_more_and_all_costs_most(self) -> None:
        one = self._run({"book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
                         "voice_id": VOICE, "chapters": 1})["result"]
        two = self._run({"book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
                         "voice_id": VOICE, "chapters": 2})["result"]
        every = self._run({"book_id": _BOOK.id, "segment_id": _first_segment(_BOOK),
                           "voice_id": VOICE})["result"]
        self.assertLess(one["usd"], two["usd"])
        self.assertLess(two["usd"], every["usd"])
        self.assertEqual(every["chapters"], 3)

    def test_pasted_text_is_priced_too_and_counts_what_will_be_sent(self) -> None:
        # The case that needed it most: a paste can be 100,000 characters,
        # which is one press of a button and ten dollars on the dearer
        # voices, and this screen never had a number on it at all.
        from vieneu_reader.domain.prosody import speakable_text
        from vieneu_reader.headless.server import _text_utterances
        from vieneu_reader.speech.contracts import SynthesisSettings

        pasted = "Một đoạn văn để thử. " * 200
        result = self._run({"text": pasted, "voice_id": VOICE})["result"]
        self.assertTrue(result["paid"])
        self.assertEqual(result["chapters"], 0)
        self.assertGreater(result["usd"], 0)
        # Counted over the strings the READING sends, not the raw paste:
        # `speakable_text` rewrites on the way past, so counting the box
        # would quote a number the bill then disagrees with.
        expected = sum(
            len(utterance.text)
            for utterance in _text_utterances(pasted, SynthesisSettings())
        )
        self.assertEqual(result["chars"], expected)
        self.assertNotEqual(speakable_text(pasted), "")

    def test_a_local_voice_reading_pasted_text_is_free(self) -> None:
        result = self._run({"text": "Một câu.", "voice_id": "Minh Đức"})["result"]
        self.assertFalse(result["paid"])
        self.assertGreater(result["chars"], 0)
        self.assertNotIn("usd", result)

    def test_an_empty_paste_prices_at_nothing_rather_than_failing(self) -> None:
        # The shell asks while somebody is still typing.
        result = self._run({"text": "", "voice_id": VOICE})["result"]
        self.assertEqual(result["chars"], 0)
        self.assertEqual(result["usd"], 0)

    def test_the_local_voice_answers_free_rather_than_nothing(self) -> None:
        # The button waits on an answer either way; silence would leave it
        # disabled for ever.
        result = self._run({"book_id": _BOOK.id, "voice_id": "Minh Đức"})["result"]
        self.assertFalse(result["paid"])
        self.assertGreater(result["chars"], 0)
        self.assertNotIn("usd", result)


class CatalogueTests(unittest.TestCase):
    """A paid voice is offered only when it could actually speak."""

    def _voices(self, settings):
        from tests.headless.test_server import FakeEngine, run_server

        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps(settings), encoding="utf-8")
            reply = run_server(
                [{"id": 1, "method": "voices"}], FakeEngine(), settings_path=path,
            )[0]
            return reply["result"]["voices"]

    def _unreachable(self, settings):
        from tests.headless.test_server import FakeEngine, run_server

        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps(settings), encoding="utf-8")
            reply = run_server(
                [{"id": 1, "method": "voices"}], FakeEngine(), settings_path=path,
            )[0]
            return reply["result"].get("unreachable")

    def test_without_a_key_the_catalogue_is_the_local_model_alone(self) -> None:
        # Offering Alloy to somebody with no key would put the refusal AFTER
        # the choice: they pick it, press read, and are told no.
        voices = self._voices({})
        self.assertTrue(voices)
        self.assertTrue(all(voice["paid"] is False for voice in voices))

    def test_with_a_key_the_paid_voices_join_it_below(self) -> None:
        voices = self._voices({"openai_api_key": KEY})
        paid = [voice for voice in voices if voice["paid"]]
        self.assertTrue(paid)
        # The local model stays first: it is the product, the rest is an
        # option somebody went and switched on.
        self.assertFalse(voices[0]["paid"])
        self.assertTrue(all(voice["id"].startswith("openai:") for voice in paid))
        self.assertTrue(all(voice["id"].count(":") == 2 for voice in paid))
        # ONE model, not every model. The catalogue used to emit models x
        # voices - 18 rows for OpenAI alone, the same nine names twice at two
        # prices, which is a list nobody can scan and a choice nobody should
        # have to make nine times. The model is a setting; the id still
        # carries it, so the price is still readable off the id.
        self.assertEqual({voice["model"] for voice in paid}, {"tts-1"})

    def test_changing_the_model_changes_which_voices_are_offered(self) -> None:
        cheap = self._voices({"openai_api_key": KEY})
        dear = self._voices({"openai_api_key": KEY, "openai_model": "tts-1-hd"})
        self.assertEqual({voice["model"] for voice in dear if voice["paid"]}, {"tts-1-hd"})
        # Same voices, different price - so the ids differ in the middle and
        # nothing that keyed off the old id can silently be charged the new
        # rate.
        self.assertEqual(
            len([v for v in cheap if v["paid"]]), len([v for v in dear if v["paid"]])
        )
        self.assertNotEqual(
            {v["id"] for v in cheap if v["paid"]}, {v["id"] for v in dear if v["paid"]}
        )

    def test_a_model_this_build_does_not_know_falls_back_rather_than_asking_for_it(self) -> None:
        # A settings file edited by hand, or written by a later build that had
        # a model this one does not. Sending it anyway would be a request the
        # provider refuses AND a price this app cannot quote.
        voices = self._voices({"openai_api_key": KEY, "openai_model": "tts-9-imaginary"})
        self.assertEqual({v["model"] for v in voices if v["paid"]}, {"tts-1"})

    def test_the_other_provider_stays_out_until_it_has_its_own_key(self) -> None:
        voices = self._voices({"openai_api_key": KEY})
        self.assertFalse(any(v["id"].startswith("elevenlabs") for v in voices))

    def test_a_provider_that_cannot_be_reached_does_not_take_the_local_voices_with_it(self) -> None:
        """The one that would have been found in the field, not in a test.

        ElevenLabs' catalogue is a live authenticated call. Being on a train
        used to raise out of the middle of building this list, so `voices`
        failed entirely and the reader lost the LOCAL model too - the one
        thing that needs no network and was working perfectly.
        """

        from vieneu_reader.headless import server

        original = server._external_provider

        class Unreachable:
            name = "elevenlabs"
            model = "eleven_flash_v2_5"

            def voices(self):
                raise ExternalVoiceError("network", "offline")

            def synthesize(self, text, voice_id):  # pragma: no cover
                raise AssertionError("never asked")

            def cancel(self):
                pass

        server._external_provider = lambda provider, voice_id, settings: (
            Unreachable() if provider == "elevenlabs" else None
        )
        try:
            voices = self._voices({"elevenlabs_api_key": KEY})
        finally:
            server._external_provider = original

        local = [voice for voice in voices if not voice["paid"]]
        self.assertTrue(local, "the local model must survive a provider being unreachable")
        # Not smuggled into the list as a voice with no name, either - every
        # list in the app would have drawn that as an empty row.
        self.assertTrue(all(voice["label"] for voice in voices))
        self.assertFalse(any(voice["paid"] for voice in voices))

    def test_a_provider_that_cannot_be_reached_says_so_beside_the_list(self) -> None:
        """Reported, not swallowed. A provider that silently vanishes looks
        exactly like one that was never configured."""

        from vieneu_reader.headless import server

        original = server._external_provider

        class Unreachable:
            name = "elevenlabs"
            model = "eleven_flash_v2_5"

            def voices(self):
                raise ExternalVoiceError("quota", "no credit")

            def synthesize(self, text, voice_id):  # pragma: no cover
                raise AssertionError("never asked")

            def cancel(self):
                pass

        server._external_provider = lambda provider, voice_id, settings: (
            Unreachable() if provider == "elevenlabs" else None
        )
        try:
            reported = self._unreachable({"elevenlabs_api_key": KEY})
        finally:
            server._external_provider = original
        self.assertEqual(reported, [{"provider": "elevenlabs", "code": "quota"}])


class VerifyKeyTests(unittest.TestCase):
    """Saving a key and finding out whether it works are ONE act.

    The shell used to save, re-list the catalogue and take "a paid voice
    appeared" as proof. That is proof for a provider whose catalogue is a
    live authenticated call, and no proof at all for one whose voices are a
    constant - any non-empty string passed, and the app said it had checked.
    """

    def _ask(self, settings, params, *, verify_raises=None):
        from tests.headless.test_server import FakeEngine, run_server
        from vieneu_reader.headless import server

        class Probe:
            name = "openai"
            model = "tts-1"

            def voices(self):
                return ()

            def verify(self):
                if verify_raises is not None:
                    raise verify_raises

            def synthesize(self, text, voice_id):  # pragma: no cover
                raise AssertionError("never asked")

            def cancel(self):
                pass

        original = server._external_provider
        server._external_provider = lambda provider, voice_id, s: Probe()
        try:
            with TemporaryDirectory() as directory:
                path = Path(directory) / "settings.json"
                path.write_text(json.dumps(settings), encoding="utf-8")
                reply = run_server(
                    [{"id": 1, "method": "config.verify_key", "params": params}],
                    FakeEngine(),
                    settings_path=path,
                )[0]
                stored = json.loads(path.read_text(encoding="utf-8"))
                return reply, stored
        finally:
            server._external_provider = original

    def test_a_key_the_service_accepts_is_saved(self) -> None:
        reply, stored = self._ask({}, {"provider": "openai", "value": KEY})
        self.assertEqual(reply["result"], {"saved": True, "ok": True})
        self.assertEqual(stored["openai_api_key"], KEY)

    def test_a_key_the_service_refuses_is_NOT_saved(self) -> None:
        reply, stored = self._ask(
            {}, {"provider": "openai", "value": "wrong"},
            verify_raises=ExternalVoiceError("bad_key", "refused"),
        )
        self.assertEqual(reply["result"], {"saved": False, "ok": False, "code": "bad_key"})
        # Keeping it would leave the panel looking configured and fail again
        # later, at the worst possible moment.
        self.assertFalse(stored.get("openai_api_key"))

    def test_the_reason_travels_so_the_shell_can_say_which_failure_it_was(self) -> None:
        for code in ("bad_key", "quota", "network", "provider_down"):
            with self.subTest(code=code):
                reply, _ = self._ask(
                    {}, {"provider": "openai", "value": KEY},
                    verify_raises=ExternalVoiceError(code, "m"),
                )
                self.assertEqual(reply["result"]["code"], code)

    def test_being_offline_does_not_wipe_a_key_that_was_already_working(self) -> None:
        reply, stored = self._ask(
            {"openai_api_key": KEY}, {"provider": "openai", "value": KEY},
            verify_raises=ExternalVoiceError("network", "offline"),
        )
        self.assertFalse(reply["result"]["ok"])
        self.assertEqual(stored["openai_api_key"], KEY)

    def test_an_empty_value_clears_the_key_without_asking_anybody(self) -> None:
        reply, stored = self._ask({"openai_api_key": KEY}, {"provider": "openai", "value": ""})
        self.assertEqual(reply["result"]["code"], "no_key")
        self.assertFalse(stored.get("openai_api_key"))

    def test_the_key_never_comes_back_out(self) -> None:
        reply, _ = self._ask({}, {"provider": "openai", "value": KEY})
        self.assertNotIn(KEY, json.dumps(reply))


if __name__ == "__main__":
    unittest.main()


class CatalogueLanguageTests(unittest.TestCase):
    """The catalogue carries what a provider vouches for, and nothing more."""

    def _voices_with(self, provider_object):
        from tests.headless.test_server import FakeEngine, run_server
        from vieneu_reader.headless import server

        original = server._external_provider
        server._external_provider = lambda provider, voice_id, settings: (
            provider_object if provider == "elevenlabs" else None
        )
        try:
            with TemporaryDirectory() as directory:
                path = Path(directory) / "settings.json"
                path.write_text(json.dumps({"elevenlabs_api_key": KEY}), encoding="utf-8")
                reply = run_server(
                    [{"id": 1, "method": "voices"}], FakeEngine(), settings_path=path,
                )[0]
                return reply["result"]["voices"]
        finally:
            server._external_provider = original

    def test_verified_languages_reach_the_shell_as_a_plain_list(self) -> None:
        class Vouching:
            name = "elevenlabs"
            model = "eleven_flash_v2_5"

            def voices(self):
                return (
                    ProviderVoice(id="nhu", label="Nhu · ElevenLabs", model=self.model, languages=("vi", "en")),
                    ProviderVoice(id="rob", label="Rob · ElevenLabs", model=self.model),
                )

            def synthesize(self, text, voice_id):  # pragma: no cover
                raise AssertionError("never asked")

            def cancel(self):
                pass

        paid = [voice for voice in self._voices_with(Vouching()) if voice["paid"]]
        self.assertEqual([voice["languages"] for voice in paid], [["vi", "en"], []])
        # JSON-plain: the shell reads a list, not a tuple's repr.
        self.assertIsInstance(paid[0]["languages"], list)

    def test_the_local_model_carries_no_claim_either_way(self) -> None:
        # The local voices ARE Vietnamese, but the field is what a PROVIDER
        # verified; the shell knows the local model from `paid: False`.
        local = [voice for voice in self._voices_with(None) if not voice["paid"]]
        self.assertTrue(local)
        self.assertTrue(all("languages" not in voice for voice in local))

    def test_known_provider_gender_reaches_the_shell_without_inference(self) -> None:
        class Labelled:
            name = "elevenlabs"
            model = "eleven_flash_v2_5"

            def voices(self):
                return (
                    ProviderVoice(id="nhu", label="Nhu · ElevenLabs", model=self.model, gender="female"),
                    ProviderVoice(id="rob", label="Rob · ElevenLabs", model=self.model),
                )

            def synthesize(self, text, voice_id):  # pragma: no cover
                raise AssertionError("never asked")

            def cancel(self):
                pass

        paid = [voice for voice in self._voices_with(Labelled()) if voice["paid"]]
        self.assertEqual(paid[0]["gender"], "female")
        self.assertNotIn("gender", paid[1])
