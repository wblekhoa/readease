"""How long the rest of a reading will take to hear (HIG 3.24).

The characters are exact - the same `speakable_text` strings the engine
sends - and so are the seconds of audio it has already produced, silences
included, after the time-stretcher. Dividing one by the other is the pace
of THIS voice on THIS Mac at THIS rate, and it corrects itself as the
reading goes on. Until enough has been heard to trust that, a default per
language stands in, measured 21/09 on the shipped models with two invented
passages each (VieNeu, Minh Đức, fp32: 14.66 and 14.45 chars/s; Kokoro,
af_heart: 16.33 and 16.00 chars/s; predicting the second passage from the
first was off by -1.4 % and -2.0 %).
"""

from __future__ import annotations

from dataclasses import dataclass

#: Characters spoken per second at rate 1.0, by reading language.
DEFAULT_CHARS_PER_SECOND: dict[str, float] = {"vi": 14.5, "en": 16.0}
#: Below this much heard (at rate 1.0), the default outranks the measurement:
#: one short heading says nothing about the chapter after it.
SETTLED_SECONDS = 10.0


@dataclass
class Pace:
    """What one voice has been measured to do, normalised to rate 1.0."""

    chars: int = 0
    seconds: float = 0.0

    def add(self, chars: int, seconds: float, rate: float = 1.0) -> None:
        """Count `chars` that took `seconds` to hear at `rate`."""

        if chars <= 0 or seconds <= 0:
            return
        self.chars += chars
        self.seconds += seconds * rate

    @property
    def settled(self) -> bool:
        return self.chars > 0 and self.seconds >= SETTLED_SECONDS

    def seconds_for(self, chars: int, *, rate: float = 1.0, language: str = "vi") -> int:
        """How long `chars` will take to hear at `rate`, in whole seconds."""

        if chars <= 0:
            return 0
        rate = rate if rate > 0 else 1.0
        if self.settled:
            per_char = self.seconds / self.chars
        else:
            fallback = DEFAULT_CHARS_PER_SECOND.get(language) or DEFAULT_CHARS_PER_SECOND["vi"]
            per_char = 1.0 / fallback
        return int(round(chars * per_char / rate))
