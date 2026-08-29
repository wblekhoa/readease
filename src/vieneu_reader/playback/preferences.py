"""Remember the voice and speed chosen when no book is holding them."""

from __future__ import annotations

from pathlib import Path

from vieneu_reader.settings import load_settings, update_settings


VOICE_SETTINGS_KEY = "voice"
RATE_SETTINGS_KEY = "rate"

DEFAULT_VOICE_ID = "Adam"
DEFAULT_RATE = 1.0

MINIMUM_RATE = 0.5
MAXIMUM_RATE = 2.0


class VoicePreferenceStore:
    """Persist the voice and speed beside the other local preferences.

    A book carries its own voice and speed in its reading position, so this is
    only what the app starts from: a fresh launch, a book never opened, and
    text read from another app - the one path that has no book to remember it.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def load_voice(self) -> str:
        stored = load_settings(self.path).get(VOICE_SETTINGS_KEY)
        if isinstance(stored, str) and stored:
            return stored
        return DEFAULT_VOICE_ID

    def load_rate(self) -> float:
        stored = load_settings(self.path).get(RATE_SETTINGS_KEY)
        # A hand-edited file, or one written by a build with a wider range, must
        # not reach the audio sink: it refuses anything outside this range, and
        # it would do so from inside a Qt slot where nothing catches it.
        if not isinstance(stored, (int, float)):
            return DEFAULT_RATE
        # A bool needs no case of its own: True is 1.0, which is the default
        # anyway, and False is out of range.
        if MINIMUM_RATE <= float(stored) <= MAXIMUM_RATE:
            return float(stored)
        return DEFAULT_RATE

    def save(self, voice_id: str, rate: float) -> bool:
        return update_settings(
            self.path,
            {VOICE_SETTINGS_KEY: voice_id, RATE_SETTINGS_KEY: rate},
        )
