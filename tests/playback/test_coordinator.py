from collections.abc import Callable
from contextlib import contextmanager
import errno
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from threading import Event, RLock, Thread, current_thread
import unittest

from vieneu_reader.domain.models import AudioChunk
from vieneu_reader.playback.coordinator import PlaybackCoordinator, PlaybackState
from vieneu_reader.speech.cache import AudioCache
from vieneu_reader.speech.contracts import SynthesisSettings

from tests.domain.book_fixture import sample_book


class ManualScheduler:
    def __init__(self):
        self.tasks: list[Callable[[], None]] = []

    def submit(self, task: Callable[[], None]) -> None:
        self.tasks.append(task)

    def run_next(self) -> None:
        self.tasks.pop(0)()

    def run_all(self) -> None:
        while self.tasks:
            self.run_next()


class FakeSpeechEngine:
    engine_version = "test-engine"
    model_revision = "test-revision"

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.cancel_count = 0
        self.failure_text: str | None = None

    def voices(self):
        return ()

    def stream(self, text, voice_id, settings):
        self.calls.append((text, voice_id))
        if text == self.failure_text:
            raise RuntimeError("speech failed")
        marker = (sum(text.encode("utf-8")) % 50) / 100
        yield AudioChunk(struct.pack("<2f", marker, -marker))

    def cancel(self):
        self.cancel_count += 1


class FakeAudioOutput:
    def __init__(self):
        self.events = []
        self.on_drained: Callable[[], None] | None = None
        self.generation = 0
        self.lock = RLock()

    def begin(self, generation, rate, on_drained):
        with self.lock:
            if generation != self.generation:
                return
            self.events.append(("begin", rate))
            self.on_drained = on_drained

    def append(self, generation, chunk):
        with self.lock:
            if generation != self.generation:
                return
            self.events.append(("append", chunk.pcm))

    def end(self, generation):
        with self.lock:
            if generation == self.generation:
                self.events.append(("end",))

    def pause(self, generation):
        with self.lock:
            if generation == self.generation:
                self.events.append(("pause",))

    def resume(self, generation):
        with self.lock:
            if generation == self.generation:
                self.events.append(("resume",))

    def stop(self, generation):
        with self.lock:
            if generation < self.generation:
                return
            self.generation = generation
            self.events.append(("stop",))
            self.on_drained = None

    def set_rate(self, generation, rate):
        with self.lock:
            if generation == self.generation:
                self.events.append(("rate", rate))

    def complete(self):
        callback = self.on_drained
        self.on_drained = None
        if callback:
            callback()


class StopReleasedAudioOutput(FakeAudioOutput):
    def __init__(self):
        super().__init__()
        self.append_started = Event()
        self.release_append = Event()
        self.stop_count = 0

    def append(self, generation, chunk):
        self.append_started.set()
        if not self.release_append.wait(timeout=2):
            raise RuntimeError("test timed out waiting to release append")
        super().append(generation, chunk)

    def stop(self, generation):
        self.stop_count += 1
        super().stop(generation)
        if self.stop_count > 1:
            self.release_append.set()


class FakeProgressRepository:
    def __init__(self):
        self.saved = []
        self.failure: Exception | None = None

    def save_progress(self, progress):
        if self.failure is not None:
            raise self.failure
        self.saved.append(progress)


class LateFirstProgressRepository(FakeProgressRepository):
    def __init__(self):
        super().__init__()
        self.first_started = Event()
        self.release_first = Event()
        self.call_count = 0
        self.call_lock = RLock()

    def save_progress(self, progress):
        with self.call_lock:
            self.call_count += 1
            call = self.call_count
        if call == 1:
            self.first_started.set()
            if not self.release_first.wait(timeout=2):
                raise RuntimeError("test timed out waiting to release progress")
            self.saved.append(progress)
            return
        self.saved.append(progress)
        self.release_first.set()


class PromotionBarrierCache(AudioCache):
    def __init__(self, root):
        super().__init__(root)
        self.commit_started = Event()
        self.release_commit = Event()

    def put_complete(self, key, chunks, *, commit_guard=None):
        complete_chunks = tuple(chunks)
        self.commit_started.set()
        if not self.release_commit.wait(timeout=2):
            raise RuntimeError("test timed out waiting to release cache commit")
        if commit_guard is None:
            return super().put_complete(key, complete_chunks)
        return super().put_complete(
            key,
            complete_chunks,
            commit_guard=commit_guard,
        )


class ThreeChunkSpeechEngine(FakeSpeechEngine):
    def stream(self, text, voice_id, settings):
        self.calls.append((text, voice_id))
        for step in range(3):
            marker = (step + 1) / 10
            yield AudioChunk(struct.pack("<2f", marker, -marker))


class SilentSpeechEngine(FakeSpeechEngine):
    """Finishes without raising and without producing a single sample."""

    def stream(self, text, voice_id, settings):
        self.calls.append((text, voice_id))
        yield from ()


class FailingAfterAudioSpeechEngine(FakeSpeechEngine):
    """Delivers real audio and then fails part-way through the paragraph."""

    def stream(self, text, voice_id, settings):
        self.calls.append((text, voice_id))
        for step in range(2):
            marker = (step + 1) / 10
            yield AudioChunk(struct.pack("<2f", marker, -marker))
        raise RuntimeError("speech failed")


class DiskFullCache(AudioCache):
    """Fails the write the way a full disk does, at any point in the stream."""

    def __init__(self, root, *, consumed_chunks):
        super().__init__(root)
        self.consumed_chunks = consumed_chunks

    def put_complete(self, key, chunks, *, commit_guard=None):
        for _step, _chunk in zip(range(self.consumed_chunks), chunks):
            pass
        raise OSError(errno.ENOSPC, "No space left on device")


class BlockingPreferenceRepository:
    def __init__(self):
        self.first_started = Event()
        self.release_first = Event()
        self.current = None
        self.saved = []

    def save_progress(self, progress):
        self.first_started.set()
        if not self.release_first.wait(timeout=2):
            raise RuntimeError("test timed out waiting to release drained progress")
        self.current = progress
        self.saved.append(progress)

    def save_preferences(self, preferences):
        if self.current is None:
            self.current = preferences
        else:
            self.current = type(preferences)(
                book_id=self.current.book_id,
                segment_id=self.current.segment_id,
                playback_rate=preferences.playback_rate,
                voice_id=preferences.voice_id,
            )
        self.saved.append(self.current)
        self.release_first.set()


class BlockingGenerationAudioOutput(FakeAudioOutput):
    def __init__(self, blocked_generation):
        super().__init__()
        self.blocked_generation = blocked_generation
        self.stop_started = Event()
        self.release_stop = Event()

    def stop(self, generation):
        if generation == self.blocked_generation:
            self.stop_started.set()
            if not self.release_stop.wait(timeout=2):
                raise RuntimeError("test timed out releasing blocked stop")
        super().stop(generation)


class PauseBeforeInvalidateCoordinator(PlaybackCoordinator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.before_invalidate = Event()
        self.release_invalidate = Event()

    def _invalidate_output(self):
        if current_thread().name == "stale-next":
            self.before_invalidate.set()
            if not self.release_invalidate.wait(timeout=2):
                raise RuntimeError("test timed out releasing stale navigation")
        return super()._invalidate_output()


class PauseAfterProgressCoordinator(PlaybackCoordinator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.after_progress = Event()
        self.release_drain = Event()

    def _write_progress(self, token, index):
        super()._write_progress(token, index)
        if current_thread().name == "stale-drain":
            self.after_progress.set()
            if not self.release_drain.wait(timeout=2):
                raise RuntimeError("test timed out releasing stale drain")


class PlaybackCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.cache = AudioCache(Path(self.temp_dir.name) / "cache")
        self.engine = FakeSpeechEngine()
        self.output = FakeAudioOutput()
        self.progress = FakeProgressRepository()
        self.scheduler = ManualScheduler()
        self.coordinator = PlaybackCoordinator(
            engine=self.engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        self.book = sample_book("playback")
        self.first, self.second = self.book.chapters[0].segments

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_play_streams_current_segment_and_advances_after_audio_drains(self):
        self.coordinator.play(self.book, self.first.id, "Adam", rate=1.1)
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.LOADING)

        self.scheduler.run_next()

        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.PLAYING)
        self.assertEqual(self.engine.calls[0], (self.first.text, "Adam"))
        self.assertEqual(self.output.events[0], ("stop",))
        self.assertIn(("begin", 1.1), self.output.events)
        self.assertTrue(any(event[0] == "append" for event in self.output.events))

        self.output.complete()

        self.assertEqual(self.progress.saved[-1].segment_id, self.second.id)
        self.assertEqual(self.coordinator.snapshot.segment_id, self.second.id)
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.LOADING)

    def test_skip_invalidates_a_worker_that_has_not_started(self):
        self.coordinator.play(self.book, self.first.id, "Adam")
        self.coordinator.next()

        self.scheduler.run_all()

        self.assertNotIn((self.first.text, "Adam"), self.engine.calls)
        self.assertIn((self.second.text, "Adam"), self.engine.calls)
        self.assertEqual(self.coordinator.snapshot.segment_id, self.second.id)

    def test_previous_returns_to_the_prior_segment(self):
        self.coordinator.play(self.book, self.second.id, "Adam")
        self.scheduler.run_next()

        self.coordinator.previous()
        self.scheduler.run_all()

        self.assertIn((self.first.text, "Adam"), self.engine.calls)
        self.assertEqual(self.coordinator.snapshot.segment_id, self.first.id)

    def test_prefetch_populates_next_cache_without_playing_it(self):
        self.coordinator.play(self.book, self.first.id, "Adam")

        self.scheduler.run_next()
        self.assertEqual(len(self.scheduler.tasks), 1)
        self.scheduler.run_next()

        self.assertEqual(self.engine.calls, [
            (self.first.text, "Adam"),
            (self.second.text, "Adam"),
        ])
        append_count = sum(event[0] == "append" for event in self.output.events)
        self.assertEqual(append_count, 1)

        self.output.complete()
        self.scheduler.run_next()
        self.assertEqual(len(self.engine.calls), 2)

    def test_speech_projection_is_used_for_playback_and_prefetch_without_mutating_book(self):
        first_spoken = f"{self.first.text} Mời bạn xem Hình 1."
        second_spoken = f"Mời bạn xem Hình 2. {self.second.text}"

        self.coordinator.play(
            self.book,
            self.first.id,
            "Adam",
            speech_text_by_segment={
                self.first.id: first_spoken,
                self.second.id: second_spoken,
            },
        )
        self.scheduler.run_next()
        self.scheduler.run_next()

        self.assertEqual(
            self.engine.calls,
            [(first_spoken, "Adam"), (second_spoken, "Adam")],
        )
        self.assertNotIn("Mời bạn xem", self.first.text)
        self.assertNotIn("Mời bạn xem", self.second.text)

    def test_cached_segment_replays_without_calling_engine_or_entering_error(self):
        self.coordinator.play(self.book, self.first.id, "Adam")
        self.scheduler.run_next()
        self.coordinator.stop()

        self.coordinator.play(self.book, self.first.id, "Adam")
        self.scheduler.run_all()

        self.assertEqual(self.engine.calls.count((self.first.text, "Adam")), 1)
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.PLAYING)
        self.assertEqual(self.output.events[-1], ("end",))

    def test_selection_playback_never_changes_book_progress(self):
        self.coordinator.play(self.book, self.first.id, "Adam")
        self.scheduler.run_next()
        self.output.complete()
        saved_before_selection = list(self.progress.saved)
        self.coordinator.stop()

        self.coordinator.play_selection("Chỉ đọc phần này", "Adam")
        self.scheduler.run_all()
        self.output.complete()

        self.assertEqual(self.progress.saved, saved_before_selection)
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.IDLE)

    def test_selection_audio_is_never_written_to_the_persistent_cache(self):
        self.coordinator.play_selection("Nội dung riêng tư tạm thời", "Adam")

        self.scheduler.run_all()

        cache_files = list((Path(self.temp_dir.name) / "cache").glob("*.f32"))
        self.assertEqual(cache_files, [])

    def test_long_selection_plays_speech_sized_parts_in_order_after_each_drain(self):
        settings = SynthesisSettings(max_chars=10)

        self.coordinator.play_selection(
            "Một hai. Ba bốn. Năm sáu.",
            "Adam",
            settings=settings,
        )
        self.assertEqual(self.coordinator.snapshot.selection_part_index, 1)
        self.assertEqual(self.coordinator.snapshot.selection_part_count, 3)
        self.scheduler.run_next()
        self.assertEqual(self.engine.calls, [("Một hai.", "Adam")])
        self.assertEqual(self.coordinator.snapshot.selection_part_index, 1)
        self.coordinator.pause()
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.PAUSED)
        self.assertEqual(self.coordinator.snapshot.selection_part_index, 1)
        self.assertEqual(self.coordinator.snapshot.selection_part_count, 3)
        self.coordinator.resume()

        self.output.complete()
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.LOADING)
        self.assertTrue(self.coordinator.snapshot.is_selection)
        self.assertEqual(self.coordinator.snapshot.selection_part_index, 2)
        self.assertEqual(self.coordinator.snapshot.selection_part_count, 3)
        self.scheduler.run_next()
        self.assertEqual(self.engine.calls[-1], ("Ba bốn.", "Adam"))

        self.output.complete()
        self.scheduler.run_next()
        self.assertEqual(self.engine.calls[-1], ("Năm sáu.", "Adam"))
        self.output.complete()

        self.assertEqual(self.progress.saved, [])
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.IDLE)
        self.assertIsNone(self.coordinator.snapshot.selection_part_index)
        self.assertEqual(self.coordinator.snapshot.selection_part_count, 0)

    def test_selection_paragraphs_stay_separate_before_sentence_fallback(self):
        self.coordinator.play_selection("Đoạn một.\n\nĐoạn hai.", "Adam")

        self.scheduler.run_next()
        self.output.complete()
        self.scheduler.run_next()

        self.assertEqual(
            self.engine.calls,
            [("Đoạn một.", "Adam"), ("Đoạn hai.", "Adam")],
        )

    def test_navigation_is_a_noop_during_selection_playback(self):
        self.coordinator.activate_book(self.book, self.second.id, "Adam", rate=1.0)
        self.coordinator.play_selection("Nội dung tạm thời", "Adam")
        snapshot = self.coordinator.snapshot

        self.coordinator.previous()
        self.coordinator.next()

        self.assertEqual(self.coordinator.snapshot, snapshot)
        self.assertEqual(self.progress.saved, [])

    def test_stop_discards_unplayed_selection_parts(self):
        self.coordinator.play_selection(
            "Một hai. Ba bốn. Năm sáu.",
            "Adam",
            settings=SynthesisSettings(max_chars=10),
        )
        self.scheduler.run_next()

        self.coordinator.stop()
        self.scheduler.run_all()

        self.assertEqual(self.engine.calls, [("Một hai.", "Adam")])
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.IDLE)
        self.assertIsNone(self.coordinator.snapshot.selection_part_index)
        self.assertEqual(self.coordinator.snapshot.selection_part_count, 0)

    def test_failed_selection_part_stops_the_remaining_queue(self):
        self.engine.failure_text = "Ba bốn."
        self.coordinator.play_selection(
            "Một hai. Ba bốn. Năm sáu.",
            "Adam",
            settings=SynthesisSettings(max_chars=10),
        )
        self.scheduler.run_next()
        self.output.complete()
        self.scheduler.run_all()

        self.assertEqual(
            self.engine.calls,
            [("Một hai.", "Adam"), ("Ba bốn.", "Adam")],
        )
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.ERROR)
        self.assertTrue(self.coordinator.snapshot.is_selection)
        self.assertEqual(self.coordinator.snapshot.selection_part_index, 2)
        self.assertEqual(self.coordinator.snapshot.selection_part_count, 3)
        self.assertEqual(self.progress.saved, [])

    def test_activate_book_replaces_navigation_context_without_persisting(self):
        other = sample_book("other")
        other_first, other_second = other.chapters[0].segments
        self.coordinator.play(self.book, self.first.id, "Adam")

        self.coordinator.activate_book(other, other_first.id, "Trúc Ly", rate=1.2)
        self.assertEqual(self.progress.saved, [])
        self.coordinator.next()
        self.scheduler.run_all()

        self.assertEqual(self.progress.saved[-1].book_id, other.id)
        self.assertEqual(self.progress.saved[-1].segment_id, other_second.id)
        self.assertEqual(self.coordinator.snapshot.book_id, other.id)
        self.assertEqual(self.coordinator.snapshot.segment_id, other_second.id)
        self.assertNotIn((self.first.text, "Adam"), self.engine.calls)

    def test_selection_after_activation_is_tagged_with_the_active_book(self):
        other = sample_book("selection-context")
        other_first = other.chapters[0].segments[0]

        self.coordinator.activate_book(other, other_first.id, "Adam", rate=1.0)
        self.coordinator.play_selection("Đọc phần đang chọn", "Adam")

        self.assertEqual(self.coordinator.snapshot.book_id, other.id)
        self.assertEqual(self.coordinator.snapshot.segment_id, other_first.id)
        self.assertTrue(self.coordinator.snapshot.is_selection)
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.LOADING)

    def test_newer_activation_wins_when_older_play_is_blocked_in_stop(self):
        output = BlockingGenerationAudioOutput(blocked_generation=1)
        coordinator = PlaybackCoordinator(
            engine=self.engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=output,
            scheduler=self.scheduler,
        )
        old_book = sample_book("blocked-old-play")
        new_book = sample_book("new-activation")
        old_started = Event()

        def play_old():
            old_started.set()
            coordinator.play(
                old_book,
                old_book.chapters[0].segments[0].id,
                "Adam",
            )

        old = Thread(target=play_old)
        newer = Thread(
            target=lambda: coordinator.activate_book(
                new_book,
                new_book.chapters[0].segments[0].id,
                "Adam",
                rate=1.0,
            )
        )
        old.start()
        self.assertTrue(old_started.wait(timeout=1))
        self.assertTrue(output.stop_started.wait(timeout=1))
        newer.start()
        try:
            newer.join(timeout=0.1)
        finally:
            output.release_stop.set()
        old.join(timeout=2)
        newer.join(timeout=2)

        self.assertFalse(old.is_alive())
        self.assertFalse(newer.is_alive())
        coordinator.next()
        self.assertEqual(self.progress.saved[-1].book_id, new_book.id)

    def test_book_switch_wins_over_navigation_paused_before_invalidation(self):
        coordinator = PauseBeforeInvalidateCoordinator(
            engine=self.engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        old_book = sample_book("stale-next-old")
        new_book = sample_book("stale-next-new")
        coordinator.activate_book(
            old_book,
            old_book.chapters[0].segments[0].id,
            "Adam",
            rate=1.0,
        )
        stale_next = Thread(target=coordinator.next, name="stale-next")
        activation = Thread(
            target=lambda: coordinator.activate_book(
                new_book,
                new_book.chapters[0].segments[0].id,
                "Adam",
                rate=1.0,
            )
        )
        stale_next.start()
        self.assertTrue(coordinator.before_invalidate.wait(timeout=1))
        activation.start()
        try:
            activation.join(timeout=0.1)
        finally:
            coordinator.release_invalidate.set()
        stale_next.join(timeout=2)
        activation.join(timeout=2)

        self.assertFalse(stale_next.is_alive())
        self.assertFalse(activation.is_alive())
        coordinator.play_selection("Ngữ cảnh mới", "Adam")
        self.assertEqual(coordinator.snapshot.book_id, new_book.id)
        self.assertEqual(
            coordinator.snapshot.segment_id,
            new_book.chapters[0].segments[0].id,
        )

    def test_stale_drained_callback_cannot_move_new_book_index(self):
        coordinator = PauseAfterProgressCoordinator(
            engine=self.engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        old_book = sample_book("stale-drain-old")
        new_book = sample_book("stale-drain-new")
        coordinator.play(
            old_book,
            old_book.chapters[0].segments[0].id,
            "Adam",
        )
        self.scheduler.run_next()
        drain = Thread(target=self.output.complete, name="stale-drain")
        drain.start()
        self.assertTrue(coordinator.after_progress.wait(timeout=1))

        coordinator.activate_book(
            new_book,
            new_book.chapters[0].segments[0].id,
            "Adam",
            rate=1.0,
        )
        coordinator.release_drain.set()
        drain.join(timeout=2)

        self.assertFalse(drain.is_alive())
        coordinator.play_selection("Giữ đoạn đầu", "Adam")
        self.assertEqual(coordinator.snapshot.book_id, new_book.id)
        self.assertEqual(
            coordinator.snapshot.segment_id,
            new_book.chapters[0].segments[0].id,
        )

    def test_pause_resume_rate_and_stop_delegate_only_in_valid_range(self):
        self.coordinator.play(self.book, self.first.id, "Adam")
        self.scheduler.run_next()

        self.coordinator.pause()
        self.coordinator.set_rate(1.4)
        self.coordinator.resume()
        self.coordinator.stop()

        self.assertIn(("pause",), self.output.events)
        self.assertIn(("rate", 1.4), self.output.events)
        self.assertIn(("resume",), self.output.events)
        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.IDLE)
        with self.assertRaisesRegex(ValueError, "rate"):
            self.coordinator.set_rate(2.5)

    def test_generation_failure_enters_error_without_saving_progress(self):
        self.engine.failure_text = self.first.text
        self.coordinator.play(self.book, self.first.id, "Adam")

        self.scheduler.run_next()

        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.ERROR)
        self.assertEqual(self.coordinator.snapshot.error, "Không thể tạo giọng đọc cho đoạn này.")
        self.assertEqual(self.progress.saved, [])

    def test_cache_write_failure_is_not_reported_as_a_reading_failure(self):
        for consumed_chunks in (0, 1, 3):
            with self.subTest(consumed_chunks=consumed_chunks):
                output = FakeAudioOutput()
                progress = FakeProgressRepository()
                scheduler = ManualScheduler()
                coordinator = PlaybackCoordinator(
                    engine=ThreeChunkSpeechEngine(),
                    cache=DiskFullCache(
                        Path(self.temp_dir.name) / f"full-{consumed_chunks}",
                        consumed_chunks=consumed_chunks,
                    ),
                    progress_repository=progress,
                    output=output,
                    scheduler=scheduler,
                )
                coordinator.play(self.book, self.first.id, "Adam")

                scheduler.run_next()

                self.assertEqual(coordinator.snapshot.state, PlaybackState.PLAYING)
                self.assertIsNone(coordinator.snapshot.error)
                self.assertEqual(
                    sum(event[0] == "append" for event in output.events),
                    3,
                )
                self.assertIn(("end",), output.events)

                output.complete()

                self.assertEqual(progress.saved[-1].segment_id, self.second.id)

    def test_synthesis_that_produces_no_audio_is_reported_as_a_failure(self):
        engine = SilentSpeechEngine()
        coordinator = PlaybackCoordinator(
            engine=engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        coordinator.play(self.book, self.first.id, "Adam")

        self.scheduler.run_next()

        self.assertEqual(engine.calls, [(self.first.text, "Adam")])
        self.assertEqual(
            sum(event[0] == "append" for event in self.output.events),
            0,
        )
        self.assertEqual(coordinator.snapshot.state, PlaybackState.ERROR)
        self.assertEqual(
            coordinator.snapshot.error,
            "Không thể tạo giọng đọc cho đoạn này.",
        )
        self.assertEqual(self.progress.saved, [])

    def test_synthesis_that_fails_after_real_audio_is_still_reported(self):
        engine = FailingAfterAudioSpeechEngine()
        coordinator = PlaybackCoordinator(
            engine=engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        coordinator.play(self.book, self.first.id, "Adam")

        self.scheduler.run_next()

        self.assertEqual(
            sum(event[0] == "append" for event in self.output.events),
            2,
        )
        self.assertEqual(coordinator.snapshot.state, PlaybackState.ERROR)
        self.assertEqual(
            coordinator.snapshot.error,
            "Không thể tạo giọng đọc cho đoạn này.",
        )
        self.assertEqual(self.progress.saved, [])
        cache_files = list((Path(self.temp_dir.name) / "cache").glob("*.f32"))
        self.assertEqual(cache_files, [])

    def test_selection_that_produces_no_audio_is_reported_as_a_failure(self):
        engine = SilentSpeechEngine()
        coordinator = PlaybackCoordinator(
            engine=engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        coordinator.play_selection("Một hai ba.", "Adam")

        self.scheduler.run_next()

        self.assertEqual(len(engine.calls), 1)
        self.assertEqual(
            sum(event[0] == "append" for event in self.output.events),
            0,
        )
        self.assertEqual(coordinator.snapshot.state, PlaybackState.ERROR)
        self.assertEqual(
            coordinator.snapshot.error,
            "Không thể tạo giọng đọc cho đoạn này.",
        )
        self.assertTrue(coordinator.snapshot.is_selection)
        self.assertEqual(self.progress.saved, [])

    def test_progress_failure_enters_error_after_audio_drains(self):
        self.progress.failure = RuntimeError("database unavailable")
        self.coordinator.play(self.book, self.first.id, "Adam")
        self.scheduler.run_next()

        self.output.complete()

        self.assertEqual(self.coordinator.snapshot.state, PlaybackState.ERROR)
        self.assertEqual(
            self.coordinator.snapshot.error,
            "Không thể lưu vị trí đọc. Sách vẫn có thể mở lại.",
        )

    def test_stop_can_release_a_backpressured_append_without_deadlock(self):
        output = StopReleasedAudioOutput()
        coordinator = PlaybackCoordinator(
            engine=self.engine,
            cache=self.cache,
            progress_repository=self.progress,
            output=output,
            scheduler=self.scheduler,
        )
        coordinator.play(self.book, self.first.id, "Adam")
        worker = Thread(target=self.scheduler.run_next)
        worker.start()
        self.assertTrue(output.append_started.wait(timeout=1))

        stop_returned = Event()

        def stop_playback():
            coordinator.stop()
            stop_returned.set()

        stopper = Thread(target=stop_playback)
        stopper.start()
        try:
            self.assertTrue(
                stop_returned.wait(timeout=0.2),
                "stop deadlocked behind a backpressured append",
            )
        finally:
            output.release_append.set()
            worker.join(timeout=2)
            stopper.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertFalse(stopper.is_alive())
        self.assertEqual(list(Path(self.temp_dir.name).rglob("*.f32")), [])

    def test_next_and_previous_persist_explicit_navigation(self):
        self.coordinator.play(self.book, self.first.id, "Adam")

        self.coordinator.next()
        self.assertEqual(self.progress.saved[-1].segment_id, self.second.id)

        self.coordinator.previous()
        self.assertEqual(self.progress.saved[-1].segment_id, self.first.id)

    def test_cancel_before_cache_commit_never_promotes_stale_generation(self):
        cache = PromotionBarrierCache(Path(self.temp_dir.name) / "barrier-cache")
        coordinator = PlaybackCoordinator(
            engine=self.engine,
            cache=cache,
            progress_repository=self.progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        coordinator.play(self.book, self.first.id, "Adam")
        worker = Thread(target=self.scheduler.run_next)
        worker.start()
        self.assertTrue(cache.commit_started.wait(timeout=1))

        coordinator.stop()
        cache.release_commit.set()
        worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(list((Path(self.temp_dir.name) / "barrier-cache").glob("*.f32")), [])

    def test_late_completed_segment_save_cannot_overwrite_newer_navigation(self):
        progress = LateFirstProgressRepository()
        coordinator = PlaybackCoordinator(
            engine=self.engine,
            cache=self.cache,
            progress_repository=progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        coordinator.play(self.book, self.second.id, "Adam")
        self.scheduler.run_next()
        drain = Thread(target=self.output.complete)
        drain.start()
        self.assertTrue(progress.first_started.wait(timeout=1))

        navigation = Thread(target=coordinator.previous)
        navigation.start()
        navigation.join(timeout=0.1)
        if navigation.is_alive():
            progress.release_first.set()
        drain.join(timeout=2)
        navigation.join(timeout=2)

        self.assertFalse(drain.is_alive())
        self.assertFalse(navigation.is_alive())
        self.assertEqual(progress.saved[-1].segment_id, self.first.id)

    def test_preference_write_is_ordered_after_inflight_drained_save(self):
        progress = BlockingPreferenceRepository()
        coordinator = PlaybackCoordinator(
            engine=self.engine,
            cache=self.cache,
            progress_repository=progress,
            output=self.output,
            scheduler=self.scheduler,
        )
        coordinator.play(self.book, self.second.id, "Adam", rate=1.0)
        self.scheduler.run_next()
        drain = Thread(target=self.output.complete)
        drain.start()
        self.assertTrue(progress.first_started.wait(timeout=1))

        preference_done = Event()

        def change_preference():
            coordinator.set_rate(1.4)
            coordinator.save_preferences(
                self.book,
                self.second.id,
                "Adam",
                rate=1.4,
            )
            preference_done.set()

        preference = Thread(target=change_preference)
        preference.start()
        preference.join(timeout=0.1)
        progress.release_first.set()
        drain.join(timeout=2)
        preference.join(timeout=2)

        self.assertFalse(drain.is_alive())
        self.assertTrue(preference_done.is_set())
        self.assertEqual(progress.current.segment_id, self.second.id)
        self.assertEqual(progress.current.playback_rate, 1.4)


if __name__ == "__main__":
    unittest.main()
