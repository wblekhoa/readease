"""Qt lifecycle wrapper for the native Apple Books selection helper."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import struct
import sys
from typing import Protocol

from PySide6.QtCore import QObject, QProcess, Signal, Slot


class SelectionProtocolError(ValueError):
    """Raised when the native helper violates the bounded pipe protocol."""


class SelectionEventKind(str, Enum):
    READY = "ready"
    HOTKEY = "hotkey"
    TEXT = "text"
    PERMISSION_REQUIRED = "permission_required"
    NO_SELECTION = "no_selection"
    UNSUPPORTED_SOURCE = "unsupported_source"
    CLIPBOARD_RESTORE_FAILED = "clipboard_restore_failed"
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

    def __init__(
        self,
        *,
        command: tuple[str, ...] | None = None,
        acquirer: SelectionAcquirer | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._command = command or default_helper_command()
        if not self._command:
            raise ValueError("helper command cannot be empty")
        self._decoder = SelectionFrameDecoder()
        self._acquirer = acquirer
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

    @Slot()
    def start(self) -> None:
        if self.is_running:
            return
        program, *arguments = self._command
        if not Path(program).is_file():
            self.statusReceived.emit(SelectionEventKind.UNAVAILABLE.value)
            return
        self._closing = False
        self._decoder = SelectionFrameDecoder()
        self._process.setProgram(program)
        self._process.setArguments(arguments)
        self._process.start()

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
            else:
                self.statusReceived.emit(event.kind.value)

    def _handle_hotkey(self) -> None:
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
        if not self._closing:
            self.statusReceived.emit(SelectionEventKind.UNAVAILABLE.value)

    @Slot(int, QProcess.ExitStatus)
    def _on_process_finished(
        self,
        _exit_code: int,
        _exit_status: QProcess.ExitStatus,
    ) -> None:
        if not self._closing:
            self.statusReceived.emit(SelectionEventKind.UNAVAILABLE.value)

    def close(self) -> None:
        self._closing = True
        if self._process.state() is QProcess.ProcessState.NotRunning:
            return
        self._process.terminate()
        if not self._process.waitForFinished(500):
            self._process.kill()
            self._process.waitForFinished(500)
