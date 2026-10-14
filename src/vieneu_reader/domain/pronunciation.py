"""The reader's own pronunciations: how a written word should be SAID.

A voice model reads a brand, an acronym or an English loanword inside a
Vietnamese sentence by its own guess, and the guess is the error a person
hears most. The reader writes the word as it is written and as it should be
said - "ReadEase" → "rít ít", "AI" → "ây ai" - and every reading says it that
way: books, pasted text, a selection, an export.

Applied to the words BEFORE they are made speakable, so what the reader
typed is matched against what they see, and the voice, the estimate and the
audio cache key all move together (the cache keys on the sentence as sent,
so a changed entry is never answered with the old audio). What a reader SEES
- the page, a subtitle - never changes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

# Bounds on what a settings file may make the engine do: a pattern built from
# hundreds of long alternatives is still fast, an unbounded one is not.
MAX_ENTRIES = 300
MAX_WRITTEN = 80
MAX_SPOKEN = 200


@dataclass(frozen=True)
class Entry:
    written: str
    spoken: str


def entries_of(value: Any) -> tuple[Entry, ...]:
    """The usable entries in a stored value, in order; anything malformed is
    skipped rather than refused, so one bad row never silences the rest.

    Accepts the list the shell stores, or that list as a JSON string. A word
    written twice keeps its LAST spelling - the one the reader typed later.
    """

    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else []
        except json.JSONDecodeError:
            return ()
    if not isinstance(value, list):
        return ()
    kept: dict[str, Entry] = {}
    for row in value:
        if not isinstance(row, dict):
            continue
        written = " ".join(str(row.get("written") or "").split())
        spoken = " ".join(str(row.get("spoken") or "").split())
        if not written or not spoken or len(written) > MAX_WRITTEN or len(spoken) > MAX_SPOKEN:
            continue
        kept.pop(written.casefold(), None)
        kept[written.casefold()] = Entry(written, spoken)
    return tuple(kept.values())[-MAX_ENTRIES:]


class Pronunciations:
    """Whole-word, case-insensitive, longest first.

    Whole word: "AI" must not change "SAI" or "AIDS"; Vietnamese syllables
    are separate words already, so a syllable entry never reaches inside
    another. Longest first: "Google Docs" wins over "Google" where both are
    written.
    """

    def __init__(self, entries: tuple[Entry, ...] = ()) -> None:
        self._spoken = {entry.written.casefold(): entry.spoken for entry in entries}
        if not entries:
            self._pattern = None
            return
        alternatives = sorted({entry.written for entry in entries}, key=len, reverse=True)
        self._pattern = re.compile(
            r"(?<!\w)(?:" + "|".join(re.escape(word) for word in alternatives) + r")(?!\w)",
            re.IGNORECASE,
        )

    def __bool__(self) -> bool:
        return self._pattern is not None

    def apply(self, text: str) -> str:
        if self._pattern is None or not text:
            return text
        return self._pattern.sub(lambda match: self._spoken[match.group(0).casefold()], text)


NONE = Pronunciations()


def pronunciations_of(document: dict[str, Any]) -> Pronunciations:
    """The reader's pronunciations from the settings document."""

    entries = entries_of(document.get("pronunciations"))
    return Pronunciations(entries) if entries else NONE
