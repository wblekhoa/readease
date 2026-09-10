"""What an outside voice costs, as data with a date on it.

Nothing here is computed from a provider's API - they do not publish a price
endpoint - so every number is a quotation with a day attached, and the shell
shows that day beside the figure. A price that moved is then a visible
staleness rather than a silent wrong number, and updating it is editing one
table. The day sits on the ROW, not on the table: re-checking OpenAI must not
stamp today's date onto an ElevenLabs figure nobody looked at.

  OpenAI      gpt-4o-mini-tts   $0.60 / 1M text-input tokens
                                $12.00 / 1M audio-output tokens
                                [fetched 2026-09-10]
  ElevenLabs  v3        $0.10 / 1k characters   (1 credit ~ 1 character)
              flash     $0.05 / 1k characters   [fetched 2026-09-04]

OpenAI's newest speech model bills by TOKEN, so unlike every other row its
price cannot be counted off the text. `usd_per_1k_chars` for it is therefore
an ESTIMATE, and `billing` says so - see the row for where the number comes
from and what the interface must not promise on top of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

#: The day the table as a whole was last reviewed. Rows carry their own.
PRICES_FETCHED = "2026-09-10"

#: "counted" - the provider bills the characters this app can count, so the
#: figure is arithmetic and may be quoted as a ceiling.
#: "estimated" - the provider bills something this app cannot count (tokens
#: of generated audio), so the figure rests on a stated assumption and the
#: interface may only ever call it approximate.
Billing = Literal["counted", "estimated"]


@dataclass(frozen=True, slots=True)
class VoicePrice:
    provider: str
    model: str
    label: str
    usd_per_1k_chars: float
    # What the provider's own dashboard counts down: ElevenLabs bills
    # credits (~1 per character), older OpenAI models billed characters, and
    # the current one bills tokens of audio. A TOKEN, not a word - saying it
    # in the reader's language is the interface's job, and a Vietnamese
    # string down here would reach a screen untranslated.
    unit: str
    billing: Billing
    fetched: str

    def usd_for(self, chars: int) -> float:
        return chars * self.usd_per_1k_chars / 1000.0

    def units_for(self, chars: int) -> int:
        """How many of the provider's own units this text will spend.

        Zero means "cannot be said": a token-billed model spends tokens of
        generated audio, and nobody can count those from the text. The shell
        leaves the line off rather than printing a character count under a
        word that means something else.
        """

        if self.billing == "estimated":
            return 0
        return chars


PRICES: tuple[VoicePrice, ...] = (
    # $12 / 1M audio-output tokens, and an audio token is a slice of TIME, so
    # the cost per character is really a cost per minute divided by how fast
    # the model reads. One public measurement against OpenAI's own costs
    # endpoint: 4,096 characters of English became 268 seconds of audio and
    # was billed $0.0652 - $15.9 per 1M characters, about 917 characters a
    # minute (s-anand.net/blog/openai-tts-cost, [fetched 2026-09-10]).
    #
    # The row quotes $20 per 1M instead of that $15.9 on purpose. This app
    # reads Vietnamese, whose pace nobody here has measured, and a slower
    # reading buys more audio per character - so the figure would sit under
    # the truth exactly where it matters, in `SpendMeter.would_exceed`, which
    # is the reader's ceiling. Overshooting stops a reading early; undershoot-
    # ing spends past the limit they set. The interface never calls this
    # number a maximum (`billing="estimated"`).
    VoicePrice(
        "openai", "gpt-4o-mini-tts", "OpenAI · gpt-4o-mini-tts",
        0.020, "tokens", "estimated", "2026-09-10",
    ),
    VoicePrice(
        "elevenlabs", "eleven_v3", "ElevenLabs · v3",
        0.100, "credits", "counted", "2026-09-04",
    ),
    VoicePrice(
        "elevenlabs", "eleven_flash_v2_5", "ElevenLabs · Flash",
        0.050, "credits", "counted", "2026-09-04",
    ),
)

_BY_MODEL = {price.model: price for price in PRICES}


def price_for(model: str) -> VoicePrice | None:
    return _BY_MODEL.get(model)
