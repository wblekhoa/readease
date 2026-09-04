"""What an outside voice costs, as data with a date on it.

Nothing here is computed from a provider's API - they do not publish a price
endpoint - so every number is a quotation with a day attached, and the shell
shows that day beside the figure. A price that moved is then a visible
staleness rather than a silent wrong number, and updating it is editing one
table.

Prices fetched 2026-09-04:
  OpenAI      tts-1     $15 / 1M characters
              tts-1-hd  $30 / 1M characters
  ElevenLabs  v3        $0.10 / 1k characters   (1 credit ~ 1 character)
              flash     $0.05 / 1k characters

`gpt-4o-mini-tts` is deliberately absent: it bills by TOKEN (~$0.015 per
minute of audio), so its cost cannot be counted off the text the way the
button needs. Adding it means adding a second kind of estimate, not a row.
"""

from __future__ import annotations

from dataclasses import dataclass

PRICES_FETCHED = "2026-09-04"


@dataclass(frozen=True, slots=True)
class VoicePrice:
    provider: str
    model: str
    label: str
    usd_per_1k_chars: float
    # What the provider's own dashboard counts down: ElevenLabs bills
    # credits (~1 per character), OpenAI bills characters. A TOKEN, not a
    # word - saying it in the reader's language is the interface's job, and
    # a Vietnamese string down here would reach a screen untranslated.
    unit: str

    def usd_for(self, chars: int) -> float:
        return chars * self.usd_per_1k_chars / 1000.0

    def units_for(self, chars: int) -> int:
        # Both providers currently count one unit per character sent.
        return chars


PRICES: tuple[VoicePrice, ...] = (
    VoicePrice("openai", "tts-1", "OpenAI · tts-1", 0.015, "characters"),
    VoicePrice("openai", "tts-1-hd", "OpenAI · tts-1-hd", 0.030, "characters"),
    VoicePrice("elevenlabs", "eleven_v3", "ElevenLabs · v3", 0.100, "credits"),
    VoicePrice("elevenlabs", "eleven_flash_v2_5", "ElevenLabs · Flash", 0.050, "credits"),
)

_BY_MODEL = {price.model: price for price in PRICES}


def price_for(model: str) -> VoicePrice | None:
    return _BY_MODEL.get(model)
