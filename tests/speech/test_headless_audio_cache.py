"""A sentence already spoken is never bought twice - and never half-kept.

The cache existed (speech/cache.py, atomic + LRU) but only the Qt shell used
it; the headless server re-synthesised every re-read. That was merely slow
while the voice was a local model. It stops being merely slow the moment a
voice bills by the character.

**Every assertion here goes through `read.book`, never `read`.** The cache is
for readings OF A BOOK. Pasted text and text read from a selection must leave
nothing on disk (PRIVACY.md, "Data kept on the Mac"), and that promise has its
own receipts in `TransientReadingsLeaveNothingBehind` below. Testing the cache
through `read` is how the promise came to be broken without a test noticing:
the suite asserted the caching, so the caching of the wrong path looked right.

There is now ONE `read` that may be kept, and it is named rather than left to
be discovered: the voice-preview sample, which the shell marks `app_text`. It
is the app's own fixed sentence - the same words for every reader, written in
`i18n.ts` - so keeping it says nothing about anybody. `ThePreviewSampleIsThe
OneReadWorthKeeping` holds both halves: that the flag works, and that the
promise above is untouched by it.
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

SENTENCE = "Một câu."


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


class _CacheCase(unittest.TestCase):
    """A one-paragraph book on disk, so `read.book` has something to read."""

    def _library(self, root: Path, text: str = SENTENCE):
        from tests.headless.test_server import build_book
        from vieneu_reader.storage.repository import LibraryRepository

        repository = LibraryRepository(root / "reader.sqlite3")
        self.addCleanup(repository.close)
        book = build_book([("Một", [(text, "paragraph")])])
        source = root / "book.epub"
        source.write_bytes(b"fixture")
        repository.add_book(book, source)
        return repository

    def _run(self, engine, cache, requests, repository=None):
        from tests.headless.test_server import run_server

        return run_server(
            requests, engine, audio_cache=cache, repository=repository,
        )

    def _read_book(self, identifier: int, *, voice: str = "V", rate: float = 1.0):
        from tests.headless.test_server import BOOK_ID

        return {
            "id": identifier, "method": "read.book",
            "params": {"book_id": BOOK_ID, "voice_id": voice, "rate": rate},
        }

    def _kept(self, directory) -> list[Path]:
        return list(Path(directory).glob("*.f32"))


class HeadlessCacheTests(_CacheCase):
    def test_a_second_reading_of_the_same_text_asks_the_engine_nothing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cache = AudioCache(root / "Audio")
            repository = self._library(root)
            engine = CountingEngine()

            first = self._run(engine, cache, [self._read_book(1)], repository)
            self.assertTrue(first[-1]["ok"])
            asked_first = len(engine.calls)
            self.assertGreater(asked_first, 0)

            second = self._run(engine, cache, [self._read_book(2)], repository)
            self.assertTrue(second[-1]["ok"])
            # The seam itself is watched: not "it was fast", but "it never
            # asked".
            self.assertEqual(len(engine.calls), asked_first)

    def test_the_same_words_at_another_speed_reuse_what_was_bought(self) -> None:
        # The rate is applied on the way OUT, so 1.5x must not re-synthesise.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cache = AudioCache(root / "Audio")
            repository = self._library(root)
            engine = CountingEngine()

            self._run(engine, cache, [self._read_book(1, rate=1.0)], repository)
            asked = len(engine.calls)
            self._run(engine, cache, [self._read_book(2, rate=1.5)], repository)

            self.assertEqual(len(engine.calls), asked)

    def test_another_voice_is_another_purchase(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cache = AudioCache(root / "Audio")
            repository = self._library(root)
            engine = CountingEngine()

            for identifier, voice in enumerate(("V", "W"), start=1):
                self._run(
                    engine, cache, [self._read_book(identifier, voice=voice)],
                    repository,
                )

            self.assertEqual(len(engine.calls), 2)

    def test_a_reading_stopped_mid_sentence_keeps_nothing(self) -> None:
        # Half a sentence in the cache would be served as a whole one for
        # ever after - the reader would hear the text cut off and never know
        # why. Better to have bought it and kept nothing.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "Audio"
            cache = AudioCache(audio)
            repository = self._library(root, "Một câu dài.")
            engine = CountingEngine(chunks_per_sentence=6)

            # The stop rides in behind the read, which is how the shell's
            # own stop arrives: queued while the audio is streaming.
            self._run(engine, cache, [
                self._read_book(1),
                {"id": 2, "method": "stop"},
            ], repository)
            self.assertEqual(self._kept(audio), [])

            # And the next full reading does buy it, then keeps it.
            engine2 = CountingEngine()
            self._run(engine2, cache, [self._read_book(3)], repository)
            self.assertEqual(len(self._kept(audio)), 1)

    def test_an_engine_with_no_identity_is_never_cached_under_an_empty_name(self) -> None:
        # Two different stub engines must not collide in one cache.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "Audio"
            cache = AudioCache(audio)
            repository = self._library(root)

            class Anonymous(CountingEngine):
                engine_version = ""

            engine = Anonymous()
            for identifier in (1, 2):
                self._run(engine, cache, [self._read_book(identifier)], repository)

            self.assertEqual(self._kept(audio), [])
            self.assertEqual(len(engine.calls), 2)


class ThePreviewSampleIsTheOneReadWorthKeeping(_CacheCase):
    """Auditioning a paid voice twice must not be paid for twice.

    Every tap on a voice's preview was a fresh purchase: the sample goes down
    the `read` path, `read` never caches, so comparing five AI voices cost
    five charges and listening to one of them again cost another. The clip is
    the app's own sentence, identical for everyone, so there is nothing of the
    reader's in it to keep.

    The receipt is the number of times the ENGINE was asked, not the presence
    of a file: a file proves something was written, and what matters here is
    that the provider was not billed.
    """

    def _preview(self, identifier: int, *, voice: str = "V") -> dict:
        return {
            "id": identifier, "method": "read",
            "params": {
                "text": SENTENCE, "voice_id": voice, "rate": 1.0,
                "app_text": True,
            },
        }

    def test_the_second_audition_of_a_voice_asks_the_engine_nothing(self) -> None:
        with TemporaryDirectory() as directory:
            cache = AudioCache(Path(directory) / "Audio")
            engine = CountingEngine()

            first = self._run(engine, cache, [self._preview(1)])
            self.assertTrue(first[-1]["ok"])
            bought = len(engine.calls)
            self.assertGreater(bought, 0, "lần nghe thử đầu phải thật sự mua")

            second = self._run(engine, cache, [self._preview(2)])
            self.assertTrue(second[-1]["ok"])
            self.assertEqual(
                len(engine.calls), bought, "nghe thử lần hai vẫn bị tính tiền"
            )

    def test_each_voice_is_still_its_own_purchase(self) -> None:
        """The saving must not become a wrong answer: two voices saying the
        same sentence are two different clips, and the key already separates
        them. Without this, "cheaper" could mean "you heard the other one"."""

        with TemporaryDirectory() as directory:
            cache = AudioCache(Path(directory) / "Audio")
            engine = CountingEngine()

            self._run(engine, cache, [self._preview(1, voice="V")])
            bought = len(engine.calls)
            self._run(engine, cache, [self._preview(2, voice="W")])

            self.assertGreater(len(engine.calls), bought)

    def test_the_flag_is_the_shell_saying_whose_words_these_are(self) -> None:
        """The same text, the same voice, WITHOUT the claim: still transient.

        So the flag cannot be read as "cache this" - a reader's passage that
        happens to match the sample is still kept out. It is a statement about
        where the words came from, and only the preview makes it.
        """

        with TemporaryDirectory() as directory:
            audio = Path(directory) / "Audio"
            cache = AudioCache(audio)
            engine = CountingEngine()

            plain = {
                "id": 1, "method": "read",
                "params": {"text": SENTENCE, "voice_id": "V", "rate": 1.0},
            }
            self._run(engine, cache, [plain])

            self.assertEqual(self._kept(audio), [])


class TransientReadingsLeaveNothingBehind(_CacheCase):
    """F3 of the 05/09 product audit: what a pasted reading leaves on disk.

    PRIVACY.md, "Data kept on the Mac": *"Pasted text and text read from a
    selection are transient. They are not added to the library or persistent
    audio cache."* The Qt shell honoured that with an explicit `is_selection`
    gate (`playback/coordinator.py`, "if not is_selection"). The headless
    server - which is what the Tauri app runs - was given the cache later,
    for paid voices, and the gate did not come with it: every sentence of
    every `read` was written to `~/Library/Application Support/VieNeu
    Reader/Cache/Audio`, including text somebody selected out of their mail.

    A promise in a published document is a claim about behaviour, so it gets
    a test that reads the filesystem, not one that counts engine calls.
    """

    def _read(self, identifier: int, text: str = SENTENCE) -> dict:
        return {
            "id": identifier, "method": "read",
            "params": {"text": text, "voice_id": "V", "rate": 1.0},
        }

    def test_pasted_text_is_never_written_to_the_audio_cache(self) -> None:
        with TemporaryDirectory() as directory:
            audio = Path(directory) / "Audio"
            cache = AudioCache(audio)
            engine = CountingEngine()

            replies = self._run(engine, cache, [self._read(1)])

            self.assertTrue(replies[-1]["ok"])
            # It was spoken - this is not a read that quietly did nothing.
            self.assertEqual(engine.calls, [SENTENCE])
            self.assertEqual(self._kept(audio), [])

    def test_reading_the_same_pasted_text_again_still_writes_nothing(self) -> None:
        # The second pass is where a cache would show itself: it is the one
        # that would find an entry, touch its mtime for the LRU, and skip
        # the engine. Nothing of that may happen.
        with TemporaryDirectory() as directory:
            audio = Path(directory) / "Audio"
            cache = AudioCache(audio)
            engine = CountingEngine()

            self._run(engine, cache, [self._read(1)])
            self._run(engine, cache, [self._read(2)])

            self.assertEqual(self._kept(audio), [])
            self.assertEqual(engine.calls, [SENTENCE, SENTENCE])

    def test_a_book_reading_still_keeps_its_audio(self) -> None:
        # The other half of the promise: the cache is not switched off, it is
        # aimed. Without this, "leaves nothing" would pass on a broken cache.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "Audio"
            cache = AudioCache(audio)
            repository = self._library(root)
            engine = CountingEngine()

            replies = self._run(engine, cache, [self._read_book(1)], repository)

            self.assertTrue(replies[-1]["ok"])
            self.assertEqual(len(self._kept(audio)), 1)

    def test_the_same_words_pasted_never_reach_what_a_book_cached(self) -> None:
        # A sentence a book put in the cache must not be handed to a paste of
        # the same words: the lookup itself touches the entry's mtime, which
        # is a mark left on disk by a reading that promised to leave none.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "Audio"
            cache = AudioCache(audio)
            repository = self._library(root)
            engine = CountingEngine()

            self._run(engine, cache, [self._read_book(1)], repository)
            kept = self._kept(audio)
            self.assertEqual(len(kept), 1)
            stamped = kept[0].stat().st_mtime_ns

            engine2 = CountingEngine()
            self._run(engine2, cache, [self._read(2)])

            self.assertEqual(engine2.calls, [SENTENCE])
            self.assertEqual(self._kept(audio)[0].stat().st_mtime_ns, stamped)


if __name__ == "__main__":
    unittest.main()
