"""OpenAI's speech endpoint, over the standard library.

`urllib` on purpose: this app ships a frozen sidecar to people's Macs, and a
new dependency for one POST is weight in every download plus one more thing
whose licence has to be accounted for. The request is a JSON body and a
bearer header.

The key never appears in an exception raised from here. OpenAI's 401 body
does not currently echo the credential, but "currently" is not a guarantee
worth a reader's key, so every message out of this module goes through
`redacted()` first.
"""

from __future__ import annotations

import json
from typing import Callable, Iterator
import urllib.error
import urllib.request

from .provider import ExternalVoiceError, ProviderVoice
from .secrets import redacted

ENDPOINT = "https://api.openai.com/v1/audio/speech"
#: Free, authenticated, and returns quickly - the standard way to ask "is
#: this key real?" without buying any audio to find out.
MODELS = "https://api.openai.com/v1/models"

#: The 13 voices `gpt-4o-mini-tts` takes. The four the older `tts-1` pair
#: could not say - ballad, verse, marin, cedar - are here because that pair is
#: gone: OpenAI calls this "our newest and most reliable text-to-speech
#: model", and "for best quality, we recommend using `marin` or `cedar`", so
#: those two head the catalogue [fetched 2026-09-10]. The voices panel sorts
#: what it is given - Vietnamese first, then alphabetically - so this order
#: is what everything else reads, not what that list shows.
#:
#: The caveat that comes with them, and it matters in a Vietnamese reader:
#: the endpoint's language list is Whisper's - Vietnamese is on it - but the
#: same page says the voices are "optimized for English". A Vietnamese book
#: will be read in a Vietnamese accented by that.
#: The third column is GENDER, and it is not OpenAI's word - it is this
#: app's. OpenAI publishes names only: their text-to-speech guide, their
#: realtime guide and Microsoft's Azure documentation all describe a voice's
#: character ("deep and authoritative", "bright and energetic") and none of
#: them states a gender [fetched 2026-09-10]. So there was nothing to read,
#: and with thirteen unlabelled voices the Nam/Nữ filter matched none of them
#: - which read on screen as "OpenAI has no male voices" (owner asked exactly
#: that, 10/09, then asked for the labels, 11/09).
#:
#: What makes this safe enough to ship: gender is NEVER printed beside a
#: voice. There is no badge for it - only 💵, 🇻🇳 and 🇬🇧 reach the row. It
#: exists to make a list of thirteen searchable, and the cost of a wrong
#: guess is one preview under a cent, free to repeat.
#:
#: `alloy` is deliberately left out: every description of it says neutral,
#: and one says it "could also pass for feminine". A voice the sources
#: themselves will not place is one this table does not place either - the
#: panel counts it and says so.
VOICES: tuple[tuple[str, str, str | None], ...] = (
    ("marin", "Marin", "female"),
    ("cedar", "Cedar", "male"),
    ("alloy", "Alloy", None),
    ("ash", "Ash", "male"),
    ("ballad", "Ballad", "male"),
    ("coral", "Coral", "female"),
    ("echo", "Echo", "male"),
    ("fable", "Fable", "male"),
    ("nova", "Nova", "female"),
    ("onyx", "Onyx", "male"),
    ("sage", "Sage", "female"),
    ("shimmer", "Shimmer", "female"),
    ("verse", "Verse", "male"),
)

Opener = Callable[[urllib.request.Request], object]


class OpenAIVoiceProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini-tts",
        *,
        opener: Opener | None = None,
        timeout: float = 60.0,
    ):
        self._key = api_key
        self._model = model
        self._opener = opener or (lambda request: urllib.request.urlopen(request, timeout=timeout))
        self._cancelled = False

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def voices(self) -> tuple[ProviderVoice, ...]:
        return tuple(
            ProviderVoice(
                id=identifier,
                label=f"{label} · OpenAI",
                model=self._model,
                gender=gender,  # type: ignore[arg-type]
            )
            for identifier, label, gender in VOICES
        )

    def cancel(self) -> None:
        self._cancelled = True

    def verify(self) -> None:
        """Is this key usable? Raises `ExternalVoiceError` if not.

        `voices()` above cannot answer that - the nine names are a constant
        and never leave this machine - so the app used to accept ANY non-empty
        string as an OpenAI key and tell the reader it had been checked. It
        was then read time, mid-chapter, that found out. This asks the
        cheapest authenticated question the API has instead.
        """

        request = urllib.request.Request(
            MODELS,
            headers={"Authorization": f"Bearer {self._key}"},
            method="GET",
        )
        try:
            response = self._opener(request)
        except urllib.error.HTTPError as error:
            raise self._from_status(error) from None
        except (urllib.error.URLError, TimeoutError) as error:
            raise ExternalVoiceError(
                "network", redacted(getattr(error, "reason", error), self._key)
            ) from None
        with response:  # type: ignore[union-attr]
            response.read()  # type: ignore[union-attr]

    def synthesize(self, text: str, voice_id: str) -> Iterator[bytes]:
        self._cancelled = False
        body = json.dumps({
            # Only the words. No book title, no identifier, no reader: the
            # provider is told what to say and nothing about who is reading.
            "model": self._model,
            "voice": voice_id,
            "input": text,
            "response_format": "pcm",
        }).encode("utf-8")
        request = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            response = self._opener(request)
        except urllib.error.HTTPError as error:
            raise self._from_status(error) from None
        except urllib.error.URLError as error:
            raise ExternalVoiceError(
                "network", redacted(getattr(error, "reason", error), self._key)
            ) from None
        except TimeoutError as error:
            raise ExternalVoiceError("network", redacted(error, self._key)) from None

        with response:  # type: ignore[union-attr]
            while True:
                if self._cancelled:
                    return
                piece = response.read(16_384)  # type: ignore[union-attr]
                if not piece:
                    return
                yield piece

    def _from_status(self, error: urllib.error.HTTPError) -> ExternalVoiceError:
        try:
            payload = json.loads(error.read().decode("utf-8", "replace"))
            detail = str(payload.get("error", {}).get("message", ""))
            reason = str(payload.get("error", {}).get("code", ""))
        except Exception:  # noqa: BLE001 - an error page is not always JSON
            detail, reason = "", ""
        message = redacted(detail or error.reason or "", self._key)
        status = error.code
        if status in (401, 403):
            return ExternalVoiceError("bad_key", message)
        if status == 429:
            # OpenAI answers 429 both for "slow down" and for "you have run
            # out", and they lead to different actions - the body is the only
            # thing that tells them apart.
            code = "quota" if "quota" in reason or "quota" in detail.lower() else "rate_limit"
            return ExternalVoiceError(code, message)
        if 500 <= status < 600:
            return ExternalVoiceError("provider_down", message)
        return ExternalVoiceError("refused", message)
