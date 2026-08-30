"""Qt lifecycle wrapper for the native text-selection helper."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import struct
import sys
from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QObject, QProcess, QTimer, Signal, Slot

from vieneu_reader.integrations.selection_shortcut import (
    DEFAULT_SHORTCUT,
    Shortcut,
)


class SelectionProtocolError(ValueError):
    """Raised when the native helper violates the bounded pipe protocol."""


class SelectionEventKind(str, Enum):
    READY = "ready"
    HOTKEY = "hotkey"
    TEXT = "text"
    PERMISSION_REQUIRED = "permission_required"
    NO_SELECTION = "no_selection"
    UNSUPPORTED_SOURCE = "unsupported_source"
    CONCEALED_SOURCE = "concealed_source"
    CLIPBOARD_RESTORE_FAILED = "clipboard_restore_failed"
    SHORTCUT_UNAVAILABLE = "shortcut_unavailable"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class SelectionEvent:
    kind: SelectionEventKind
    text: str | None = None


_FRAME_KINDS = {
    ord("R"): SelectionEventKind.READY,
    ord("H"): SelectionEventKind.HOTKEY,
    ord("T"): SelectionEventKind.TEXT,
    ord("P"): SelectionEventKind.PERMISSION_REQUIRED,
    ord("N"): SelectionEventKind.NO_SELECTION,
    ord("U"): SelectionEventKind.UNSUPPORTED_SOURCE,
    ord("C"): SelectionEventKind.CLIPBOARD_RESTORE_FAILED,
    ord("K"): SelectionEventKind.SHORTCUT_UNAVAILABLE,
    ord("E"): SelectionEventKind.UNAVAILABLE,
}


class SelectionFrameDecoder:
    """Incrementally decode non-logging length-prefixed helper frames."""

    def __init__(self, *, max_payload_bytes: int = 500_000):
        if max_payload_bytes < 1:
            raise ValueError("max_payload_bytes must be positive")
        self._max_payload_bytes = max_payload_bytes
        self._buffer = bytearray()

    def feed(self, chunk: bytes | bytearray) -> tuple[SelectionEvent, ...]:
        self._buffer.extend(chunk)
        events: list[SelectionEvent] = []
        while len(self._buffer) >= 5:
            event_kind = _FRAME_KINDS.get(self._buffer[0])
            if event_kind is None:
                self._buffer.clear()
                raise SelectionProtocolError("unknown frame kind")
            payload_length = struct.unpack(">I", self._buffer[1:5])[0]
            if payload_length > self._max_payload_bytes:
                self._buffer.clear()
                raise SelectionProtocolError("frame payload is too large")
            frame_length = 5 + payload_length
            if len(self._buffer) < frame_length:
                break
            payload = bytes(self._buffer[5:frame_length])
            del self._buffer[:frame_length]
            if event_kind is SelectionEventKind.TEXT:
                try:
                    text = payload.decode("utf-8", errors="strict")
                except UnicodeDecodeError as error:
                    raise SelectionProtocolError("text payload is not UTF-8") from error
                if not text:
                    raise SelectionProtocolError("text payload is empty")
                events.append(SelectionEvent(event_kind, text))
            else:
                if payload:
                    raise SelectionProtocolError("status frame has a payload")
                events.append(SelectionEvent(event_kind))
        return tuple(events)


def default_helper_command(executable: Path | None = None) -> tuple[str, ...]:
    override = os.environ.get("VIENEU_READER_SELECTION_HELPER")
    if override:
        return (override,)
    owner = Path(executable or sys.executable).resolve()
    return (str(owner.parent / "ReadEaseSelectionBridge"),)


def default_native_library_path(executable: Path | None = None) -> Path:
    override = os.environ.get("VIENEU_READER_SELECTION_NATIVE")
    if override:
        return Path(override)
    owner = Path(executable or sys.executable).resolve()
    return owner.parent / "libReadEaseSelectionNative.dylib"


class SelectionAcquirer(Protocol):
    def acquire(self) -> SelectionEvent: ...


class MacOSSelectionAcquirer:
    """Call the native selection transaction inside the ReadEase process."""

    _RESULT_KINDS = {
        1: SelectionEventKind.PERMISSION_REQUIRED,
        2: SelectionEventKind.NO_SELECTION,
        3: SelectionEventKind.UNSUPPORTED_SOURCE,
        4: SelectionEventKind.CLIPBOARD_RESTORE_FAILED,
        5: SelectionEventKind.UNAVAILABLE,
        6: SelectionEventKind.CONCEALED_SOURCE,
    }

    def __init__(
        self,
        library_path: Path | None = None,
        *,
        library: object | None = None,
    ):
        path = library_path or default_native_library_path()
        self._library = library if library is not None else ctypes.CDLL(str(path))
        self._library.RDXSelectionAcquire.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self._library.RDXSelectionAcquire.restype = ctypes.c_int
        self._library.RDXSelectionFree.argtypes = [ctypes.c_void_p]
        self._library.RDXSelectionFree.restype = None

    def acquire(self) -> SelectionEvent:
        output = ctypes.c_void_p()
        length = ctypes.c_size_t()
        result = int(
            self._library.RDXSelectionAcquire(
                ctypes.byref(output),
                ctypes.byref(length),
            )
        )
        if result != 0:
            return SelectionEvent(
                self._RESULT_KINDS.get(result, SelectionEventKind.UNAVAILABLE)
            )
        if not output.value or length.value == 0 or length.value > 500_000:
            if output.value:
                self._library.RDXSelectionFree(output)
            return SelectionEvent(SelectionEventKind.UNAVAILABLE)
        try:
            payload = ctypes.string_at(output, length.value)
            text = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return SelectionEvent(SelectionEventKind.UNAVAILABLE)
        finally:
            self._library.RDXSelectionFree(output)
        if not text:
            return SelectionEvent(SelectionEventKind.UNAVAILABLE)
        return SelectionEvent(SelectionEventKind.TEXT, text)


class SelectionShortcutBridge(QObject):
    """Own the native helper process and expose only safe Qt signals."""

    selectionReceived = Signal(str)
    statusReceived = Signal(str)
    shortcutAccepted = Signal(object)
    shortcutRejected = Signal(object)
    stopRequested = Signal()

    # A refused combination is worth one fallback. Beyond that the machine is
    # telling us both are taken, and relaunching only burns processes.
    _MAX_REGISTRATION_ATTEMPTS = 2

    def __init__(
        self,
        *,
        command: tuple[str, ...] | None = None,
        acquirer: SelectionAcquirer | None = None,
        shortcut: Shortcut | None = None,
        is_reading: Callable[[], bool] | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._is_reading = is_reading
        self._command = command or default_helper_command()
        if not self._command:
            raise ValueError("helper command cannot be empty")
        self._decoder = SelectionFrameDecoder()
        self._acquirer = acquirer
        self._shortcut = shortcut or DEFAULT_SHORTCUT
        self._registered: Shortcut | None = None
        self._registration_attempts = 0
        self._restart_pending: Shortcut | None = None
        self._suppress_exit_status = False
        self._closing = False
        self._process = QProcess(self)
        self._process.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.errorOccurred.connect(self._on_process_error)
        self._process.finished.connect(self._on_process_finished)

    @property
    def is_running(self) -> bool:
        return self._process.state() is not QProcess.ProcessState.NotRunning

    @property
    def shortcut(self) -> Shortcut:
        """The combination the helper is registering or has registered."""

        return self._shortcut

    @Slot()
    def start(self) -> None:
        if self.is_running:
            return
        program, *arguments = self._command
        if not Path(program).is_file():
            self.statusReceived.emit(SelectionEventKind.UNAVAILABLE.value)
            return
        self._closing = False
        self._suppress_exit_status = False
        self._decoder = SelectionFrameDecoder()
        self._process.setProgram(program)
        self._process.setArguments(
            [
                *arguments,
                str(self._shortcut.key_code),
                str(self._shortcut.modifiers),
            ]
        )
        self._process.start()

    def apply_shortcut(self, shortcut: Shortcut) -> None:
        """Re-register the helper on a newly chosen combination."""

        if shortcut == self._shortcut and self.is_running:
            return
        self._restart_pending = shortcut
        self._registration_attempts = 0
        if not self.is_running:
            self._begin_pending_restart()
            return
        # The helper exits when its parent changes; asking it to stop is the
        # same mechanism, and the finished handler picks the new one up.
        self._suppress_exit_status = True
        self._process.terminate()

    def _begin_pending_restart(self) -> None:
        pending = self._restart_pending
        self._restart_pending = None
        if pending is None:
            return
        self._shortcut = pending
        self.start()

    def _fallback_shortcut(self) -> Shortcut | None:
        if self._registered is not None and self._registered != self._shortcut:
            return self._registered
        if self._shortcut != DEFAULT_SHORTCUT:
            return DEFAULT_SHORTCUT
        return None

    @Slot()
    def _read_stdout(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput())
        if not chunk:
            return
        try:
            events = self._decoder.feed(chunk)
        except SelectionProtocolError:
            self.statusReceived.emit(SelectionEventKind.UNAVAILABLE.value)
            self.close()
            return
        for event in events:
            if event.kind is SelectionEventKind.HOTKEY:
                self._handle_hotkey()
            elif event.kind is SelectionEventKind.TEXT:
                self.selectionReceived.emit(event.text)
            elif event.kind is SelectionEventKind.SHORTCUT_UNAVAILABLE:
                self._handle_rejected_shortcut()
            else:
                if event.kind is SelectionEventKind.READY:
                    self._registered = self._shortcut
                    self._registration_attempts = 0
                    self.shortcutAccepted.emit(self._shortcut)
                self.statusReceived.emit(event.kind.value)

    def _handle_rejected_shortcut(self) -> None:
        refused = self._shortcut
        self._registration_attempts += 1
        exhausted = self._registration_attempts >= self._MAX_REGISTRATION_ATTEMPTS
        fallback = None if exhausted else self._fallback_shortcut()
        # The helper exits right after refusing; that exit must not replace the
        # honest "this combination is taken" message with a generic failure.
        self._suppress_exit_status = True
        self._restart_pending = fallback
        # Say it once. Repeating it per doomed attempt turns one problem into
        # a stream of identical banners.
        if self._registration_attempts == 1:
            self.shortcutRejected.emit(refused)
            self.statusReceived.emit(
                SelectionEventKind.SHORTCUT_UNAVAILABLE.value
            )

    def _handle_hotkey(self) -> None:
        # Pressed while something is already being read, the same key means
        # stop. Deciding here, before the copy, keeps ReadEase from touching
        # the clipboard for a selection it is not going to read.
        if self._is_reading is not None and self._is_reading():
            self.stopRequested.emit()
            return
        if self._acquirer is None:
            try:
                self._acquirer = MacOSSelectionAcquirer()
            except OSError:
                self.statusReceived.emit(SelectionEventKind.UNAVAILABLE.value)
                return
        event = self._acquirer.acquire()
        if event.kind is SelectionEventKind.TEXT and event.text:
            self.selectionReceived.emit(event.text)
        else:
            kind = (
                event.kind
                if event.kind is not SelectionEventKind.TEXT
                else SelectionEventKind.UNAVAILABLE
            )
            self.statusReceived.emit(kind.value)

    @Slot(QProcess.ProcessError)
    def _on_process_error(self, _error: QProcess.ProcessError) -> None:
        self._report_exit()

    @Slot(int, QProcess.ExitStatus)
    def _on_process_finished(
        self,
        _exit_code: int,
        _exit_status: QProcess.ExitStatus,
    ) -> None:
        self._report_exit()

    def _report_exit(self) -> None:
        if self._process.state() is not QProcess.ProcessState.NotRunning:
            # Terminating a helper emits errorOccurred AND finished. The first
            # already started its replacement, so this is the old process
            # signing off, not the running one failing.
            return
        if self._restart_pending is not None and not self._closing:
            self._begin_pending_restart()
            return
        if self._suppress_exit_status:
            self._suppress_exit_status = False
            return
        if not self._closing:
            self.statusReceived.emit(SelectionEventKind.UNAVAILABLE.value)

    def close(self) -> None:
        self._closing = True
        self._restart_pending = None
        if self._process.state() is QProcess.ProcessState.NotRunning:
            return
        self._process.terminate()
        if not self._process.waitForFinished(500):
            self._process.kill()
            self._process.waitForFinished(500)
