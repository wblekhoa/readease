from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.domain.models import AudioChunk, Voice
from vieneu_reader.speech.self_check import run_tts_self_check


class _ReadyEngine:
    is_model_ready = True

    def __init__(self, models_path: Path, *, precision: str = "int8"):
        self.models_path = models_path
        self.precision = precision

    def voices(self) -> tuple[Voice, ...]:
        return (Voice(id="preset", label="Preset voice"),)

    def stream(self, text: str, voice_id: str):
        self.request = (text, voice_id)
        yield AudioChunk(pcm=(b"\x00\x00\x00?" * 4_800))


class _MissingModelEngine(_ReadyEngine):
    is_model_ready = False


class PackagedSpeechSelfCheckTests(unittest.TestCase):
    def test_ready_preset_engine_emits_non_silent_48khz_audio(self) -> None:
        with TemporaryDirectory() as temporary:
            output = StringIO()
            with redirect_stdout(output):
                result = run_tts_self_check(
                    Path(temporary),
                    engine_factory=_ReadyEngine,
                )

        self.assertEqual(result, 0)
        self.assertIn("TTS_SELF_CHECK PASS", output.getvalue())
        self.assertIn("sample_rate=48000", output.getvalue())

    def test_missing_model_fails_closed_without_downloading(self) -> None:
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "not prepared"):
                run_tts_self_check(
                    Path(temporary),
                    engine_factory=_MissingModelEngine,
                )


if __name__ == "__main__":
    unittest.main()
