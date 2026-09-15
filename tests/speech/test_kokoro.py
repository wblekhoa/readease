"""The English engine, with the model, the tagger and the network faked.

The real model is 326 MB and downloaded on request; nothing here touches
it. What is tested is the contract the server and the shell depend on:
readiness is files plus a marker written only after every file matched its
pinned hash and a trial sentence produced audio; a removal takes the
marker with it; audio leaves at 48 kHz in short slices; a stop is honoured
between slices; and the labels read the way the Vietnamese ones do.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from vieneu_reader.speech import kokoro
from vieneu_reader.speech.kokoro import (
    EnglishModelError,
    EnglishModelNotReadyError,
    KokoroSpeechEngine,
    double_rate,
    split_phonemes,
)


class FakeSession:
    """Answers every window with one second of 24 kHz sine."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, _outputs, feeds):
        self.calls.append(feeds)
        samples = np.sin(np.linspace(0, 200, 24_000, dtype=np.float32))
        return [samples[None, :]]


def fake_g2p(text: str):
    """Phonemes are the letters: enough to exercise the vocabulary lookup."""
    return " ".join(word.lower() for word in text.split()), []


def _write(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


TOKENIZER = json.dumps({"model": {"vocab": {
    "$": 0, "ˈ": 1, **{letter: index + 2 for index, letter in enumerate("abcdefghijklmnopqrstuvwxyz .,")},
}}}).encode("utf-8")


def _payload(name: str) -> bytes:
    if name == kokoro.TOKENIZER_FILE:
        return TOKENIZER
    if name.startswith("voices/"):
        return np.zeros(510 * 256, dtype=np.float32).tobytes()
    if name.endswith(".json"):
        return b"{}"
    return b"onnx" * 64


class Fixture:
    """A fetcher that writes stand-ins, and the pins that match them.

    The pins in the engine are of the real files; the fakes write stand-ins,
    so a test points the tables at what they wrote."""

    def __init__(self, root: Path, *, corrupt: str | None = None):
        self.root = root
        self.corrupt = corrupt
        self.fetched: list[str] = []
        self.model_hashes: dict[str, str | None] = {
            name: (None if name == kokoro.TOKENIZER_FILE else hashlib.sha256(_payload(name)).hexdigest())
            for name in kokoro.MODEL_FILES
        }
        if corrupt:
            self.model_hashes[corrupt] = "0" * 64
        self.lexicon_pins = {
            name: hashlib.sha256(_payload(name)).hexdigest() for name in kokoro.LEXICON_FILES
        }

    def fetch(self, url: str, target: Path, expected, progress=None):
        assert url.startswith(("https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/",
                               "https://raw.githubusercontent.com/hexgrad/misaki/"))
        assert kokoro.MODEL_REVISION in url or kokoro.LEXICON_REVISION in url
        self.fetched.append(url.rsplit("/", 1)[-1])
        name = target.name if target.parent.name != "voices" else f"voices/{target.name}"
        if target.name == "model.onnx":
            name = kokoro.MODEL_ONNX
        _write(target, _payload(name))
        if progress is not None:
            progress(target.stat().st_size)
        if expected is not None and hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            target.unlink()
            raise kokoro.EnglishModelError(kokoro._mismatch_message(target.name))


class EnglishEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "Models"
        self.session = FakeSession()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _engine(self, fixture: Fixture) -> KokoroSpeechEngine:
        return KokoroSpeechEngine(
            self.root,
            file_fetcher=fixture.fetch,
            session_factory=lambda path: self.session,
            g2p_factory=lambda gold, silver: fake_g2p,
        )

    def _pinned(self, fixture: Fixture):
        return (
            mock.patch.dict(kokoro.MODEL_FILES, fixture.model_hashes),
            mock.patch.dict(kokoro.LEXICON_FILES, fixture.lexicon_pins),
        )

    def _prepared(self, fixture: Fixture | None = None) -> KokoroSpeechEngine:
        fixture = fixture or Fixture(self.root)
        engine = self._engine(fixture)
        models, lexicon = self._pinned(fixture)
        with models, lexicon:
            engine.prepare_model(lambda progress, message: None)
        return engine

    def test_not_ready_until_prepared_and_refuses_to_speak(self) -> None:
        engine = self._engine(Fixture(self.root))

        self.assertFalse(engine.is_model_ready)
        with self.assertRaises(EnglishModelNotReadyError):
            list(engine.stream("Hello there.", "af_heart"))

    def test_prepare_fetches_every_file_by_url_and_writes_the_marker_after_a_trial_sentence(self) -> None:
        fixture = Fixture(self.root)
        engine = self._engine(fixture)
        models, lexicon = self._pinned(fixture)
        with models, lexicon:
            engine.prepare_model(lambda progress, message: None)

        self.assertTrue(engine.is_model_ready)
        # Ten plain downloads: no Hub client, which the Vietnamese model
        # puts into offline mode for the whole process once it is ready.
        self.assertEqual(len(fixture.fetched), len(kokoro.MODEL_FILES) + len(kokoro.LEXICON_FILES))
        self.assertIn("model.onnx", fixture.fetched)
        self.assertIn("us_gold.json", fixture.fetched)
        marker = json.loads((self.root / ".kokoro-ready.json").read_text())
        self.assertEqual(marker["model_revision"], engine.model_revision)
        self.assertEqual(marker["lexicon_revision"], kokoro.LEXICON_REVISION)
        # The trial sentence ran through the model.
        self.assertGreaterEqual(len(self.session.calls), 1)

    def test_a_file_that_does_not_match_its_pin_leaves_no_marker(self) -> None:
        fixture = Fixture(self.root, corrupt="voices/af_heart.bin")
        engine = self._engine(fixture)
        models, lexicon = self._pinned(fixture)

        with models, lexicon:
            with self.assertRaises(EnglishModelError) as caught:
                engine.prepare_model(lambda progress, message: None)

        self.assertIn("không khớp", str(caught.exception))
        self.assertFalse((self.root / ".kokoro-ready.json").exists())
        self.assertFalse(engine.is_model_ready)

    def test_prepare_reports_progress_in_order_and_ends_ready(self) -> None:
        fixture = Fixture(self.root)
        engine = self._engine(fixture)
        seen: list[tuple[float, str]] = []
        models, lexicon = self._pinned(fixture)
        with models, lexicon:
            engine.prepare_model(lambda progress, message: seen.append((progress, message)))

        self.assertEqual([progress for progress, _ in seen], sorted(progress for progress, _ in seen))
        self.assertEqual(seen[0][0], 0.0)
        self.assertEqual(seen[-1], (1.0, "Giọng đọc tiếng Anh đã sẵn sàng."))
        self.assertIn("330 MB", seen[0][1])
        # Every file reported as it landed, so a cancel can land between them.
        self.assertGreater(len(seen), len(kokoro.MODEL_FILES) + len(kokoro.LEXICON_FILES))

    def test_a_prepared_model_is_not_downloaded_again(self) -> None:
        fixture = Fixture(self.root)
        engine = self._prepared(fixture)
        fixture.fetched.clear()

        engine.prepare_model(lambda progress, message: None)

        self.assertEqual(fixture.fetched, [])

    def test_a_whole_file_left_by_an_earlier_attempt_is_kept(self) -> None:
        fixture = Fixture(self.root)
        engine = self._engine(fixture)
        # The earlier attempt got the model and one voice down.
        for name in (kokoro.MODEL_ONNX, "voices/af_heart.bin"):
            _write(self.root / kokoro.MODEL_DIRECTORY / name, _payload(name))
        models, lexicon = self._pinned(fixture)
        with models, lexicon:
            engine.prepare_model(lambda progress, message: None)

        self.assertTrue(engine.is_model_ready)
        self.assertNotIn("model.onnx", fixture.fetched)
        self.assertNotIn("af_heart.bin", fixture.fetched)
        self.assertIn("af_bella.bin", fixture.fetched)

    def test_a_cancel_raised_from_progress_leaves_no_marker_and_no_temp_file(self) -> None:
        class Cancelled(BaseException):
            pass

        fixture = Fixture(self.root)
        engine = self._engine(fixture)
        calls = 0

        def report(progress: float, message: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise Cancelled()

        models, lexicon = self._pinned(fixture)
        with models, lexicon:
            with self.assertRaises(Cancelled):
                engine.prepare_model(report)

        self.assertFalse(engine.is_model_ready)
        self.assertFalse((self.root / ".kokoro-ready.json").exists())
        self.assertEqual(list(self.root.rglob(".download-*")), [])

    def test_audio_is_48k_float32_in_short_slices(self) -> None:
        engine = self._prepared()

        chunks = list(engine.stream("Hello there.", "af_heart"))

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.sample_rate == 48_000 for chunk in chunks))
        samples = sum(len(chunk.pcm) // 4 for chunk in chunks)
        # One second at 24 kHz, doubled.
        self.assertEqual(samples, 48_000)
        longest = max(len(chunk.pcm) // 4 for chunk in chunks)
        self.assertLessEqual(longest, int(48_000 * kokoro.SLICE_SECONDS))
        feeds = self.session.calls[-1]
        self.assertEqual(feeds["input_ids"][0][0], 0)
        self.assertEqual(feeds["input_ids"][0][-1], 0)
        self.assertEqual(feeds["style"].shape, (1, 256))

    def test_a_stop_ends_the_stream_between_slices(self) -> None:
        engine = self._prepared()
        stream = engine.stream("Hello there.", "af_heart")
        first = next(stream)

        engine.cancel()

        self.assertTrue(first.pcm)
        self.assertEqual(list(stream), [])

    def test_an_unknown_voice_is_refused_by_name(self) -> None:
        engine = self._prepared()

        with self.assertRaises(ValueError):
            list(engine.stream("Hello there.", "adam"))

    def test_remove_takes_the_files_and_the_marker(self) -> None:
        engine = self._prepared()
        self.assertGreater(engine.installed_size(), 0)

        self.assertTrue(engine.remove())

        self.assertFalse(engine.is_model_ready)
        self.assertEqual(engine.installed_size(), 0)
        self.assertFalse((self.root / ".kokoro-ready.json").exists())
        self.assertFalse(engine.remove())

    def test_voices_carry_the_house_label_shape_and_a_gender(self) -> None:
        engine = self._engine(Fixture(self.root))

        labels = [voice.label for voice in engine.voices()]

        self.assertIn("Heart — Nữ · Mỹ", labels)
        self.assertIn("Michael — Nam · Mỹ", labels)
        self.assertEqual(engine.gender_of("af_heart"), "female")
        self.assertEqual(engine.gender_of("am_puck"), "male")
        self.assertIsNone(engine.gender_of("adam"))
        # The ids can never collide with a paid voice's `provider:model:voice`.
        self.assertTrue(all(":" not in voice.id for voice in engine.voices()))

    def test_the_cache_key_parts_differ_from_the_vietnamese_model(self) -> None:
        engine = self._engine(Fixture(self.root))
        from vieneu_reader.speech import vieneu

        self.assertNotEqual(engine.engine_version, vieneu.ENGINE_VERSION)
        self.assertNotIn(vieneu.MODEL_REVISION, engine.model_revision)


class HelperTests(unittest.TestCase):
    def test_double_rate_interleaves_midpoints_and_holds_the_last_sample(self) -> None:
        doubled = double_rate(np.array([0.0, 1.0, 0.0], dtype=np.float32))

        np.testing.assert_array_equal(doubled, [0.0, 0.5, 1.0, 0.5, 0.0, 0.0])
        self.assertEqual(double_rate(np.array([], dtype=np.float32)).size, 0)
        self.assertEqual(doubled.dtype, np.float32)

    def test_split_phonemes_cuts_at_spaces_inside_the_window(self) -> None:
        pieces = split_phonemes("aaa bbb ccc ddd", limit=7)

        self.assertEqual(pieces, ["aaa bbb", "ccc ddd"])
        self.assertEqual(split_phonemes("", limit=7), [])
        self.assertEqual(split_phonemes("short", limit=508), ["short"])

    def test_a_word_longer_than_the_window_is_cut_rather_than_dropped(self) -> None:
        pieces = split_phonemes("a" * 10, limit=4)

        self.assertEqual(pieces, ["aaaa", "aaaa", "aa"])
