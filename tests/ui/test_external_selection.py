from __future__ import annotations

import ctypes
from importlib.util import find_spec
import os
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


class FakeClipboardSource:
    """Stand in for the native pasteboard without touching the real one."""

    def __init__(self, *, count: int, text: str | None):
        self.count = count
        self.text = text
        self.result_kind = None
        self.text_reads = 0

    def change_count(self) -> int:
        return self.count

    def copied_text(self):
        from vieneu_reader.integrations.macos_selection import (
            SelectionEvent,
            SelectionEventKind,
        )

        self.text_reads += 1
        if self.result_kind is not None:
            return SelectionEvent(self.result_kind)
        if self.text is None:
            return SelectionEvent(SelectionEventKind.NO_SELECTION)
        return SelectionEvent(SelectionEventKind.TEXT, self.text)


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

    def test_helper_is_launched_with_the_chosen_keycode_and_modifier_mask(
        self,
    ) -> None:
        module = self._module()
        from vieneu_reader.integrations.selection_shortcut import Shortcut

        script = (
            "import os,struct,sys,time;"
            "payload=' '.join(sys.argv[1:]).encode();"
            "os.write(1,b'T'+struct.pack('>I',len(payload))+payload);"
            "time.sleep(0.05)"
        )
        chosen = Shortcut(key_code=38, modifiers=4352)
        bridge = module.SelectionShortcutBridge(
            command=(sys.executable, "-c", script),
            shortcut=chosen,
        )
        selections = []
        bridge.selectionReceived.connect(selections.append)

        bridge.start()
        try:
            self.assertTrue(self._pump_until(lambda: bool(selections)))
            self.assertEqual(selections, ["38 4352"])
        finally:
            bridge.close()

    def test_rejected_shortcut_is_reported_once_and_falls_back(self) -> None:
        module = self._module()
        from vieneu_reader.integrations.selection_shortcut import (
            DEFAULT_SHORTCUT,
            Shortcut,
        )

        with TemporaryDirectory() as directory:
            marker = Path(directory) / "attempted"
            # First launch refuses to register, as macOS does for a combination
            # another app already owns; the fallback launch succeeds.
            script = (
                "import os,struct,time;"
                f"marker={str(marker)!r};"
                "taken=not os.path.exists(marker);"
                "open(marker,'a').close();"
                "os.write(1,(b'K' if taken else b'R')+struct.pack('>I',0));"
                "time.sleep(0.0 if taken else 0.3)"
            )
            occupied = Shortcut(key_code=38, modifiers=4352)
            bridge = module.SelectionShortcutBridge(
                command=(sys.executable, "-c", script),
                shortcut=occupied,
            )
            statuses = []
            rejected = []
            accepted = []
            bridge.statusReceived.connect(statuses.append)
            bridge.shortcutRejected.connect(rejected.append)
            bridge.shortcutAccepted.connect(accepted.append)

            bridge.start()
            try:
                self.assertTrue(self._pump_until(lambda: len(statuses) >= 2))
                # The helper exits after refusing; that exit must not overwrite
                # the honest "this combination is taken" message.
                self.assertEqual(statuses, ["shortcut_unavailable", "ready"])
                self.assertEqual(rejected, [occupied])
                # A refused choice must not leave the person without a shortcut.
                self.assertEqual(accepted, [DEFAULT_SHORTCUT])
                self.assertEqual(bridge.shortcut, DEFAULT_SHORTCUT)
            finally:
                bridge.close()

    def test_registered_shortcut_is_announced_so_it_can_be_persisted(self) -> None:
        module = self._module()
        from vieneu_reader.integrations.selection_shortcut import Shortcut

        frame = b"R" + struct.pack(">I", 0)
        script = (
            "import os,time;"
            f"os.write(1,{frame!r});"
            "time.sleep(0.05)"
        )
        chosen = Shortcut(key_code=38, modifiers=4352)
        bridge = module.SelectionShortcutBridge(
            command=(sys.executable, "-c", script),
            shortcut=chosen,
        )
        accepted = []
        bridge.shortcutAccepted.connect(accepted.append)

        bridge.start()
        try:
            self.assertTrue(self._pump_until(lambda: bool(accepted)))
            self.assertEqual(accepted, [chosen])
        finally:
            bridge.close()

    def test_read_on_copy_is_off_until_it_is_switched_on(self) -> None:
        module = self._module()
        source = FakeClipboardSource(count=4, text="Đoạn vừa sao chép")
        watcher = module.ClipboardReadingWatcher(source=source)
        selections = []
        watcher.selectionReceived.connect(selections.append)

        self.assertFalse(watcher.is_enabled)
        self.assertFalse(watcher.is_active)

        # Nothing may be read while the toggle is off, however the clipboard
        # moves underneath it.
        source.count = 5
        watcher.poll()
        self.assertEqual(selections, [])
        self.assertEqual(source.text_reads, 0)

        watcher.set_enabled(True)
        self.assertTrue(watcher.is_active)

        # Switching on adopts whatever is already on the clipboard, so an old
        # copy is never spoken just because the toggle moved.
        watcher.poll()
        self.assertEqual(selections, [])
        self.assertEqual(source.text_reads, 0)

        source.count = 6
        watcher.poll()
        self.assertEqual(selections, ["Đoạn vừa sao chép"])

        # A clipboard that has not moved is not read again.
        watcher.poll()
        self.assertEqual(selections, ["Đoạn vừa sao chép"])
        self.assertEqual(source.text_reads, 1)

        watcher.set_enabled(False)
        self.assertFalse(watcher.is_active)
        source.count = 7
        watcher.poll()
        self.assertEqual(selections, ["Đoạn vừa sao chép"])
        watcher.close()

    def test_read_on_copy_stays_silent_for_anything_but_apple_books(self) -> None:
        module = self._module()
        source = FakeClipboardSource(count=1, text=None)
        watcher = module.ClipboardReadingWatcher(source=source)
        selections = []
        statuses = []
        watcher.selectionReceived.connect(selections.append)
        watcher.statusReceived.connect(statuses.append)
        watcher.set_enabled(True)

        source.count = 2
        source.result_kind = module.SelectionEventKind.UNSUPPORTED_SOURCE
        watcher.poll()

        # Copying a password somewhere else must be silent, not an error the
        # person has to dismiss.
        self.assertEqual(selections, [])
        self.assertEqual(statuses, [])
        watcher.close()

    def test_restoring_the_clipboard_after_a_hotkey_is_not_a_new_copy(self) -> None:
        module = self._module()
        source = FakeClipboardSource(count=10, text="Nội dung cũ trong clipboard")
        watcher = module.ClipboardReadingWatcher(source=source)
        selections = []
        watcher.selectionReceived.connect(selections.append)
        watcher.set_enabled(True)

        # The shortcut copies and then restores, which moves the change count
        # twice; the clipboard it leaves behind is the person's own, not a
        # fresh copy, so it must not be read aloud.
        source.count = 12
        watcher.resync()
        watcher.poll()

        self.assertEqual(selections, [])
        self.assertEqual(source.text_reads, 0)
        watcher.close()

    def test_read_on_copy_stays_off_when_the_native_library_is_missing(self) -> None:
        module = self._module()
        watcher = module.ClipboardReadingWatcher()

        # No packaged dylib sits beside the test interpreter, so switching on
        # must fail closed rather than leave a timer running on nothing.
        watcher.set_enabled(True)

        self.assertFalse(watcher.is_enabled)
        self.assertFalse(watcher.is_active)
        watcher.close()

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
