"""Which build of the reading model this Mac uses."""

from __future__ import annotations

import os
from pathlib import Path

from vieneu_reader.settings import load_settings, update_settings

from .vieneu import DEFAULT_PRECISION, PRECISIONS


SETTINGS_KEY = "voice_quality"
ENVIRONMENT_KEY = "READEASE_PRECISION"

# What each build costs, so the choice can be presented honestly rather than as
# a bare technical word. Measured on an Apple Silicon Mac, 2026-08-29.
DOWNLOAD_MEGABYTES = {"int8": 158, "fp32": 453}

# What the first-time download comes to once the shared audio codec and the
# fetch cache are counted, which is the number the setup screen promises.
# Measured on an Apple Silicon Mac, 2026-08-29: codec 86 MB, caches ~87 MB.
TOTAL_DOWNLOAD_MEGABYTES = {"int8": 330, "fp32": 625}


class VoiceQualityPreferenceStore:
    """Persist the chosen model build beside the other local preferences."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> str:
        # An environment override wins, so a build can be tried without
        # touching the saved choice.
        chosen = os.environ.get(ENVIRONMENT_KEY) or load_settings(self.path).get(
            SETTINGS_KEY
        )
        if isinstance(chosen, str) and chosen in PRECISIONS:
            return chosen
        return DEFAULT_PRECISION

    def save(self, precision: str) -> bool:
        if precision not in PRECISIONS:
            raise ValueError(f"unknown precision: {precision!r}")
        return update_settings(self.path, {SETTINGS_KEY: precision})
