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
        # Both models are offered, because they are different prices.
        self.assertEqual(
            {voice["model"] for voice in paid}, {"tts-1", "tts-1-hd"},
        )

    def test_the_other_provider_stays_out_until_it_has_its_own_key(self) -> None:
        voices = self._voices({"openai_api_key": KEY})
        self.assertFalse(any(v["id"].startswith("elevenlabs") for v in voices))


if __name__ == "__main__":
    unittest.main()
