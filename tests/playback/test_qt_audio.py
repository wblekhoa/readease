from __future__ import annotations

import os
import struct
from threading import Event, Thread
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudioFormat, QtAudio
from PySide6.QtWidgets import QApplication

from vieneu_reader.domain.models import AudioChunk
from vieneu_reader.playback.qt_audio import QtAudioOutput


class FakeAudioSink(QObject):
    stateChanged = Signal(object)

    def __init__(self, audio_format: QAudioFormat):
        super().__init__()
        self.audio_format = audio_format
        self.device = None
        self._state = QtAudio.State.StoppedState
        self.events: list[str] = []

    def start(self, device) -> None:
        self.device = device
        self._state = QtAudio.State.ActiveState
        self.events.append("start")
        self.stateChanged.emit(self._state)

    def stop(self) -> None:
        self._state = QtAudio.State.StoppedState
        self.events.append("stop")
        self.stateChanged.emit(self._state)

    def suspend(self) -> None:
        self._state = QtAudio.State.SuspendedState
        self.events.append("suspend")
        self.stateChanged.emit(self._state)

    def resume(self) -> None:
        self._state = QtAudio.State.ActiveState
        self.events.append("resume")
        self.stateChanged.emit(self._state)

    def state(self):
        return self._state

    def become_idle(self) -> None:
        self._state = QtAudio.State.IdleState
        self.stateChanged.emit(self._state)


class SinkFactory:
    def __init__(self):
        self.created: list[FakeAudioSink] = []

    def __call__(self, audio_format: QAudioFormat) -> FakeAudioSink:
        sink = FakeAudioSink(audio_format)
        self.created.append(sink)
        return sink


class QtAudioOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.factory = SinkFactory()
        self.output = QtAudioOutput(
            sink_factory=self.factory,
            capacity_bytes=16,
        )
        self.drained = Event()
        self.output.stop(1)
        self.output.begin(1, 1.0, self.drained.set)

    def tearDown(self) -> None:
        self.output.stop(100)
        self.application.processEvents()

    def test_begin_uses_mono_48khz_float32_pull_format(self) -> None:
        sink = self.factory.created[-1]

        self.assertEqual(sink.audio_format.sampleRate(), 48_000)
        self.assertEqual(sink.audio_format.channelCount(), 1)
        self.assertEqual(
            sink.audio_format.sampleFormat(),
            QAudioFormat.SampleFormat.Float,
        )
        self.assertIsNotNone(sink.device)

    def test_append_exposes_pcm_to_sink_and_drains_only_after_idle(self) -> None:
        sink = self.factory.created[-1]
        pcm = struct.pack("<2f", 0.25, -0.25)

        self.output.append(1, AudioChunk(pcm))
        self.output.end(1)

        self.assertEqual(bytes(sink.device.read(len(pcm))), pcm)
        self.assertFalse(self.drained.is_set())
        sink.become_idle()
        self.assertTrue(self.drained.is_set())

    def test_stale_generation_cannot_append_or_complete(self) -> None:
        sink = self.factory.created[-1]

        self.output.append(0, AudioChunk(struct.pack("<f", 0.5)))
        self.output.end(0)

        self.assertEqual(sink.device.bytesAvailable(), 0)
        self.assertFalse(self.drained.is_set())

    def test_pause_and_resume_act_on_the_current_sink(self) -> None:
        first_sink = self.factory.created[-1]

        self.output.pause(1)
        self.output.resume(1)

        self.assertIn("suspend", first_sink.events)
        self.assertIn("resume", first_sink.events)

    def test_changing_speed_does_not_restart_the_audio_device(self) -> None:
        """Speed is applied to the samples now, so the device keeps running -
        no gap in the middle of a sentence, and no change of pitch."""
        before = len(self.factory.created)

        self.output.set_rate(1, 1.25)

        self.assertEqual(len(self.factory.created), before)
        # 60_000 was the old mechanism: play 48 kHz samples faster and the
        # voice rises with them. The device stays at 48 kHz now.
        self.assertEqual(self.factory.created[-1].audio_format.sampleRate(), 48_000)

    def _drain_device(self, device) -> bytes:
        collected = bytearray()
        while True:
            block = device.readData(8192)
            if not block:
                break
            collected.extend(block)
        return bytes(collected)

    def test_audio_already_queued_is_heard_at_the_new_speed(self) -> None:
        """Speed is applied on the way out, so a change is heard at once.

        Applying it on the way in would commit whatever is queued - up to
        several seconds of it - to the old speed before the change took effect.
        """
        import math

        # The shared harness uses a 16-byte buffer to exercise backpressure;
        # this needs a real one, because the whole point is audio sitting in it.
        factory = SinkFactory()
        output = QtAudioOutput(sink_factory=factory, capacity_bytes=4 * 1024 * 1024)
        self.addCleanup(output.stop, 100)
        output.stop(1)
        output.begin(1, 1.0, lambda: None)

        seconds = 1.0
        source = b"".join(
            struct.pack("<f", 0.4 * math.sin(2 * math.pi * 150 * index / 48_000))
            for index in range(int(48_000 * seconds))
        )

        output.append(1, AudioChunk(source))
        # Nothing has been read yet: it is all still queued.
        output.set_rate(1, 2.0)
        output.end(1)
        produced = self._drain_device(factory.created[-1].device)

        heard = len(produced) / 4 / 48_000
        self.assertAlmostEqual(heard, seconds / 2.0, delta=0.05)

    def test_changing_speed_while_paused_leaves_it_paused(self) -> None:
        self.output.pause(1)

        self.output.set_rate(1, 1.25)

        sink = self.factory.created[-1]
        self.assertEqual(sink.state(), QtAudio.State.SuspendedState)
        # And it was never resumed on the way: no sink was swapped underneath.
        self.assertEqual(sink.events[-1], "suspend")

    def test_stop_unblocks_a_backpressured_append_and_discards_old_audio(self) -> None:
        payload = struct.pack("<8f", *([0.25] * 8))
        append_started = Event()
        append_finished = Event()

        def append_audio() -> None:
            append_started.set()
            self.output.append(1, AudioChunk(payload))
            append_finished.set()

        worker = Thread(target=append_audio)
        worker.start()
        self.assertTrue(append_started.wait(timeout=1))
        self.assertFalse(append_finished.wait(timeout=0.05))

        self.output.stop(2)
        worker.join(timeout=1)

        self.assertFalse(worker.is_alive())
        self.assertTrue(append_finished.is_set())
        self.assertFalse(self.drained.is_set())

    def test_invalid_audio_contract_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "48 kHz"):
            self.output.append(1, AudioChunk(b"1234", sample_rate=44_100))
        with self.assertRaisesRegex(ValueError, "float32"):
            self.output.append(1, AudioChunk(b"123"))


if __name__ == "__main__":
    unittest.main()
