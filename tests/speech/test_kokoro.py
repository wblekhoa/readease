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


class Fixture:
    """A models folder the fakes fill, and the pinned hashes to match it."""

    def __init__(self, root: Path, *, corrupt: str | None = None):
        self.root = root
        self.model_hashes: dict[str, str | None] = {}
        self.lexicon_hashes: dict[str, str] = {}
        self.corrupt = corrupt

    def download(self, **kwargs):
        model_root = Path(kwargs["local_dir"])
        for name in kokoro.MODEL_FILES:
            if name == kokoro.TOKENIZER_FILE:
                _write(model_root / name, TOKENIZER)
                self.model_hashes[name] = None
                continue
            payload = (
                np.zeros(510 * 256, dtype=np.float32).tobytes()
                if name.startswith("voices/")
                else b"onnx" * 64
            )
            self.model_hashes[name] = _write(model_root / name, payload)
            if name == self.corrupt:
                self.model_hashes[name] = "0" * 64
        return str(model_root)

    def fetch(self, url: str, target: Path, expected: str):
        assert url.startswith("https://raw.githubusercontent.com/hexgrad/misaki/")
        assert kokoro.LEXICON_REVISION in url
        self.lexicon_hashes[target.name] = _write(target, b"{}")

    def lexicon_pins(self) -> dict[str, str]:
        # The engine checks the fetched file against the pin it was given;
        # the fake fetcher hashes what it wrote, so the pins are those.
        return {name: hashlib.sha256(b"{}").hexdigest() for name in kokoro.LEXICON_FILES}


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
            model_downloader=fixture.download,
            file_fetcher=fixture.fetch,
            session_factory=lambda path: self.session,
            g2p_factory=lambda gold, silver: fake_g2p,
        )

    def _prepared(self, fixture: Fixture | None = None) -> KokoroSpeechEngine:
        fixture = fixture or Fixture(self.root)
        engine = self._engine(fixture)
        # The pins are of the real files; the fakes write stand-ins, so the
        # table is pointed at what they wrote.
        fixture.download(local_dir=str(self.root / kokoro.MODEL_DIRECTORY))
        with mock.patch.dict(kokoro.MODEL_FILES, fixture.model_hashes), \
                mock.patch.dict(kokoro.LEXICON_FILES, fixture.lexicon_pins()):
            engine.prepare_model(lambda progress, message: None)
        return engine

    def test_not_ready_until_prepared_and_refuses_to_speak(self) -> None:
        engine = self._engine(Fixture(self.root))

        self.assertFalse(engine.is_model_ready)
        with self.assertRaises(EnglishModelNotReadyError):
            list(engine.stream("Hello there.", "af_heart"))

    def test_prepare_writes_the_marker_after_a_trial_sentence(self) -> None:
        engine = self._prepared()

        self.assertTrue(engine.is_model_ready)
        marker = json.loads((self.root / ".kokoro-ready.json").read_text())
        self.assertEqual(marker["model_revision"], engine.model_revision)
        self.assertEqual(marker["lexicon_revision"], kokoro.LEXICON_REVISION)
        # The trial sentence ran through the model.
        self.assertGreaterEqual(len(self.session.calls), 1)

    def test_a_file_that_does_not_match_its_pin_leaves_no_marker(self) -> None:
        fixture = Fixture(self.root, corrupt="voices/af_heart.bin")
        engine = self._engine(fixture)
        fixture.download(local_dir=str(self.root / kokoro.MODEL_DIRECTORY))

        with mock.patch.dict(kokoro.MODEL_FILES, fixture.model_hashes), \
                mock.patch.dict(kokoro.LEXICON_FILES, fixture.lexicon_pins()):
            with self.assertRaises(EnglishModelError) as caught:
                engine.prepare_model(lambda progress, message: None)

        self.assertIn("không khớp", str(caught.exception))
        self.assertFalse((self.root / ".kokoro-ready.json").exists())
        self.assertFalse(engine.is_model_ready)

    def test_prepare_reports_progress_in_order_and_ends_ready(self) -> None:
        fixture = Fixture(self.root)
        engine = self._engine(fixture)
        fixture.download(local_dir=str(self.root / kokoro.MODEL_DIRECTORY))
        seen: list[tuple[float, str]] = []
        with mock.patch.dict(kokoro.MODEL_FILES, fixture.model_hashes), \
                mock.patch.dict(kokoro.LEXICON_FILES, fixture.lexicon_pins()):
            engine.prepare_model(lambda progress, message: seen.append((progress, message)))

        self.assertEqual([progress for progress, _ in seen], sorted(progress for progress, _ in seen))
        self.assertEqual(seen[0][0], 0.0)
        self.assertEqual(seen[-1], (1.0, "Giọng đọc tiếng Anh đã sẵn sàng."))
        self.assertIn("330 MB", seen[0][1])

    def test_a_prepared_model_is_not_downloaded_again(self) -> None:
        engine = self._prepared()
        downloads: list[dict] = []
        engine._model_downloader = lambda **kwargs: downloads.append(kwargs)  # type: ignore[assignment]

        engine.prepare_model(lambda progress, message: None)

        self.assertEqual(downloads, [])

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
