from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread, current_thread, main_thread
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from vieneu_reader.config import default_app_root
from vieneu_reader.ui.app import QtDispatcher, build_runtime


class AppRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_runtime_composes_local_services_without_starting_network_setup(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "VieNeu Reader"

            runtime = build_runtime(root)
            try:
                self.assertEqual(runtime.window.windowTitle(), "ReadEase — Thư Âm")
                self.assertFalse(runtime.model_setup.is_ready)
                self.assertEqual(
                    runtime.window.root_stack.currentWidget().objectName(),
                    "modelSetupPage",
                )
                self.assertTrue((root / "Books").is_dir())
                self.assertTrue((root / "Cache").is_dir())
                self.assertTrue((root / "Models").is_dir())
                self.assertIsNotNone(runtime.selection_shortcut)
            finally:
                runtime.close()

    def test_rebrand_keeps_the_existing_application_support_directory(self) -> None:
        self.assertEqual(default_app_root().name, "VieNeu Reader")

    def test_dispatcher_moves_worker_callback_to_qt_main_thread(self) -> None:
        dispatcher = QtDispatcher()
        completed = Event()
        observed_threads = []

        worker = Thread(
            target=lambda: dispatcher(
                lambda: (observed_threads.append(current_thread()), completed.set())
            )
        )
        worker.start()
        worker.join(timeout=1)
        self.assertFalse(completed.is_set())

        for _step in range(100):
            self.application.processEvents()
            if completed.wait(timeout=0.01):
                break

        self.assertTrue(completed.is_set())
        self.assertEqual(observed_threads, [main_thread()])


if __name__ == "__main__":
    unittest.main()
