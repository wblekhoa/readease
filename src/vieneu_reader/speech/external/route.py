"""Which engine speaks this voice - decided once, in one pure function.

The workspace has paid for the alternative already: when the same
local-or-paid branch is retyped at the call site, at the button that starts
it, at the label, and at the estimate, they drift, and the drift shows up as
a button that offers something the engine then refuses (lesson
`hosted-vs-byok-route-picker-pure-function`). So the decision is data in,
verdict out, and every caller asks the same question.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

#: Which settings key holds which provider's credential.
KEY_FOR_PROVIDER: Mapping[str, str] = {
    "openai": "openai_api_key",
    "elevenlabs": "elevenlabs_api_key",
}

BlockedReason = Literal["no_key", "budget"]


@dataclass(frozen=True, slots=True)
class Route:
    kind: Literal["local", "external", "blocked"]
    provider: str | None = None
    reason: BlockedReason | None = None


def provider_of(voice_id: str) -> str | None:
    """The provider a voice id names, or None for a local voice.

    Paid voices are `provider:model:voice` so they can never collide with the
    local catalogue, and so the price can be read off the id itself. A bare
    name is the local model's.
    """

    if ":" not in voice_id:
        return None
    provider = voice_id.split(":", 1)[0]
    return provider if provider in KEY_FOR_PROVIDER else None


def model_of(voice_id: str) -> str | None:
    """The provider's model, which is what the price is per."""

    parts = voice_id.split(":")
    if len(parts) < 3 or parts[0] not in KEY_FOR_PROVIDER:
        return None
    return parts[1]


def pick_voice_route(
    voice_id: str,
    *,
    keys: Mapping[str, object],
    would_exceed_budget: bool = False,
) -> Route:
    """Where this voice's audio should come from.

    `keys` is the settings document, so the caller does not have to know
    which key belongs to which provider.
    """

    provider = provider_of(voice_id)
    if provider is None:
        return Route("local")
    if not keys.get(KEY_FOR_PROVIDER[provider]):
        return Route("blocked", provider=provider, reason="no_key")
    if would_exceed_budget:
        # Checked before anything is sent, so the ceiling holds rather than
        # being noticed on the way back.
        return Route("blocked", provider=provider, reason="budget")
    return Route("external", provider=provider)
