"""What an outside voice service has to be able to do, and how it fails.

One protocol for every provider, and one small vocabulary of failures. The
vocabulary matters more than it looks: "something went wrong" is useless to
somebody who is mid-chapter and has just been charged, whereas "the key was
refused" and "you are out of credit" lead to different next actions, and
"the network dropped" leads to trying again. The shell turns each code into
one sentence in the reader's language; nothing here is a display string.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, Protocol

from vieneu_reader.domain.models import Voice

#: Sample rate every provider is asked for. Both OpenAI (`response_format=
#: "pcm"`) and ElevenLabs (`output_format=pcm_24000`) hand back signed
#: 16-bit little-endian mono at this rate, so the conversion is one path.
PROVIDER_SAMPLE_RATE = 24_000

ErrorCode = Literal[
    "bad_key",        # the credential was refused - re-enter it
    "quota",          # out of credit, or over the account's own cap - top up
    "rate_limit",     # too fast; the same request may work in a moment
    "network",        # never reached them; nothing was charged
    "provider_down",  # reached them and they broke (5xx) - not the reader's fault
    "refused",        # they understood and said no (moderation, bad input)
    "budget",         # OUR ceiling, not theirs: nothing was sent
]


class ExternalVoiceError(Exception):
    """A provider failure that the shell can say something useful about.

    `message` has already been through `redacted()` by the provider that
    raised it - nothing carrying a key gets this far.
    """

    def __init__(self, code: ErrorCode, message: str = ""):
        super().__init__(message or code)
        self.code: ErrorCode = code
        self.message = message or code


@dataclass(frozen=True, slots=True)
class ProviderVoice:
    """One voice a provider offers, in the shape the catalogue needs."""

    id: str
    label: str
    model: str

    def as_voice(self, provider: str) -> Voice:
        # Namespaced, because a provider's "Alloy" and the local catalogue
        # must never collide in a shortlist or a cache key.
        return Voice(id=f"{provider}:{self.id}", label=self.label)


class ExternalVoiceProvider(Protocol):
    """A paid text-to-speech service, on the reader's own account."""

    @property
    def name(self) -> str:
        """Stable id: "openai", "elevenlabs"."""

    @property
    def model(self) -> str:
        """Which model this instance speaks with - part of the cache key."""

    def voices(self) -> tuple[ProviderVoice, ...]: ...

    def synthesize(self, text: str, voice_id: str) -> Iterator[bytes]:
        """Signed 16-bit little-endian mono at PROVIDER_SAMPLE_RATE.

        Yields as the bytes arrive so a long sentence starts sounding before
        it is finished. Raises ExternalVoiceError, never a bare HTTP error.
        """

    def cancel(self) -> None:
        """Abandon whatever is in flight. Called when the reader stops."""
