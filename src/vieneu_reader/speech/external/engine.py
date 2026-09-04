"""A paid provider, wearing the same face as the local model.

The whole point of this file is that nothing above it has to know. It
satisfies the same `SpeechEngine` protocol the VieNeu model does, yields the
same `AudioChunk`s at the same rate, and so travels the same road: the same
sentence loop, the same pauses and picture cues, the same time-stretching for
speed, the same audio cache, the same `stop`. The Rust host and the webview
were not changed by any of it.

Two conversions happen here and nowhere else:

* **s16le → float32.** Providers speak in 16-bit integers; everything past
  this point is float32, because that is what the player and the cache take.
* **24 kHz → 48 kHz.** Both providers top out at 24 kHz for PCM (ElevenLabs
  offers 44.1 kHz on Pro, which is not 48 either), and the app is 48 kHz from
  the player down to the cache's own validation. Linear interpolation on an
  exact 2x ratio: speech has little energy near 12 kHz, so the imaging it
  leaves is inaudible against the artefacts of the codec that made the audio.
  If that ever stops being true, this is the one function to replace.
"""

from __future__ import annotations

from typing import Iterator

import numpy as np

from vieneu_reader.domain.models import AudioChunk, Voice

from .contracts_shim import SynthesisSettings
from .provider import (
    PROVIDER_SAMPLE_RATE,
    ExternalVoiceError,
    ExternalVoiceProvider,
)

TARGET_SAMPLE_RATE = 48_000


def _decode(pcm_s16le: bytes) -> np.ndarray:
    if len(pcm_s16le) % 2:
        raise ValueError("s16le needs an even number of bytes")
    return np.frombuffer(pcm_s16le, dtype="<i2").astype(np.float32) / 32768.0


def _interleave(source: np.ndarray) -> np.ndarray:
    """Each sample of `source`, followed by the midpoint to the next one.

    Returns 2*(n-1) samples: the last input has no successor to aim at, so it
    is not emitted here. Whoever owns the stream decides whether another
    chunk is coming or the line has ended.
    """

    if source.size < 2:
        return np.empty(0, dtype=np.float32)
    doubled = np.empty((source.size - 1) * 2, dtype=np.float32)
    doubled[0::2] = source[:-1]
    doubled[1::2] = (source[:-1] + source[1:]) / 2.0
    return doubled


class Upsampler:
    """24 kHz s16le in, 48 kHz float32 out, across chunk boundaries.

    One sample of latency, and that is the whole design. Resampling each
    chunk on its own has to invent a successor for its final sample, which
    leaves a held value and a missing midpoint at every boundary - a click
    every few hundred milliseconds, which a listener blames on the voice.
    Holding one sample back until the next chunk arrives means every midpoint
    is computed between two real samples. `drain()` releases the last one
    when the sentence ends.
    """

    def __init__(self) -> None:
        self._pending = np.empty(0, dtype=np.float32)

    def feed(self, pcm_s16le: bytes) -> np.ndarray:
        samples = _decode(pcm_s16le)
        source = samples if self._pending.size == 0 else np.concatenate(
            (self._pending, samples)
        )
        if source.size == 0:
            return source
        self._pending = source[-1:]
        return _interleave(source)

    def drain(self) -> np.ndarray:
        """The final sample, held for its own two output slots."""

        if self._pending.size == 0:
            return self._pending
        tail = np.repeat(self._pending, 2).astype(np.float32)
        self._pending = np.empty(0, dtype=np.float32)
        return tail


def to_float32_48k(pcm_s16le: bytes) -> np.ndarray:
    """The whole of a finished piece of audio, in one call."""

    upsampler = Upsampler()
    return np.concatenate((upsampler.feed(pcm_s16le), upsampler.drain()))


class ExternalSpeechEngine:
    """`SpeechEngine` over an `ExternalVoiceProvider`."""

    def __init__(self, provider: ExternalVoiceProvider):
        self._provider = provider

    @property
    def engine_version(self) -> str:
        # Part of the audio cache key, which is why it names the provider:
        # a sentence bought from OpenAI must never be served as ElevenLabs'.
        return f"external:{self._provider.name}"

    @property
    def model_revision(self) -> str:
        return self._provider.model

    def voices(self) -> tuple[Voice, ...]:
        return tuple(
            voice.as_voice(self._provider.name) for voice in self._provider.voices()
        )

    def stream(
        self,
        text: str,
        voice_id: str,
        settings: SynthesisSettings = SynthesisSettings(),
    ) -> Iterator[AudioChunk]:
        """Speak one sentence, in chunks, as they arrive.

        `settings` belongs to the local model's sampler and means nothing to
        a provider; it is accepted and ignored so the seam stays one shape.
        """

        bare = voice_id.split(":", 1)[1] if ":" in voice_id else voice_id
        upsampler = Upsampler()
        remainder = b""
        for piece in self._provider.synthesize(text, bare):
            data = remainder + piece
            if len(data) % 2:
                # Keep the orphan byte for the next piece rather than
                # dropping it - one dropped byte shifts every sample after
                # it by half a sample and turns the rest into noise.
                data, remainder = data[:-1], data[-1:]
            else:
                remainder = b""
            if not data:
                continue
            audio = upsampler.feed(data)
            if audio.size:
                yield AudioChunk(pcm=audio.tobytes(), sample_rate=TARGET_SAMPLE_RATE)
        if remainder:
            raise ExternalVoiceError("refused", "provider sent an odd number of bytes")
        tail = upsampler.drain()
        if tail.size:
            yield AudioChunk(pcm=tail.tobytes(), sample_rate=TARGET_SAMPLE_RATE)

    def cancel(self) -> None:
        self._provider.cancel()
