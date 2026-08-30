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
        self.refused_text = None
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
            return SelectionEvent(self.result_kind, self.refused_text)
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

    def test_the_same_key_stops_a_reading_instead_of_starting_another(self) -> None:
        """Reading happens with another app in front, so the way out has to be
        reachable from there: the key that started it stops it."""
        module = self._module()
        acquired = []

        class Acquirer:
            def acquire(self):
                acquired.append(1)
                return module.SelectionEvent(
                    module.SelectionEventKind.TEXT, "đoạn mới"
                )

        reading = False
        bridge = module.SelectionShortcutBridge(
            command=("/bin/echo",),
            acquirer=Acquirer(),
            is_reading=lambda: reading,
        )
        stops = []
        selections = []
        bridge.stopRequested.connect(lambda: stops.append(1))
        bridge.selectionReceived.connect(selections.append)
        try:
            bridge._handle_hotkey()
            self.assertEqual((selections, stops), (["đoạn mới"], []))

            reading = True
            bridge._handle_hotkey()

            self.assertEqual(stops, [1])
            # Nothing new was read, and the clipboard was never touched for a
            # selection ReadEase was not going to speak.
            self.assertEqual(selections, ["đoạn mới"])
            self.assertEqual(len(acquired), 1)
        finally:
            bridge.close()

    def test_a_concealed_selection_is_reported_rather_than_read(self) -> None:
        """Now that any window can be the source, a password manager can be
        one. The native side refuses what it marks; the wrapper must carry
        that refusal through as its own reason, not as a generic failure."""
        module = self._module()

        class Function:
            def __init__(self, implementation):
                self.implementation = implementation
                self.argtypes = None
                self.restype = None

            def __call__(self, *arguments):
                return self.implementation(*arguments)

        class Library:
            def __init__(self, code):
                self.code = code
                self.RDXSelectionAcquire = Function(self.acquire)
                self.RDXSelectionFree = Function(lambda pointer: None)

            def acquire(self, output, length):
                return self.code

        for code, expected in (
            (6, module.SelectionEventKind.CONCEALED_SOURCE),
            (3, module.SelectionEventKind.UNSUPPORTED_SOURCE),
            (2, module.SelectionEventKind.NO_SELECTION),
        ):
            with self.subTest(code=code):
                event = module.MacOSSelectionAcquirer(
                    library=Library(code)
                ).acquire()

                self.assertEqual(event.kind, expected)
                self.assertIsNone(event.text)

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

    def test_changing_the_shortcut_does_not_look_like_a_broken_helper(self) -> None:
        module = self._module()
        from vieneu_reader.integrations.selection_shortcut import (
            CMD_KEY,
            CONTROL_KEY,
            OPTION_KEY,
            Shortcut,
        )

        # A helper that stays alive, so changing the shortcut really has to
        # terminate it the way the running app would.
        script = (
            "import os,struct,time;"
            "os.write(1,b'R'+struct.pack('>I',0));"
            "time.sleep(30)"
        )
        first = Shortcut(key_code=15, modifiers=CONTROL_KEY | OPTION_KEY | CMD_KEY)
        second = Shortcut(key_code=38, modifiers=CONTROL_KEY | CMD_KEY)
        bridge = module.SelectionShortcutBridge(
            command=(sys.executable, "-c", script),
            shortcut=first,
        )
        statuses = []
        accepted = []
        bridge.statusReceived.connect(statuses.append)
        bridge.shortcutAccepted.connect(accepted.append)

        bridge.start()
        try:
            self.assertTrue(self._pump_until(lambda: bool(statuses)))
            self.assertEqual(statuses, ["ready"])

            bridge.apply_shortcut(second)
            self.assertTrue(
                self._pump_until(lambda: len(statuses) >= 2, timeout=5.0)
            )
            # Terminating emits both errorOccurred and finished; neither is a
            # failure the person should be told about.
            self._pump_until(lambda: False, timeout=0.5)

            self.assertEqual(statuses, ["ready", "ready"])
            self.assertEqual(accepted, [first, second])
            self.assertEqual(bridge.shortcut, second)
        finally:
            bridge.close()

    def test_two_refused_shortcuts_stop_instead_of_relaunching_forever(self) -> None:
        module = self._module()
        from vieneu_reader.integrations.selection_shortcut import (
            CMD_KEY,
            CONTROL_KEY,
            Shortcut,
        )

        with TemporaryDirectory() as directory:
            launches = Path(directory) / "launches"
            # The first helper registers; every later one refuses, which is
            # what a machine looks like when both the chosen combination and
            # the fallback are taken.
            script = (
                "import os,struct,time;"
                f"path={str(launches)!r};"
                "first=not os.path.exists(path);"
                "open(path,'a').write('x');"
                "os.write(1,(b'R' if first else b'K')+struct.pack('>I',0));"
                "time.sleep(30 if first else 0)"
            )
            first = Shortcut(key_code=38, modifiers=CONTROL_KEY | CMD_KEY)
            second = Shortcut(key_code=40, modifiers=CONTROL_KEY | CMD_KEY)
            bridge = module.SelectionShortcutBridge(
                command=(sys.executable, "-c", script),
                shortcut=first,
            )
            statuses = []
            bridge.statusReceived.connect(statuses.append)

            bridge.start()
            try:
                self.assertTrue(self._pump_until(lambda: bool(statuses)))
                bridge.apply_shortcut(second)
                self._pump_until(lambda: False, timeout=3.0)

                launch_count = len(launches.read_text(encoding="utf-8"))
                self.assertLess(
                    launch_count,
                    8,
                    f"helper relaunched {launch_count} times",
                )
                # One honest report, not one per doomed attempt.
                self.assertEqual(statuses.count("shortcut_unavailable"), 1)
            finally:
                bridge.close()

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
