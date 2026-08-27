"""Speech engine boundary and local audio cache."""

from .cache import AudioCache, audio_cache_key
from .contracts import SpeechEngine, SynthesisSettings
from .vieneu import (
    CODEC_REVISION,
    ENGINE_VERSION,
    MODEL_REVISION,
    ModelNotReadyError,
    ModelPreparationError,
    VieNeuSpeechEngine,
)

__all__ = [
    "AudioCache",
    "CODEC_REVISION",
    "ENGINE_VERSION",
    "MODEL_REVISION",
    "ModelNotReadyError",
    "ModelPreparationError",
    "SpeechEngine",
    "SynthesisSettings",
    "VieNeuSpeechEngine",
    "audio_cache_key",
]
