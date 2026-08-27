from __future__ import annotations

import ctypes
from importlib.util import find_spec
import os
from pathlib import Path
import struct
import sys
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


class ExternalSelectionBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def _module(self):
        try:
            spec = find_spec("vieneu_reader.integrations.macos_selection")
        except ModuleNotFoundError:
            spec = None
        self.assertIsNotNone(
            spec,
            "external-selection bridge module must exist",
        )
        from vieneu_reader.integrations import macos_selection

        return macos_selection

    def _pump_until(self, predicate, timeout: float = 2.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.application.processEvents()
            if predicate():
                return True
            time.sleep(0.005)
        self.application.processEvents()
        return bool(predicate())

    def test_decoder_waits_for_a_complete_unicode_frame(self) -> None:
        module = self._module()
        decoder = module.SelectionFrameDecoder()
        payload = "Đọc đúng phần đã chọn".encode("utf-8")
        frame = b"T" + struct.pack(">I", len(payload)) + payload

        self.assertEqual(decoder.feed(frame[:4]), ())
        events = decoder.feed(frame[4:])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, module.SelectionEventKind.TEXT)
        self.assertEqual(events[0].text, "Đọc đúng phần đã chọn")

    def test_decoder_rejects_oversized_or_invalid_frames(self) -> None:
        module = self._module()
        decoder = module.SelectionFrameDecoder(max_payload_bytes=8)

        with self.assertRaises(module.SelectionProtocolError):
            decoder.feed(b"T" + struct.pack(">I", 9))

        with self.assertRaises(module.SelectionProtocolError):
            module.SelectionFrameDecoder().feed(b"X" + struct.pack(">I", 0))

    def test_default_helper_sits_beside_the_packaged_app_executable(self) -> None:
        module = self._module()
        executable = Path("/Applications/ReadEase.app/Contents/MacOS/app_main")

        command = module.default_helper_command(executable)

        self.assertEqual(
            command,
            (
                "/Applications/ReadEase.app/Contents/MacOS/"
                "ReadEaseSelectionBridge",
            ),
        )

    def test_default_native_library_sits_beside_the_packaged_executable(self) -> None:
        module = self._module()
        executable = Path("/Applications/ReadEase.app/Contents/MacOS/app_main")

        resolver = getattr(module, "default_native_library_path", None)
        self.assertIsNotNone(resolver, "native-library resolver must exist")
        path = resolver(executable)

        self.assertEqual(
            path,
            Path(
                "/Applications/ReadEase.app/Contents/MacOS/"
                "libReadEaseSelectionNative.dylib"
            ),
        )

    def test_real_child_process_delivers_text_and_status_frames(self) -> None:
        module = self._module()
        text = "Xin chào từ Apple Books"
        frames = (
            b"R" + struct.pack(">I", 0)
            + b"H" + struct.pack(">I", 0)
        )
        script = (
            "import os,time;"
            f"os.write(1,{frames!r});"
            "time.sleep(0.05)"
        )
        class Acquirer:
            def acquire(self):
                return module.SelectionEvent(module.SelectionEventKind.TEXT, text)

        self.assertIn(
            "acquirer",
            __import__("inspect").signature(module.SelectionShortcutBridge).parameters,
            "bridge must acquire clipboard in the ReadEase process",
        )
        bridge = module.SelectionShortcutBridge(
            command=(sys.executable, "-c", script),
            acquirer=Acquirer(),
        )
        statuses = []
        selections = []
        bridge.statusReceived.connect(statuses.append)
        bridge.selectionReceived.connect(selections.append)

        bridge.start()
        try:
            self.assertTrue(self._pump_until(lambda: bool(selections)))
            self.assertEqual(statuses[0], "ready")
            self.assertEqual(selections, [text])
        finally:
            bridge.close()

    def test_hotkey_acquisition_failure_emits_only_safe_status(self) -> None:
        module = self._module()
        frame = b"H" + struct.pack(">I", 0)
        script = (
            "import os,time;"
            f"os.write(1,{frame!r});"
            "time.sleep(0.05)"
        )

        class Acquirer:
            def acquire(self):
                return module.SelectionEvent(
                    module.SelectionEventKind.CLIPBOARD_RESTORE_FAILED
                )

        self.assertIn(
            "acquirer",
            __import__("inspect").signature(module.SelectionShortcutBridge).parameters,
            "bridge must acquire clipboard in the ReadEase process",
        )
        bridge = module.SelectionShortcutBridge(
            command=(sys.executable, "-c", script),
            acquirer=Acquirer(),
        )
        statuses = []
        selections = []
        bridge.statusReceived.connect(statuses.append)
        bridge.selectionReceived.connect(selections.append)

        bridge.start()
        try:
            self.assertTrue(self._pump_until(lambda: bool(statuses)))
            self.assertEqual(statuses, ["clipboard_restore_failed"])
            self.assertEqual(selections, [])
        finally:
            bridge.close()

    def test_native_acquirer_decodes_utf8_and_frees_the_native_buffer(self) -> None:
        module = self._module()
        encoded = "Đọc từ process chính".encode("utf-8")

        class Function:
            def __init__(self, implementation):
                self.implementation = implementation
                self.argtypes = None
                self.restype = None

            def __call__(self, *arguments):
                return self.implementation(*arguments)

        class Library:
            def __init__(self):
                self.buffer = ctypes.create_string_buffer(encoded)
                self.freed = []
                self.RDXSelectionAcquire = Function(self.acquire)
                self.RDXSelectionFree = Function(self.free)

            def acquire(self, output, length):
                ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = (
                    ctypes.cast(self.buffer, ctypes.c_void_p)
                )
                ctypes.cast(length, ctypes.POINTER(ctypes.c_size_t))[0] = len(encoded)
                return 0

            def free(self, pointer):
                self.freed.append(pointer.value)

        library = Library()
        constructor = module.MacOSSelectionAcquirer
        self.assertIn(
            "library",
            __import__("inspect").signature(constructor).parameters,
            "native wrapper must be testable without loading a real dylib",
        )

        event = constructor(library=library).acquire()

        self.assertEqual(event.kind, module.SelectionEventKind.TEXT)
        self.assertEqual(event.text, "Đọc từ process chính")
        self.assertEqual(library.freed, [ctypes.addressof(library.buffer)])

    def test_permission_frame_is_safe_status_not_selected_text(self) -> None:
        module = self._module()
        frame = b"P" + struct.pack(">I", 0)
        script = (
            "import os,time;"
            f"os.write(1,{frame!r});"
            "time.sleep(0.05)"
        )
        bridge = module.SelectionShortcutBridge(
            command=(sys.executable, "-c", script),
        )
        statuses = []
        selections = []
        bridge.statusReceived.connect(statuses.append)
        bridge.selectionReceived.connect(selections.append)

        bridge.start()
        try:
            self.assertTrue(self._pump_until(lambda: bool(statuses)))
            self.assertEqual(statuses, ["permission_required"])
            self.assertEqual(selections, [])
        finally:
            bridge.close()


if __name__ == "__main__":
    unittest.main()
