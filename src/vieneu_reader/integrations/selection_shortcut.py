"""The one global shortcut, described the way the native helper needs it."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vieneu_reader.settings import load_settings, update_settings


SETTINGS_KEY = "selection_shortcut"
READ_ON_COPY_SETTINGS_KEY = "read_on_copy"

# Carbon modifier bits; the native helper is handed exactly this mask.
CMD_KEY = 0x0100
SHIFT_KEY = 0x0200
OPTION_KEY = 0x0800
CONTROL_KEY = 0x1000

_SUPPORTED_MODIFIERS = CONTROL_KEY | OPTION_KEY | SHIFT_KEY | CMD_KEY
# Shift alone still leaves an ordinary typing key; a global hotkey on one would
# swallow that key in every app, so at least one of these has to be held.
_REQUIRED_MODIFIERS = CONTROL_KEY | OPTION_KEY | CMD_KEY

# macOS virtual key codes. Only keys a person can safely give up globally.
KEY_CODES: dict[str, int] = {
    "A": 0, "S": 1, "D": 2, "F": 3, "H": 4, "G": 5, "Z": 6, "X": 7, "C": 8,
    "V": 9, "B": 11, "Q": 12, "W": 13, "E": 14, "R": 15, "Y": 16, "T": 17,
    "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "9": 25, "7": 26,
    "8": 28, "0": 29, "O": 31, "U": 32, "I": 34, "P": 35, "Return": 36,
    "L": 37, "J": 38, "K": 40, "N": 45, "M": 46, "Space": 49,
    "F5": 96, "F6": 97, "F7": 98, "F3": 99, "F8": 100, "F9": 101, "F11": 103,
    "F10": 109, "F12": 111, "F4": 118, "F2": 120, "F1": 122,
}

_KEY_LABELS: dict[int, str] = {code: name for name, code in KEY_CODES.items()}

_MODIFIER_LABELS: tuple[tuple[int, str], ...] = (
    (CONTROL_KEY, "Control"),
    (OPTION_KEY, "Option"),
    (SHIFT_KEY, "Shift"),
    (CMD_KEY, "Command"),
)


class InvalidShortcutError(ValueError):
    """Raised for a combination macOS could not be asked to register."""


@dataclass(frozen=True, slots=True)
class Shortcut:
    key_code: int
    modifiers: int

    def __post_init__(self) -> None:
        if self.key_code not in _KEY_LABELS:
            raise InvalidShortcutError("unsupported key")
        if self.modifiers & ~_SUPPORTED_MODIFIERS:
            raise InvalidShortcutError("unsupported modifier")
        if not self.modifiers & _REQUIRED_MODIFIERS:
            raise InvalidShortcutError("needs Control, Option or Command")

    @property
    def label(self) -> str:
        parts = [
            name for bit, name in _MODIFIER_LABELS if self.modifiers & bit
        ]
        parts.append(_KEY_LABELS[self.key_code])
        return " + ".join(parts)

    def to_payload(self) -> dict[str, int]:
        return {"key_code": self.key_code, "modifiers": self.modifiers}

    @classmethod
    def from_payload(cls, payload: Any) -> "Shortcut | None":
        if not isinstance(payload, dict):
            return None
        key_code = payload.get("key_code")
        modifiers = payload.get("modifiers")
        if not isinstance(key_code, int) or not isinstance(modifiers, int):
            return None
        if isinstance(key_code, bool) or isinstance(modifiers, bool):
            return None
        try:
            return cls(key_code=key_code, modifiers=modifiers)
        except InvalidShortcutError:
            return None


DEFAULT_SHORTCUT = Shortcut(
    key_code=KEY_CODES["R"],
    modifiers=OPTION_KEY | CMD_KEY,
)

# The first default asked for three modifiers at once, which is a lot of hand
# for something meant to be pressed mid-sentence. Anyone still on it never
# chose it - the app saved it for them the first time it registered - so they
# are moved to the shorter one. A combination someone picked themselves is
# never touched.
LEGACY_DEFAULT_SHORTCUT = Shortcut(
    key_code=KEY_CODES["R"],
    modifiers=CONTROL_KEY | OPTION_KEY | CMD_KEY,
)


def key_label(key_code: int) -> str | None:
    return _KEY_LABELS.get(key_code)


class ShortcutPreferenceStore:
    """Persist the chosen combination beside the other local preferences."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> Shortcut:
        stored = Shortcut.from_payload(load_settings(self.path).get(SETTINGS_KEY))
        if stored is None or stored == LEGACY_DEFAULT_SHORTCUT:
            return DEFAULT_SHORTCUT
        return stored

    def save(self, shortcut: Shortcut) -> bool:
        return update_settings(self.path, {SETTINGS_KEY: shortcut.to_payload()})


class ReadOnCopyPreferenceStore:
    """Persist the opt-in read-on-copy switch, which stays off by default."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> bool:
        # Only a stored true means on: a damaged or hand-edited settings file
        # must never quietly start reading the clipboard.
        return load_settings(self.path).get(READ_ON_COPY_SETTINGS_KEY) is True

    def save(self, enabled: bool) -> bool:
        return update_settings(
            self.path,
            {READ_ON_COPY_SETTINGS_KEY: bool(enabled)},
        )
