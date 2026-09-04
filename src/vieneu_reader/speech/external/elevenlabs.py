"""ElevenLabs' speech endpoint, over the standard library.

Same shape as `openai.py` and for the same reason - a frozen sidecar should
not carry an SDK for two HTTP calls - but the service differs in three ways
that matter, and each one is a place a naive copy would go wrong.

**The catalogue is a network call.** OpenAI's nine voices are a constant;
here they are whatever this account owns, so `voices()` can fail, can be
slow, and can be paginated. Everything that lists voices has to survive that.

**The failure is in the BODY, not the status.** ElevenLabs answers 401 both
for a key that is wrong and for an account that is out of credit
[fetched 2026-09-04], and those lead to opposite actions - re-enter the key,
or go and top up. Reading the status alone would tell a reader who has run
out that their key is bad. So `detail.status` decides, and the HTTP code is
only the fallback for a body that is not the documented shape.

**`output_format` is a query parameter**, not a body field, and logging is
opt-out per request rather than per account.

API facts [fetched 2026-09-04, elevenlabs.io/docs]:
  POST /v1/text-to-speech/{voice_id}/stream?output_format=…&enable_logging=…
  GET  /v2/voices  ->  {voices: [{voice_id, name, category}], next_page_token}
  header `xi-api-key`; body {text, model_id}
"""

from __future__ import annotations

import json
from typing import Callable, Iterator
import urllib.error
import urllib.parse
import urllib.request

from .provider import ExternalVoiceError, ProviderVoice
from .secrets import redacted

API = "https://api.elevenlabs.io"

#: The catalogue is paged. A reader with a big cloned-voice library should
#: not turn one settings panel into forty requests, and a list nobody can
#: scan is not more useful than a long one - so it stops, and stops at a
#: round number rather than at whatever the first page happened to hold.
MAX_VOICES = 60
_PAGE = 100

#: Zero-retention: the words are not kept by the provider for review. It is
#: sent on every request rather than assumed from the account, because it is
#: the app that made the promise about where the reader's book goes.
LOGGING = "false"

#: What the provider calls the thing that went wrong, mapped to what the
#: reader can do about it. `detail.status` strings, [fetched 2026-09-04].
BY_STATUS = {
    "invalid_api_key": "bad_key",
    "missing_api_key": "bad_key",
    "quota_exceeded": "quota",
    "detected_unusual_activity": "refused",
    "max_character_limit_exceeded": "refused",
    "invalid_uid": "refused",
    "voice_not_found": "refused",
}

Opener = Callable[[urllib.request.Request], object]


class ElevenLabsVoiceProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "eleven_flash_v2_5",
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
        return "elevenlabs"

    @property
    def model(self) -> str:
        return self._model

    def cancel(self) -> None:
        self._cancelled = True

    def _get(self, path: str) -> dict:
        request = urllib.request.Request(
            f"{API}{path}", headers={"xi-api-key": self._key}, method="GET"
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
            body = response.read()  # type: ignore[union-attr]
        try:
            return json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            # A 200 that is not JSON is the shape of a captive portal or a
            # proxy, not of this API. Saying "provider_down" would blame
            # them for something that happened on the way.
            raise ExternalVoiceError("network", "unreadable reply") from None

    def voices(self) -> tuple[ProviderVoice, ...]:
        """The account's own voices. Raises, because this one really can."""

        found: list[ProviderVoice] = []
        token = ""
        while True:
            query = urllib.parse.urlencode(
                {"page_size": _PAGE, **({"next_page_token": token} if token else {})}
            )
            payload = self._get(f"/v2/voices?{query}")
            for entry in payload.get("voices") or ():
                identifier = str(entry.get("voice_id") or "")
                if not identifier:
                    continue
                found.append(
                    ProviderVoice(
                        id=identifier,
                        label=f"{entry.get('name') or identifier} · ElevenLabs",
                        model=self._model,
                    )
                )
                if len(found) >= MAX_VOICES:
                    return tuple(found)
            token = str(payload.get("next_page_token") or "")
            if not payload.get("has_more") or not token:
                return tuple(found)

    def verify(self) -> None:
        """Is this key usable? Raises `ExternalVoiceError` if not.

        Listing voices is the check: it is the cheapest authenticated call
        the app already needs, and a key that cannot list voices cannot read
        a book either.
        """

        self.voices()

    def synthesize(self, text: str, voice_id: str) -> Iterator[bytes]:
        self._cancelled = False
        query = urllib.parse.urlencode(
            {"output_format": "pcm_24000", "enable_logging": LOGGING}
        )
        body = json.dumps({
            # The words and which voice says them. Nothing about the book,
            # the reader or this machine.
            "text": text,
            "model_id": self._model,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{API}/v1/text-to-speech/{urllib.parse.quote(voice_id)}/stream?{query}",
            data=body,
            headers={"xi-api-key": self._key, "Content-Type": "application/json"},
            method="POST",
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
            while True:
                if self._cancelled:
                    return
                piece = response.read(16_384)  # type: ignore[union-attr]
                if not piece:
                    return
                yield piece

    def _from_status(self, error: urllib.error.HTTPError) -> ExternalVoiceError:
        """The body first, the status only when the body will not say.

        401 means "wrong key" AND "out of credit" here, so a reader who has
        simply run out would otherwise be sent to re-enter a key that was
        fine all along.
        """

        status_word, detail = "", ""
        try:
            payload = json.loads(error.read().decode("utf-8", "replace"))
            inner = payload.get("detail")
            if isinstance(inner, dict):
                status_word = str(inner.get("status") or "")
                detail = str(inner.get("message") or "")
            elif isinstance(inner, str):
                detail = inner
        except Exception:  # noqa: BLE001 - an error page is not always JSON
            pass
        message = redacted(detail or error.reason or "", self._key)
        named = BY_STATUS.get(status_word)
        if named is not None:
            return ExternalVoiceError(named, message)  # type: ignore[arg-type]
        code = error.code
        if code in (401, 403):
            return ExternalVoiceError("bad_key", message)
        if code == 429:
            return ExternalVoiceError("rate_limit", message)
        if 500 <= code < 600:
            return ExternalVoiceError("provider_down", message)
        return ExternalVoiceError("refused", message)
