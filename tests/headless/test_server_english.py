"""The second local model on the wire: listed only when it is on this Mac,
routed by the language it reads, and prepared or removed by name."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from vieneu_reader.domain.models import AudioChunk, Voice
from vieneu_reader.headless.server import serve
from vieneu_reader.speech.kokoro import VOICES


def _chunk() -> AudioChunk:
    return AudioChunk(pcm=np.full(480, 0.25, dtype=np.float32).tobytes())


class FakeVietnamese:
    engine_version = "fake-vi"
    model_revision = "vi-1"

    def __init__(self) -> None:
        self.requests: list[tuple[str, str]] = []

    def voices(self) -> tuple[Voice, ...]:
        return (Voice(id="adam", label="Adam — Nam · Bắc"),)

    def stream(self, text, voice_id, settings):
        self.requests.append((text, voice_id))
        yield _chunk()


class FakeEnglish:
    """Wears the English engine's face: ready or not, by the test's choice."""

    engine_version = "fake-en"
    model_revision = "en-1"

    def __init__(self, ready: bool = True, wraps_errors: bool = False) -> None:
        self.ready = ready
        self.wraps_errors = wraps_errors
        self.requests: list[tuple[str, str]] = []
        self.prepared = 0
        self.removed = 0

    @property
    def is_model_ready(self) -> bool:
        return self.ready

    def voices(self) -> tuple[Voice, ...]:
        return tuple(Voice(id=voice.id, label=voice.label) for voice in VOICES[:2])

    def gender_of(self, voice_id: str) -> str | None:
        return next((voice.gender for voice in VOICES if voice.id == voice_id), None)

    def installed_size(self) -> int:
        return 335_000_000 if self.ready else 0

    def prepare_model(self, report) -> None:
        self.prepared += 1
        try:
            for step in range(1, 5):
                report(step / 5, "Đang tải giọng đọc tiếng Anh…")
        except Exception as error:  # noqa: BLE001 - the real engine does this
            if self.wraps_errors:
                raise RuntimeError("Không thể tải giọng đọc tiếng Anh.") from error
            raise
        self.ready = True
        report(1.0, "Giọng đọc tiếng Anh đã sẵn sàng.")

    def remove(self) -> bool:
        self.removed += 1
        was = self.ready
        self.ready = False
        return was

    def warm(self) -> bool:
        return self.ready

    def stream(self, text, voice_id, settings):
        self.requests.append((text, voice_id))
        yield _chunk()


def run_server(requests, vietnamese, english, settings_path=None) -> list[dict]:
    reader = io.StringIO("".join(json.dumps(request) + "\n" for request in requests))
    writer = io.StringIO()
    serve(reader, writer, vietnamese, settings_path=settings_path, english_engine=english)
    return [json.loads(line) for line in writer.getvalue().splitlines()]


ENGLISH = "Reading is the art of listening with your eyes, and this paragraph came from a book."
VIETNAMESE = "Đọc sách là nghe bằng mắt, và đoạn này đến từ một cuốn sách tiếng Việt."


class EnglishVoicesOnTheWireTests(unittest.TestCase):
    def test_english_voices_are_listed_only_once_the_model_is_on_this_mac(self) -> None:
        absent = run_server([{"id": 1, "method": "voices"}], FakeVietnamese(), FakeEnglish(ready=False))
        present = run_server([{"id": 1, "method": "voices"}], FakeVietnamese(), FakeEnglish(ready=True))

        self.assertEqual([voice["id"] for voice in absent[0]["result"]["voices"]], ["adam"])
        listed = present[0]["result"]["voices"]
        self.assertEqual([voice["id"] for voice in listed], ["adam", "af_heart", "af_bella"])
        heart = listed[1]
        self.assertEqual(heart["languages"], ["en"])
        self.assertEqual(heart["gender"], "female")
        self.assertFalse(heart["paid"])
        self.assertEqual(heart["label"], "Heart — Nữ · Mỹ")
        # The Vietnamese voice keeps saying what it is.
        self.assertEqual(listed[0]["languages"], ["vi"])

    def _read(self, text: str, voice_id: str, english: FakeEnglish, language: str = "vi"):
        vietnamese = FakeVietnamese()
        with TemporaryDirectory() as directory:
            replies = run_server(
                [
                    {"id": 1, "method": "config.set",
                     "params": {"key": "ui_language", "value": language}},
                    {"id": 2, "method": "read", "params": {"text": text, "voice_id": voice_id}},
                ],
                vietnamese, english, settings_path=Path(directory) / "settings.json",
            )
        return replies[-1], vietnamese, english

    def test_an_english_passage_with_an_english_voice_is_read_by_the_english_model(self) -> None:
        reply, vietnamese, english = self._read(ENGLISH, "af_heart", FakeEnglish())

        self.assertTrue(reply["ok"], reply)
        self.assertEqual(vietnamese.requests, [])
        self.assertEqual(len(english.requests), 1)
        self.assertEqual(english.requests[0][1], "af_heart")

    def test_an_english_voice_refuses_vietnamese_by_name(self) -> None:
        reply, vietnamese, english = self._read(VIETNAMESE, "af_heart", FakeEnglish())

        self.assertFalse(reply["ok"])
        self.assertIn("voice_unavailable: wrong_language", reply["error"])
        self.assertEqual(english.requests, [])
        self.assertEqual(vietnamese.requests, [])

    def test_the_vietnamese_voice_still_refuses_english(self) -> None:
        reply, vietnamese, english = self._read(ENGLISH, "adam", FakeEnglish())

        self.assertFalse(reply["ok"])
        self.assertIn("wrong_language", reply["error"])
        self.assertEqual(english.requests, [])

    def test_an_english_voice_whose_model_is_gone_is_refused_as_missing(self) -> None:
        # A book, or settings, can remember the voice from before the
        # download was removed. Named, so the sentence can say where to go.
        reply, _, english = self._read(ENGLISH, "af_heart", FakeEnglish(ready=False))

        self.assertFalse(reply["ok"])
        self.assertIn("voice_unavailable: model_missing", reply["error"])
        self.assertEqual(english.requests, [])

    def test_without_an_english_engine_its_voice_ids_stay_local_and_refused(self) -> None:
        vietnamese = FakeVietnamese()
        with TemporaryDirectory() as directory:
            replies = run_server(
                [{"id": 2, "method": "read", "params": {"text": VIETNAMESE, "voice_id": "af_heart"}}],
                vietnamese, None, settings_path=Path(directory) / "settings.json",
            )
        # No English engine on this server: the id is a local voice the
        # Vietnamese model is asked for, exactly as before this existed.
        self.assertTrue(replies[-1]["ok"], replies[-1])
        self.assertEqual(vietnamese.requests[0][1], "af_heart")


class EnglishModelManagementTests(unittest.TestCase):
    def test_status_carries_the_english_block(self) -> None:
        replies = run_server([{"id": 1, "method": "model.status"}], FakeVietnamese(), FakeEnglish(ready=False))

        english = replies[0]["result"]["english"]
        self.assertEqual(english["ready"], False)
        self.assertEqual(english["installed"], 0)
        self.assertGreater(english["download_bytes"], 300_000_000)

    def test_status_without_an_english_engine_has_no_block(self) -> None:
        replies = run_server([{"id": 1, "method": "model.status"}], FakeVietnamese(), None)

        self.assertNotIn("english", replies[0]["result"])

    def test_prepare_by_name_streams_progress_and_ends_ready(self) -> None:
        english = FakeEnglish(ready=False)
        replies = run_server(
            [{"id": 7, "method": "model.prepare", "params": {"engine": "english"}}],
            FakeVietnamese(), english,
        )

        progress = [r for r in replies if r.get("event") == "model_progress"]
        self.assertGreaterEqual(len(progress), 4)
        self.assertTrue(all(r["id"] == 7 for r in progress))
        done = next(r for r in replies if r.get("id") == 7 and "ok" in r)
        self.assertEqual(done["result"], {"ready": True})
        self.assertEqual(english.prepared, 1)
        self.assertTrue(english.ready)
        # The shell re-lists on this: the new voices must not wait for a
        # relaunch to be offered.
        after = replies.index(done)
        self.assertIn({"event": "voices", "providers": ["local"]}, replies[after:])

    def test_prepare_without_a_name_still_means_the_vietnamese_model(self) -> None:
        english = FakeEnglish(ready=False)
        replies = run_server([{"id": 7, "method": "model.prepare"}], FakeVietnamese(), english)

        self.assertFalse(replies[-1]["ok"])
        self.assertEqual(english.prepared, 0)

    def test_remove_by_name(self) -> None:
        english = FakeEnglish(ready=True)
        replies = run_server(
            [{"id": 9, "method": "model.remove_build", "params": {"engine": "english"}},
             {"id": 10, "method": "voices"}],
            FakeVietnamese(), english,
        )

        self.assertEqual(replies[0]["result"], {"removed": True})
        self.assertEqual(english.removed, 1)
        self.assertIn({"event": "voices", "providers": ["local"]}, replies)
        listing = next(r for r in replies if r.get("id") == 10)
        self.assertEqual([voice["id"] for voice in listing["result"]["voices"]], ["adam"])

    def test_a_cancel_passes_through_an_engine_that_wraps_its_errors(self) -> None:
        # The real engines wrap whatever fails inside `prepare_model` into
        # their own "check the network" error. A cancel raised from the
        # progress callback used to be wrapped the same way and come back as
        # a failure; it is not an error, and it must not be caught as one.
        english = FakeEnglish(ready=False, wraps_errors=True)
        replies = run_server(
            [{"id": 70, "method": "model.prepare", "params": {"engine": "english"}},
             {"id": 71, "method": "stop"}],
            FakeVietnamese(), english,
        )

        done = next(r for r in replies if r.get("id") == 70 and "ok" in r)
        self.assertTrue(done["ok"], done)
        self.assertTrue(done["result"]["cancelled"])
        self.assertFalse(done["result"]["ready"])
        self.assertFalse(english.ready)
