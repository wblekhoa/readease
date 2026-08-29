from __future__ import annotations

import os
from threading import Event, current_thread, main_thread
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from vieneu_reader.domain.models import Voice
from vieneu_reader.speech.vieneu import ModelPreparationError
from vieneu_reader.ui.model_setup import ModelSetupCoordinator


class FakeModelEngine:
    def __init__(self):
        self.is_model_ready = False
        self.failure: Exception | None = None
        self.worker_thread = None
        self.release = Event()
        self.block = False

    def prepare_model(self, callback) -> None:
        self.worker_thread = current_thread()
        callback(0.25, "Đang tải mô hình…")
        if self.block:
            self.release.wait(timeout=2)
            callback(0.75, "Đang kiểm tra…")
        if self.failure is not None:
            raise self.failure
        self.is_model_ready = True
        callback(1.0, "Sẵn sàng.")

    def voices(self):
        return (Voice("Adam", "Adam - Nam Bộ"),)


class ModelSetupCoordinatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _pump_until(self, event: Event, timeout_steps: int = 200) -> bool:
        for _step in range(timeout_steps):
            self.application.processEvents()
            if event.wait(timeout=0.01):
                self.application.processEvents()
                return True
        return False

    def test_preparation_runs_off_main_thread_and_emits_voices(self) -> None:
        engine = FakeModelEngine()
        coordinator = ModelSetupCoordinator(engine)
        completed = Event()
        received = []
        coordinator.ready.connect(lambda voices: (received.extend(voices), completed.set()))

        coordinator.start()

        self.assertTrue(self._pump_until(completed))
        self.assertIsNot(engine.worker_thread, main_thread())
        self.assertEqual(received[0].id, "Adam")
        self.assertTrue(coordinator.is_ready)
        coordinator.close()

    def test_failure_emits_safe_retry_message(self) -> None:
        engine = FakeModelEngine()
        engine.failure = RuntimeError("secret filesystem detail")
        coordinator = ModelSetupCoordinator(engine)
        failed = Event()
        messages = []
        coordinator.failed.connect(lambda message: (messages.append(message), failed.set()))

        coordinator.start()

        self.assertTrue(self._pump_until(failed))
        self.assertIn("Thử lại", messages[0])
        self.assertNotIn("secret", messages[0])
        coordinator.close()

    def test_prepared_failure_keeps_the_reason_the_engine_gave(self) -> None:
        engine = FakeModelEngine()
        engine.failure = ModelPreparationError("Máy đã hết dung lượng trống.")
        coordinator = ModelSetupCoordinator(engine)
        failed = Event()
        messages = []
        coordinator.failed.connect(lambda message: (messages.append(message), failed.set()))

        coordinator.start()

        self.assertTrue(self._pump_until(failed))
        self.assertEqual(messages[0], "Máy đã hết dung lượng trống.")
        coordinator.close()

    def test_cancel_discards_late_success(self) -> None:
        engine = FakeModelEngine()
        engine.block = True
        coordinator = ModelSetupCoordinator(engine)
        progressed = Event()
        cancelled = Event()
        ready = Event()
        coordinator.progressChanged.connect(lambda *_args: progressed.set())
        coordinator.cancelled.connect(cancelled.set)
        coordinator.ready.connect(lambda _voices: ready.set())
        coordinator.start()
        self.assertTrue(self._pump_until(progressed))

        coordinator.cancel()
        engine.release.set()

        self.assertTrue(self._pump_until(cancelled))
        self.assertFalse(ready.is_set())
        coordinator.close()

    def test_close_suppresses_late_qt_signals(self) -> None:
        engine = FakeModelEngine()
        engine.block = True
        coordinator = ModelSetupCoordinator(engine)
        progressed = Event()
        late_signals = []
        coordinator.progressChanged.connect(lambda *_args: progressed.set())
        coordinator.ready.connect(lambda _voices: late_signals.append("ready"))
        coordinator.failed.connect(lambda _message: late_signals.append("failed"))
        coordinator.cancelled.connect(lambda: late_signals.append("cancelled"))
        coordinator.start()
        self.assertTrue(self._pump_until(progressed))

        coordinator.close()
        engine.release.set()

        coordinator._worker.join(timeout=1)
        self.assertFalse(coordinator._worker.is_alive())
        self.application.processEvents()
        self.assertEqual(late_signals, [])


class BuildsOnDiskTests(unittest.TestCase):
    """What the coordinator reports about builds it did not download itself."""

    class _Engine:
        precision = "int8"

        def __init__(self, sizes):
            self._sizes = sizes

        def installed_builds(self):
            return dict(self._sizes)

    def test_a_build_with_bytes_on_disk_is_reported_as_downloaded(self):
        coordinator = ModelSetupCoordinator(
            self._Engine({"int8": 165_675_008, "fp32": 475_000_000})
        )

        self.assertTrue(coordinator.is_build_downloaded("fp32"))
        self.assertTrue(coordinator.is_build_downloaded("int8"))

    def test_a_build_that_is_absent_or_empty_is_not_downloaded(self):
        coordinator = ModelSetupCoordinator(
            self._Engine({"int8": 165_675_008, "fp32": 0})
        )

        self.assertFalse(coordinator.is_build_downloaded("fp32"))
        self.assertFalse(coordinator.is_build_downloaded("unknown"))

    def test_an_engine_without_the_capability_answers_no_instead_of_raising(self):
        class Older:
            precision = "int8"

        self.assertFalse(ModelSetupCoordinator(Older()).is_build_downloaded("fp32"))


if __name__ == "__main__":
    unittest.main()
