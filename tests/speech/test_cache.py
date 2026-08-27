from pathlib import Path
from contextlib import contextmanager
import os
import struct
from tempfile import TemporaryDirectory
from threading import Event, Thread
import unittest
from unittest.mock import patch

from vieneu_reader.domain.models import AudioChunk
from vieneu_reader.speech.cache import AudioCache, audio_cache_key
from vieneu_reader.speech.contracts import SynthesisSettings


class AudioCacheKeyTests(unittest.TestCase):
    def test_equivalent_whitespace_has_the_same_cache_key(self):
        settings = SynthesisSettings()

        first = audio_cache_key("Xin   chào", "Adam", "3.3.0", "revision", settings)
        second = audio_cache_key(" Xin chào\n", "Adam", "3.3.0", "revision", settings)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_synthesis_inputs_each_invalidate_the_cache_key(self):
        base = audio_cache_key(
            "Xin chào",
            "Adam",
            "3.3.0",
            "revision-a",
            SynthesisSettings(),
        )
        variants = {
            audio_cache_key("Tạm biệt", "Adam", "3.3.0", "revision-a", SynthesisSettings()),
            audio_cache_key("Xin chào", "Trúc Ly", "3.3.0", "revision-a", SynthesisSettings()),
            audio_cache_key("Xin chào", "Adam", "3.3.1", "revision-a", SynthesisSettings()),
            audio_cache_key("Xin chào", "Adam", "3.3.0", "revision-b", SynthesisSettings()),
            audio_cache_key(
                "Xin chào",
                "Adam",
                "3.3.0",
                "revision-a",
                SynthesisSettings(temperature=0.7),
            ),
        }

        self.assertEqual(len(variants), 5)
        self.assertNotIn(base, variants)


class AudioCacheStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.cache = AudioCache(self.root)
        self.key = "a" * 64

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_complete_chunks_round_trip_as_one_audio_chunk(self):
        first = AudioChunk(struct.pack("<2f", 0.1, -0.1))
        second = AudioChunk(struct.pack("<2f", 0.2, -0.2))

        self.cache.put_complete(self.key, (first, second))
        cached = self.cache.get(self.key)

        self.assertIsNotNone(cached)
        self.assertEqual(cached.pcm, first.pcm + second.pcm)
        self.assertEqual(cached.sample_rate, 48_000)
        self.assertEqual((self.root / f"{self.key}.f32").stat().st_mode & 0o077, 0)

    def test_failed_stream_never_promotes_a_partial_cache_file(self):
        def broken_stream():
            yield AudioChunk(struct.pack("<f", 0.1))
            raise RuntimeError("generation failed")

        with self.assertRaisesRegex(RuntimeError, "generation failed"):
            self.cache.put_complete(self.key, broken_stream())

        self.assertIsNone(self.cache.get(self.key))
        self.assertEqual(list(self.root.glob("*.part")), [])

    def test_empty_or_incompatible_audio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            self.cache.put_complete(self.key, ())
        with self.assertRaisesRegex(ValueError, "48 kHz"):
            self.cache.put_complete(
                self.key,
                (AudioChunk(struct.pack("<f", 0.1), sample_rate=24_000),),
            )

    def test_cache_key_cannot_escape_the_cache_directory(self):
        with self.assertRaisesRegex(ValueError, "cache key"):
            self.cache.get("../outside")

    def test_quota_evicts_the_oldest_complete_segment(self):
        bounded = AudioCache(self.root, max_bytes=12)
        older_key = "b" * 64
        newer_key = "c" * 64
        bounded.put_complete(
            older_key,
            (AudioChunk(struct.pack("<2f", 0.1, -0.1)),),
        )
        older_path = self.root / f"{older_key}.f32"
        os.utime(older_path, (1, 1))

        bounded.put_complete(
            newer_key,
            (AudioChunk(struct.pack("<2f", 0.2, -0.2)),),
        )

        self.assertIsNone(bounded.get(older_key))
        self.assertIsNotNone(bounded.get(newer_key))

    def test_quota_stops_consuming_stream_before_the_next_oversized_write(self):
        bounded = AudioCache(self.root, max_bytes=8)
        consumed = 0

        def unbounded_stream():
            nonlocal consumed
            for _ in range(10_000):
                consumed += 1
                yield AudioChunk(struct.pack("<f", 0.1))

        with self.assertRaisesRegex(ValueError, "quota"):
            bounded.put_complete(self.key, unbounded_stream())

        self.assertEqual(consumed, 3)
        self.assertEqual(list(self.root.glob("*.part")), [])
        self.assertIsNone(bounded.get(self.key))

    def test_reopen_scavenges_only_exact_owned_regular_cache_scratch(self):
        stale = self.root / f".{self.key}-abcdefgh.part"
        unrelated = self.root / f".{self.key}-short.part"
        directory = self.root / f".{self.key}-ijklmnop.part"
        external = self.root / "outside.part"
        symlink = self.root / f".{self.key}-qrstuvwx.part"
        stale.write_bytes(b"stale")
        unrelated.write_bytes(b"unrelated")
        directory.mkdir()
        external.write_bytes(b"external")
        symlink.symlink_to(external)

        AudioCache(self.root, max_bytes=8)

        self.assertFalse(stale.exists())
        self.assertTrue(unrelated.is_file())
        self.assertTrue(directory.is_dir())
        self.assertTrue(symlink.is_symlink())
        self.assertEqual(external.read_bytes(), b"external")

    def test_cache_instances_serialize_active_temporary_writers(self):
        first_cache = AudioCache(self.root, max_bytes=16)
        second_cache = AudioCache(self.root, max_bytes=16)
        first_waiting = Event()
        release_first = Event()
        second_consumed = Event()
        errors = []

        def first_stream():
            yield AudioChunk(struct.pack("<f", 0.1))
            first_waiting.set()
            if not release_first.wait(timeout=2):
                raise RuntimeError("test timed out releasing first cache writer")
            yield AudioChunk(struct.pack("<f", 0.2))

        def second_stream():
            second_consumed.set()
            yield AudioChunk(struct.pack("<f", 0.3))

        def write(cache, key, chunks):
            try:
                cache.put_complete(key, chunks)
            except Exception as error:
                errors.append(error)

        first = Thread(target=write, args=(first_cache, "b" * 64, first_stream()))
        second = Thread(target=write, args=(second_cache, "c" * 64, second_stream()))
        first.start()
        self.assertTrue(first_waiting.wait(timeout=1))
        second.start()
        overlapped = second_consumed.wait(timeout=0.1)
        release_first.set()
        first.join(timeout=3)
        second.join(timeout=3)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertFalse(overlapped)
        self.assertEqual(errors, [])
        self.assertIsNotNone(first_cache.get("b" * 64))
        self.assertIsNotNone(second_cache.get("c" * 64))

    def test_get_rejects_oversized_complete_file_before_reading_it(self):
        bounded = AudioCache(self.root, max_bytes=8)
        oversized = self.root / f"{self.key}.f32"
        oversized.write_bytes(b"\x00" * 12)

        with patch.object(
            Path,
            "read_bytes",
            side_effect=AssertionError("oversized cache file was materialized"),
        ):
            cached = bounded.get(self.key)

        self.assertIsNone(cached)

    def test_eviction_failure_aborts_before_promoting_the_new_segment(self):
        bounded = AudioCache(self.root, max_bytes=8)
        older_key = "b" * 64
        newer_key = "c" * 64
        bounded.put_complete(
            older_key,
            (AudioChunk(struct.pack("<2f", 0.1, -0.1)),),
        )
        older_path = self.root / f"{older_key}.f32"
        newer_path = self.root / f"{newer_key}.f32"
        real_unlink = Path.unlink

        def fail_oldest_eviction(path, *args, **kwargs):
            if path == older_path:
                raise OSError("simulated eviction failure")
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", new=fail_oldest_eviction):
            with self.assertRaisesRegex(OSError, "eviction"):
                bounded.put_complete(
                    newer_key,
                    (AudioChunk(struct.pack("<2f", 0.2, -0.2)),),
                )

        self.assertTrue(older_path.is_file())
        self.assertFalse(newer_path.exists())
        self.assertEqual(list(self.root.glob("*.part")), [])

    def test_commit_guard_can_abort_atomic_promotion(self):
        @contextmanager
        def reject_stale_generation():
            raise RuntimeError("stale generation")
            yield

        with self.assertRaisesRegex(RuntimeError, "stale"):
            self.cache.put_complete(
                self.key,
                (AudioChunk(struct.pack("<f", 0.1)),),
                commit_guard=reject_stale_generation,
            )

        self.assertIsNone(self.cache.get(self.key))
        self.assertEqual(list(self.root.glob("*.part")), [])


if __name__ == "__main__":
    unittest.main()
