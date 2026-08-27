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

    def test_pause_resume_and_rate_restart_the_current_sink(self) -> None:
        first_sink = self.factory.created[-1]

        self.output.pause(1)
        self.output.resume(1)
        self.output.set_rate(1, 1.25)

        self.assertIn("suspend", first_sink.events)
        self.assertIn("resume", first_sink.events)
        self.assertEqual(len(self.factory.created), 2)
        self.assertEqual(self.factory.created[-1].audio_format.sampleRate(), 60_000)

    def test_changing_rate_while_paused_keeps_the_replacement_sink_paused(self) -> None:
        self.output.pause(1)

        self.output.set_rate(1, 1.25)

        replacement = self.factory.created[-1]
        self.assertEqual(replacement.state(), QtAudio.State.SuspendedState)
        self.assertEqual(replacement.events[-1], "suspend")

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
