"""The sole adapter from VieNeu-TTS SDK objects to reader audio contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
from contextlib import contextmanager
from threading import RLock
from typing import Any, Callable, Iterator

from vieneu_reader.domain.models import AudioChunk, Voice
from vieneu_reader.domain.segmenter import normalize_paragraph

from .contracts import SynthesisSettings


ENGINE_VERSION = "3.3.0"
MODEL_REVISION = "2da0efab622a1722125991736524f080b751ef5b"
MODEL_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
MODEL_DIRECTORY = "vieneu-v3-turbo"
MODEL_SUBFOLDER = "onnx_int8"
MODEL_FILES = (
    "vieneu_prefill.onnx",
    "vieneu_decode_step.onnx",
    "vieneu_acoustic_cached.onnx",
    "vieneu_backbone_shared.data",
    "vieneu_v3_heads.npz",
    "config.json",
    "tokenizer.json",
)
CODEC_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"
CODEC_REVISION = "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae"
CODEC_DIRECTORY = "moss-audio-tokenizer-nano-onnx"
CODEC_FILES = (
    "moss_audio_tokenizer_decode_full.onnx",
    "moss_audio_tokenizer_decode_shared.data",
    "moss_audio_tokenizer_decode_step.onnx",
    "codec_browser_onnx_meta.json",
    "moss_audio_tokenizer_encode.onnx",
    "moss_audio_tokenizer_encode.data",
)
_READY_MARKER = ".vieneu-ready.json"
_SDK_LOAD_LOCK = RLock()


class ModelPreparationError(RuntimeError):
    """The local model could not be prepared for offline synthesis."""


class ModelNotReadyError(RuntimeError):
    """Synthesis was requested before explicit model preparation."""


@contextmanager
def _local_codec_downloads(codec_directory: Path) -> Iterator[None]:
    """Route VieNeu's unpinned codec lookup to the verified local snapshot."""

    import huggingface_hub

    directory = Path(codec_directory)
    original_download = huggingface_hub.hf_hub_download

    def local_download(
        repo_id: str,
        filename: str,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if repo_id != CODEC_REPO:
            raise FileNotFoundError("network access is disabled for the prepared SDK")
        if kwargs.get("subfolder") not in (None, "") or filename not in CODEC_FILES:
            raise FileNotFoundError("VieNeu requested an unknown codec asset")
        candidate = directory / filename
        if not candidate.is_file() or candidate.stat().st_size < 1:
            raise FileNotFoundError(f"missing pinned codec asset: {filename}")
        return str(candidate)

    with _SDK_LOAD_LOCK:
        huggingface_hub.hf_hub_download = local_download
        try:
            yield
        finally:
            huggingface_hub.hf_hub_download = original_download


def _load_sdk(*, codec_dir: str | None = None, **kwargs: Any) -> Any:
    from vieneu import Vieneu

    if codec_dir is None:
        return Vieneu(**kwargs)
    with _local_codec_downloads(Path(codec_dir)):
        return Vieneu(**kwargs)


def _download_snapshot(**kwargs: Any) -> str:
    from huggingface_hub import snapshot_download

    return snapshot_download(**kwargs)


class VieNeuSpeechEngine:
    def __init__(
        self,
        models_path: Path,
        sdk_factory: Callable[..., Any] | None = None,
        model_downloader: Callable[..., str] | None = None,
    ):
        self._models_path = Path(models_path)
        self._models_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._models_path.chmod(0o700)
        self._requires_prepared_model = sdk_factory is None
        self._sdk_factory = sdk_factory or _load_sdk
        self._model_downloader = model_downloader or _download_snapshot
        self._sdk: Any | None = None
        self._lock = RLock()
        self._generation = 0

    @property
    def engine_version(self) -> str:
        return ENGINE_VERSION

    @property
    def model_revision(self) -> str:
        return MODEL_REVISION

    @property
    def _model_root(self) -> Path:
        return self._models_path / MODEL_DIRECTORY

    @property
    def _onnx_directory(self) -> Path:
        return self._model_root / MODEL_SUBFOLDER

    @property
    def _codec_root(self) -> Path:
        return self._models_path / CODEC_DIRECTORY

    @property
    def _ready_marker(self) -> Path:
        return self._models_path / _READY_MARKER

    def _assets_present(self) -> bool:
        model_present = all(
            (self._onnx_directory / filename).is_file()
            and (self._onnx_directory / filename).stat().st_size > 0
            for filename in MODEL_FILES
        )
        codec_present = all(
            (self._codec_root / filename).is_file()
            and (self._codec_root / filename).stat().st_size > 0
            for filename in CODEC_FILES
        )
        return model_present and codec_present

    def _marker_matches(self) -> bool:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self._ready_marker, flags)
        except OSError:
            return False
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or metadata.st_size > 4096
            ):
                return False
            payload = os.read(descriptor, 4097)
        finally:
            os.close(descriptor)
        try:
            marker = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return False
        return marker == {
            "codec_revision": CODEC_REVISION,
            "engine_version": ENGINE_VERSION,
            "model_revision": MODEL_REVISION,
        }

    @property
    def is_model_ready(self) -> bool:
        try:
            return self._assets_present() and self._marker_matches()
        except OSError:
            return False

    def _sdk_arguments(self, *, prepared: bool) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "mode": "v3turbo",
            "backend": "onnx",
            "precision": "int8",
        }
        if prepared:
            arguments.update(
                backbone_repo=str(self._model_root),
                onnx_dir=str(self._onnx_directory),
                codec_dir=str(self._codec_root),
            )
        return arguments

    def _write_ready_marker(self) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".vieneu-ready-",
            suffix=".tmp",
            dir=self._models_path,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            payload = json.dumps(
                {
                    "codec_revision": CODEC_REVISION,
                    "engine_version": ENGINE_VERSION,
                    "model_revision": MODEL_REVISION,
                },
                sort_keys=True,
            ).encode("utf-8")
            marker_file = os.fdopen(descriptor, "wb")
            descriptor = -1
            with marker_file:
                marker_file.write(payload)
                marker_file.flush()
                os.fsync(marker_file.fileno())
            temporary_path.replace(self._ready_marker)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    def _configure_huggingface_environment(self, *, offline: bool = False) -> None:
        os.environ["HF_HOME"] = str(self._models_path)
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("DO_NOT_TRACK", "1")
        if offline:
            os.environ["HF_HUB_OFFLINE"] = "1"

    def prepare_model(
        self,
        progress_callback: Callable[[float, str], None],
    ) -> None:
        """Download both pinned ONNX snapshots and validate offline readiness."""

        with self._lock:
            if self.is_model_ready:
                progress_callback(1.0, "Mô hình đọc tiếng Việt đã sẵn sàng.")
                return
            self._configure_huggingface_environment()
            progress_callback(0.0, "Đang tải mô hình đọc tiếng Việt lần đầu…")
            try:
                self._model_downloader(
                    repo_id=MODEL_REPO,
                    revision=MODEL_REVISION,
                    local_dir=str(self._model_root),
                    allow_patterns=[f"{MODEL_SUBFOLDER}/*"],
                )
                progress_callback(0.55, "Đang tải bộ giải mã âm thanh…")
                self._model_downloader(
                    repo_id=CODEC_REPO,
                    revision=CODEC_REVISION,
                    local_dir=str(self._codec_root),
                    allow_patterns=list(CODEC_FILES),
                )
                if not self._assets_present():
                    raise OSError("pinned snapshot is incomplete")
                progress_callback(0.75, "Đang kiểm tra bộ đọc tiếng Việt…")
                self._configure_huggingface_environment(offline=True)
                sdk = self._sdk_factory(**self._sdk_arguments(prepared=True))
                if not sdk.list_preset_voices():
                    raise RuntimeError("VieNeu exposes no preset voices")
                self._sdk = sdk
                self._write_ready_marker()
            except Exception as error:
                self._sdk = None
                raise ModelPreparationError(
                    "Không thể chuẩn bị mô hình đọc tiếng Việt. Hãy kiểm tra mạng và thử lại."
                ) from error
            progress_callback(1.0, "Mô hình đọc tiếng Việt đã sẵn sàng.")

    def _instance(self) -> Any:
        with self._lock:
            if self._sdk is None:
                prepared = self.is_model_ready
                self._configure_huggingface_environment(offline=prepared)
                if self._requires_prepared_model and not prepared:
                    raise ModelNotReadyError(
                        "Mô hình đọc tiếng Việt chưa được chuẩn bị."
                    )
                self._sdk = self._sdk_factory(
                    **self._sdk_arguments(prepared=prepared)
                )
            return self._sdk

    def voices(self) -> tuple[Voice, ...]:
        return tuple(
            Voice(id=voice_id, label=label)
            for label, voice_id in self._instance().list_preset_voices()
        )

    def stream(
        self,
        text: str,
        voice_id: str,
        settings: SynthesisSettings = SynthesisSettings(),
    ) -> Iterator[AudioChunk]:
        normalized = normalize_paragraph(text)
        if not normalized:
            raise ValueError("speech text cannot be empty")
        with self._lock:
            token = self._generation
        sdk = self._instance()
        raw_stream = sdk.infer_stream(
            normalized,
            voice=voice_id,
            temperature=settings.temperature,
            top_k=settings.top_k,
            top_p=settings.top_p,
            max_chars=settings.max_chars,
            repetition_penalty=settings.repetition_penalty,
        )
        for raw in raw_stream:
            with self._lock:
                if token != self._generation:
                    return
            if raw is None:
                continue
            if getattr(raw, "ndim", 1) != 1:
                raise ValueError("VieNeu returned non-mono audio")
            converted = raw.astype("<f4", copy=False)
            pcm = converted.tobytes()
            if pcm:
                if len(pcm) % 4:
                    raise ValueError("VieNeu returned incomplete float32 audio")
                yield AudioChunk(pcm=pcm)

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1
