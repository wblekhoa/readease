"""The English voice: Kokoro-82M through onnxruntime, behind the same seam
as the Vietnamese model.

Why a second local engine rather than a paid voice: the owner's rule is
that the Vietnamese model never reads English, and a book in English then
had nowhere to go without an API key. Kokoro-82M (Apache-2.0) was measured
against the alternatives on 15/09/2026 - `docs/english-voice-research-
2026-09-15.md` - and chosen for its voice; fp32 on four threads synthesises
at a third of real time on an M4 Max.

Ten files make the model, none in the bundle: the ONNX weights, the
tokenizer and six voice packs from a pinned Hugging Face revision, and the
two lexicon files the G2P reads, from a pinned commit of the library they
belong to. Each is fetched as a plain HTTPS download - not through the Hub
client, which the Vietnamese model switches to offline mode process-wide
once it is prepared, and which would then refuse this download on a
working network - checked against its pinned hash as it lands, and the
ready marker is written only after all of them matched and a trial
sentence produced audio. Readiness is that marker plus the files, exactly
as the Vietnamese model does it.

Audio leaves here as float32 at 48 kHz, in slices short enough for the
player's look-ahead, whatever the model produced - its 24 kHz is doubled by
the same interpolation the paid voices go through.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Iterator

import numpy as np

from vieneu_reader.domain.models import AudioChunk, Voice
from vieneu_reader.domain.segmenter import normalize_paragraph

from .contracts import SynthesisSettings

ENGINE_VERSION = "kokoro-onnx-1"
MODEL_REPO = "onnx-community/Kokoro-82M-v1.0-ONNX"
MODEL_REVISION = "1939ad2a8e416c0acfeecc08a694d14ef25f2231"
MODEL_DIRECTORY = "kokoro-82m-v1.0-onnx"
MODEL_URL = "https://huggingface.co/{repo}/resolve/{revision}/{name}"
MODEL_ONNX = "onnx/model.onnx"
TOKENIZER_FILE = "tokenizer.json"

#: What the model repo's own manifest says each file hashes to [fetched
#: 2026-09-15]; the small tokenizer is not stored as a large file there and
#: carries no published hash, so it is checked for shape instead.
MODEL_FILES: dict[str, str | None] = {
    MODEL_ONNX: "8fbea51ea711f2af382e88c833d9e288c6dc82ce5e98421ea61c058ce21a34cb",
    TOKENIZER_FILE: None,
    "voices/af_heart.bin": "d583ccff3cdca2f7fae535cb998ac07e9fcb90f09737b9a41fa2734ec44a8f0b",
    "voices/af_bella.bin": "f69d836209b78eb8c66e75e3cda491e26ea838a3674257e9d4e5703cbaf55c8b",
    "voices/af_nicole.bin": "cd2191ab31b914ed7b318416b0e4440fdf392ddad9106a060819aa600a64f59a",
    "voices/am_michael.bin": "1d1f21dd8da39c30705cd4c75d039d265e9bc4a2a93ed09bc9e1b1225eb95ba1",
    "voices/am_fenrir.bin": "c27989f741f7ee34d273a39d8a595cc0837d35f5ced9a29b7cc162614616df43",
    "voices/am_puck.bin": "fcf73c989033e9233e0b98713eca600c8c74dcc1614b37009d5450ff4a2274a0",
}

LEXICON_REPO = "hexgrad/misaki"
LEXICON_REVISION = "fba1236595f2d2bf21d414ba6e57d25256afada3"
LEXICON_DIRECTORY = "misaki-lexicon"
LEXICON_URL = "https://raw.githubusercontent.com/{repo}/{revision}/misaki/data/{name}"
LEXICON_FILES: dict[str, str] = {
    "us_gold.json": "dc414872a49a28ae6c141463d502fd945f3b2fde040484fdc47d00cc4612686f",
    "us_silver.json": "de8f67be911bb6c659187b4a65fd966b6a30e56350e0f790d763210b053ac475",
}

#: Roughly what the download comes to, for the settings row and the bar.
DOWNLOAD_BYTES = 335_000_000
#: How often a download reports, in bytes - and so how soon a cancel lands,
#: since the report is the only place one can.
REPORT_EVERY = 1 << 20

MODEL_SAMPLE_RATE = 24_000
TARGET_SAMPLE_RATE = 48_000
#: The model's position limit, minus the two padding tokens around a piece.
MAX_TOKENS = 508
#: Audio is handed over in slices this long, so the player's look-ahead
#: and a stop both work on a sentence-sized synthesis.
SLICE_SECONDS = 0.3
STYLE_WIDTH = 256
INTRA_OP_THREADS = 4

_READY_MARKER = ".kokoro-ready.json"
_MARKER_GATE = ("model_revision", "lexicon_revision")
_LOAD_LOCK = RLock()


@dataclass(frozen=True, slots=True)
class EnglishVoice:
    id: str
    name: str
    gender: str  # "male" | "female"
    accent: str  # the label's word for it

    @property
    def label(self) -> str:
        # The shape the Vietnamese catalogue uses - "Tên — Nữ · Bắc" - so the
        # shell reads the gender and the region off it the same way.
        gender = "Nữ" if self.gender == "female" else "Nam"
        return f"{self.name} — {gender} · {self.accent}"


#: American voices only, the ones the model's own card grades best
#: [fetched 2026-09-15]. British voices need the British lexicon, which is
#: another six megabytes and another vocabulary - not in this release.
VOICES: tuple[EnglishVoice, ...] = (
    EnglishVoice("af_heart", "Heart", "female", "Mỹ"),
    EnglishVoice("af_bella", "Bella", "female", "Mỹ"),
    EnglishVoice("af_nicole", "Nicole", "female", "Mỹ"),
    EnglishVoice("am_michael", "Michael", "male", "Mỹ"),
    EnglishVoice("am_fenrir", "Fenrir", "male", "Mỹ"),
    EnglishVoice("am_puck", "Puck", "male", "Mỹ"),
)
VOICE_IDS = frozenset(voice.id for voice in VOICES)


class EnglishModelError(RuntimeError):
    """The English model could not be prepared."""


class EnglishModelNotReadyError(RuntimeError):
    """Synthesis was requested before the English model was downloaded."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


#: Called with the bytes landed so far, as a download proceeds.
Progress = Callable[[int], None]


def _fetch(
    url: str,
    target: Path,
    expected_sha256: str | None,
    progress: Progress | None = None,
) -> None:
    """One file, to a temp name beside the target, checked, then renamed.

    `progress` is called every megabyte; whatever it raises - a cancel -
    leaves nothing behind, since the temp file goes in the `finally`."""

    import requests

    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".download-", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        digest = hashlib.sha256()
        landed = 0
        reported = 0
        with os.fdopen(descriptor, "wb") as handle:
            with requests.get(url, stream=True, timeout=60) as response:
                response.raise_for_status()
                for block in response.iter_content(1 << 16):
                    handle.write(block)
                    digest.update(block)
                    landed += len(block)
                    if progress is not None and landed - reported >= REPORT_EVERY:
                        reported = landed
                        progress(landed)
            handle.flush()
            os.fsync(handle.fileno())
        if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
            raise EnglishModelError(_mismatch_message(target.name))
        temporary.replace(target)
        if progress is not None:
            progress(landed)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def double_rate(samples: np.ndarray) -> np.ndarray:
    """24 kHz to 48 kHz for a whole finished piece: each sample, then the
    midpoint to the next; the last one is held for both slots."""

    source = np.asarray(samples, dtype=np.float32).reshape(-1)
    if source.size == 0:
        return source
    doubled = np.empty(source.size * 2, dtype=np.float32)
    doubled[0::2] = source
    doubled[1:-1:2] = (source[:-1] + source[1:]) / 2.0
    doubled[-1] = source[-1]
    return doubled


def split_phonemes(phonemes: str, limit: int = MAX_TOKENS) -> list[str]:
    """Pieces no longer than the model's window, cut at spaces.

    A sentence the reader sends is a few hundred characters at most, which
    is well inside the window; this is for the one that is not, so it is
    read in two rather than refused or cut short.
    """

    pieces: list[str] = []
    current = ""
    for word in phonemes.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= limit or not current:
            current = candidate
        else:
            pieces.append(current)
            current = word
        while len(current) > limit:
            pieces.append(current[:limit])
            current = current[limit:]
    if current:
        pieces.append(current)
    return pieces


class KokoroSpeechEngine:
    def __init__(
        self,
        models_path: Path,
        *,
        file_fetcher: Callable[..., None] | None = None,
        session_factory: Callable[[Path], Any] | None = None,
        g2p_factory: Callable[[Path, Path], Callable[[str], Any]] | None = None,
    ):
        self._models_path = Path(models_path)
        self._models_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._file_fetcher = file_fetcher or _fetch
        self._session_factory = session_factory or self._open_session
        self._g2p_factory = g2p_factory or self._build_g2p
        self._lock = RLock()
        self._generation = 0
        self._session: Any | None = None
        self._g2p: Callable[[str], Any] | None = None
        self._vocab: dict[str, int] | None = None
        self._styles: dict[str, np.ndarray] = {}

    # ---- identity -------------------------------------------------------

    @property
    def engine_version(self) -> str:
        return ENGINE_VERSION

    @property
    def model_revision(self) -> str:
        # Distinct from anything the Vietnamese model reports: the audio
        # cache is keyed on this, and a sentence must never be served
        # across engines.
        return f"{MODEL_REVISION}+kokoro"

    # ---- where things live ---------------------------------------------

    @property
    def _model_root(self) -> Path:
        return self._models_path / MODEL_DIRECTORY

    @property
    def _lexicon_root(self) -> Path:
        return self._models_path / LEXICON_DIRECTORY

    @property
    def _ready_marker(self) -> Path:
        return self._models_path / _READY_MARKER

    def _assets_present(self) -> bool:
        files = [self._model_root / name for name in MODEL_FILES]
        files += [self._lexicon_root / name for name in LEXICON_FILES]
        return all(path.is_file() and path.stat().st_size > 0 for path in files)

    # ---- the ready marker ---------------------------------------------

    def _read_marker(self, path: Path, limit: int = 4096) -> Any:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError:
            return None
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or metadata.st_size > limit
            ):
                return None
            payload = os.read(descriptor, limit + 1)
        finally:
            os.close(descriptor)
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return None

    def _expected_marker(self) -> dict[str, str]:
        return {
            "engine_version": ENGINE_VERSION,
            "model_revision": self.model_revision,
            "lexicon_revision": LEXICON_REVISION,
        }

    def _marker_matches(self) -> bool:
        marker = self._read_marker(self._ready_marker)
        if not isinstance(marker, dict):
            return False
        expected = self._expected_marker()
        return all(marker.get(key) == expected[key] for key in _MARKER_GATE)

    def _write_private_json(self, target: Path, document: Any) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".kokoro-ready-", suffix=".tmp", dir=self._models_path
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            payload = json.dumps(document, sort_keys=True).encode("utf-8")
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(target)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    @property
    def is_model_ready(self) -> bool:
        try:
            return self._assets_present() and self._marker_matches()
        except OSError:
            return False

    # ---- the settings row --------------------------------------------

    def installed_size(self) -> int:
        """Bytes on disk for the model and its lexicon, 0 when absent."""

        total = 0
        for root in (self._model_root, self._lexicon_root):
            try:
                for path in root.rglob("*"):
                    if path.is_file() and not path.is_symlink():
                        total += path.stat().st_size
            except OSError:
                continue
        return total

    def remove(self) -> bool:
        """Delete the download. Refuses anything but the two known folders."""

        removed = False
        with self._lock:
            self._session = None
            self._styles = {}
            self._vocab = None
            for root in (self._model_root, self._lexicon_root):
                if root.parent != self._models_path or root.is_symlink():
                    raise ValueError("refusing to remove an unexpected path")
                try:
                    shutil.rmtree(root)
                    removed = True
                except FileNotFoundError:
                    continue
                except OSError:
                    continue
            try:
                self._ready_marker.unlink()
            except OSError:
                pass
        return removed

    # ---- preparing ------------------------------------------------------

    def _verify_files(self) -> None:
        for name, expected in MODEL_FILES.items():
            path = self._model_root / name
            if expected is None:
                # The tokenizer: small, unhashed upstream, so checked by
                # what it must contain.
                try:
                    vocab = json.loads(path.read_text(encoding="utf-8"))["model"]["vocab"]
                except (OSError, ValueError, KeyError, TypeError) as error:
                    raise EnglishModelError(_mismatch_message(name)) from error
                if not isinstance(vocab, dict) or "$" not in vocab or "ˈ" not in vocab:
                    raise EnglishModelError(_mismatch_message(name))
                continue
            if _sha256(path) != expected:
                raise EnglishModelError(_mismatch_message(name))
        for name, expected in LEXICON_FILES.items():
            if _sha256(self._lexicon_root / name) != expected:
                raise EnglishModelError(_mismatch_message(name))

    def prepare_model(self, progress_callback: Callable[[float, str], None]) -> None:
        """Download, check and try the English voice, reporting as it goes."""

        with self._lock:
            if self.is_model_ready:
                progress_callback(1.0, "Giọng đọc tiếng Anh đã sẵn sàng.")
                return
            downloading = "Đang tải giọng đọc tiếng Anh (khoảng 330 MB)…"
            progress_callback(0.0, downloading)
            # The bar runs over the whole download; 0.9 is where the check
            # and the trial sentence begin.
            landed_before = 0

            def report(landed: int) -> None:
                fraction = min(landed_before + landed, DOWNLOAD_BYTES) / DOWNLOAD_BYTES
                progress_callback(0.9 * fraction, downloading)

            try:
                files: list[tuple[str, Path, str | None]] = [
                    (
                        MODEL_URL.format(repo=MODEL_REPO, revision=MODEL_REVISION, name=name),
                        self._model_root / name,
                        expected,
                    )
                    for name, expected in MODEL_FILES.items()
                ]
                files += [
                    (
                        LEXICON_URL.format(repo=LEXICON_REPO, revision=LEXICON_REVISION, name=name),
                        self._lexicon_root / name,
                        expected,
                    )
                    for name, expected in LEXICON_FILES.items()
                ]
                for url, target, expected in files:
                    if target.is_file() and target.stat().st_size > 0 and (
                        expected is None or _sha256(target) == expected
                    ):
                        # Left by an earlier attempt and still whole: kept.
                        landed_before += target.stat().st_size
                        report(0)
                        continue
                    self._file_fetcher(url, target, expected, report)
                    landed_before += target.stat().st_size
                if not self._assets_present():
                    raise OSError("the English voice download is incomplete")
                progress_callback(0.9, "Đang kiểm tra giọng đọc tiếng Anh…")
                self._verify_files()
                # The whole path, once: tagger, lexicon, fallback and model.
                self._session = None
                self._vocab = None
                self._styles = {}
                spoken = 0
                for chunk in self._synthesize("Ready.", VOICES[0].id):
                    spoken += len(chunk)
                if spoken == 0:
                    raise EnglishModelError("the English voice produced no audio")
                self._write_private_json(self._ready_marker, self._expected_marker())
            except EnglishModelError:
                self._session = None
                raise
            except Exception as error:
                self._session = None
                raise EnglishModelError(_preparation_message(error)) from error
            progress_callback(1.0, "Giọng đọc tiếng Anh đã sẵn sàng.")

    # ---- loading --------------------------------------------------------

    @staticmethod
    def _open_session(path: Path) -> Any:
        import onnxruntime

        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = INTRA_OP_THREADS
        options.log_severity_level = 3
        return onnxruntime.InferenceSession(
            str(path), options, providers=["CPUExecutionProvider"]
        )

    @staticmethod
    def _build_g2p(gold: Path, silver: Path) -> Callable[[str], Any]:
        from .english.fallback import Fallback
        from .english.g2p import G2P, Lexicon
        from .english.tagger import tag

        return G2P(tag, Lexicon(gold, silver), fallback=Fallback(), unk="")

    def _loaded(self) -> tuple[Any, Callable[[str], Any], dict[str, int]]:
        with self._lock:
            if not self._assets_present():
                raise EnglishModelNotReadyError(
                    "Giọng đọc tiếng Anh chưa được tải về máy."
                )
            if self._g2p is None:
                self._g2p = self._g2p_factory(
                    self._lexicon_root / "us_gold.json",
                    self._lexicon_root / "us_silver.json",
                )
            if self._vocab is None:
                tokenizer = json.loads(
                    (self._model_root / TOKENIZER_FILE).read_text(encoding="utf-8")
                )
                self._vocab = {
                    str(key): int(value)
                    for key, value in tokenizer["model"]["vocab"].items()
                }
            if self._session is None:
                with _LOAD_LOCK:
                    self._session = self._session_factory(self._model_root / MODEL_ONNX)
            return self._session, self._g2p, self._vocab

    def _style(self, voice_id: str) -> np.ndarray:
        pack = self._styles.get(voice_id)
        if pack is None:
            raw = np.fromfile(self._model_root / f"voices/{voice_id}.bin", dtype=np.float32)
            if raw.size % STYLE_WIDTH:
                raise EnglishModelError(f"voice pack {voice_id} has an unexpected shape")
            pack = raw.reshape(-1, STYLE_WIDTH)
            self._styles[voice_id] = pack
        return pack

    def warm(self) -> bool:
        """Load everything now so the first English sentence does not."""

        if not self.is_model_ready:
            return False
        try:
            self._loaded()
        except (EnglishModelNotReadyError, OSError, ValueError):
            return False
        return True

    # ---- speaking -------------------------------------------------------

    def voices(self) -> tuple[Voice, ...]:
        return tuple(Voice(id=voice.id, label=voice.label) for voice in VOICES)

    @staticmethod
    def gender_of(voice_id: str) -> str | None:
        for voice in VOICES:
            if voice.id == voice_id:
                return voice.gender
        return None

    def _synthesize(self, text: str, voice_id: str) -> Iterator[np.ndarray]:
        """The model's own 24 kHz audio, one piece per window of phonemes."""

        if voice_id not in VOICE_IDS:
            raise ValueError(f"unknown English voice: {voice_id!r}")
        session, g2p, vocab = self._loaded()
        phonemes, _ = g2p(text)
        pack = self._style(voice_id)
        for piece in split_phonemes(phonemes.strip()):
            tokens = [vocab[char] for char in piece if char in vocab]
            if not tokens:
                continue
            style = pack[min(len(tokens), len(pack) - 1)][None, :]
            waveform = session.run(None, {
                "input_ids": np.array([[0, *tokens, 0]], dtype=np.int64),
                "style": style.astype(np.float32),
                "speed": np.array([1.0], dtype=np.float32),
            })[0]
            yield np.asarray(waveform, dtype=np.float32).reshape(-1)

    def stream(
        self,
        text: str,
        voice_id: str,
        settings: SynthesisSettings = SynthesisSettings(),
    ) -> Iterator[AudioChunk]:
        """`settings` belongs to the Vietnamese model's sampler; the English
        model has no sampler, so it is accepted and ignored."""

        normalized = normalize_paragraph(text)
        if not normalized:
            raise ValueError("speech text cannot be empty")
        with self._lock:
            token = self._generation
        slice_length = int(TARGET_SAMPLE_RATE * SLICE_SECONDS)
        for piece in self._synthesize(normalized, voice_id):
            with self._lock:
                if token != self._generation:
                    return
            audio = double_rate(piece)
            for start in range(0, audio.size, slice_length):
                with self._lock:
                    if token != self._generation:
                        return
                pcm = audio[start:start + slice_length].astype("<f4", copy=False).tobytes()
                if pcm:
                    yield AudioChunk(pcm=pcm, sample_rate=TARGET_SAMPLE_RATE)

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1


def _mismatch_message(name: str) -> str:
    return (
        f"Tệp {name} tải về không khớp bản đã kiểm định, nên chưa dùng được. "
        "Hãy thử tải lại."
    )


def _preparation_message(error: BaseException) -> str:
    import errno

    seen: set[int] = set()
    cause: BaseException | None = error
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, OSError) and cause.errno == errno.ENOSPC:
            return (
                "Máy đã hết dung lượng trống nên chưa tải xong giọng đọc tiếng Anh. "
                "Hãy giải phóng bớt dung lượng rồi thử lại."
            )
        cause = cause.__cause__ or cause.__context__
    return "Không thể tải giọng đọc tiếng Anh. Hãy kiểm tra mạng và thử lại."
