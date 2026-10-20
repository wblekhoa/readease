"""The translation model ReadEase downloads and keeps (RE-PLAY-031).

One file: Tencent's Hy-MT2 1.8B, quantised Q4_K_M, as Tencent publishes it
in GGUF. The engine only fetches, checks and removes it; translating is the
host's job - it runs the bundled llama.cpp server on this file, on loopback,
for as long as translations keep coming.

The file is pinned like the English voice's: one revision of the model
repository and the SHA-256 that repository publishes for it [fetched
2026-10-20], so a moved or altered upload can never land.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable

from vieneu_reader.speech.kokoro import _fetch, _sha256

MODEL_REPO = "tencent/Hy-MT2-1.8B-GGUF"
MODEL_REVISION = "a0c709d9fac510f2c807aa3af52872340dc37a4a"
MODEL_NAME = "Hy-MT2-1.8B-Q4_K_M.gguf"
MODEL_SHA256 = "dc5f44fcf1fa496ee7ad725982c0c8c553a4de00259b53af84c4b89fb0c06699"
DOWNLOAD_BYTES = 1_133_080_448
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{MODEL_NAME}"
MODEL_DIRECTORY = "hy-mt2-1.8b-gguf"
#: Written once the file is whole and its hash matched: checking 1.1 GB on
#: every status request would make the hub slow to open.
_READY_MARKER = "ready.sha256"


class TranslatorModelError(RuntimeError):
    """The download failed or did not match; the message says what to do."""


class TranslatorModel:
    def __init__(self, models_path: Path, *, file_fetcher: Callable[..., None] | None = None):
        self._models_path = Path(models_path)
        self._file_fetcher = file_fetcher or _fetch

    @property
    def _root(self) -> Path:
        return self._models_path / MODEL_DIRECTORY

    @property
    def path(self) -> Path:
        return self._root / MODEL_NAME

    @property
    def is_model_ready(self) -> bool:
        try:
            marker = (self._root / _READY_MARKER).read_text(encoding="ascii").strip()
            return marker == MODEL_SHA256 and self.path.is_file() and self.path.stat().st_size == DOWNLOAD_BYTES
        except OSError:
            return False

    def installed_size(self) -> int:
        try:
            return sum(p.stat().st_size for p in self._root.iterdir() if p.is_file() and not p.is_symlink())
        except OSError:
            return 0

    def remove(self) -> bool:
        root = self._root
        if root.parent != self._models_path or root.is_symlink():
            raise ValueError("refusing to remove an unexpected path")
        try:
            shutil.rmtree(root)
        except FileNotFoundError:
            return False
        return True

    def prepare_model(self, progress_callback: Callable[[float, str], None]) -> None:
        if self.is_model_ready:
            progress_callback(1.0, "Bộ dịch đã sẵn sàng.")
            return
        downloading = "Đang tải bộ dịch (khoảng 1,1 GB)…"
        progress_callback(0.0, downloading)

        def report(landed: int) -> None:
            progress_callback(0.98 * min(landed, DOWNLOAD_BYTES) / DOWNLOAD_BYTES, downloading)

        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self._file_fetcher(MODEL_URL, self.path, MODEL_SHA256, report)
        except Exception as error:  # a cancel is a BaseException and passes through
            raise TranslatorModelError(
                "Chưa tải được bộ dịch. Kiểm tra kết nối mạng và dung lượng trống, rồi thử lại."
            ) from error
        if _sha256(self.path) != MODEL_SHA256:
            raise TranslatorModelError("Tệp bộ dịch tải về không khớp bản đã kiểm định. Hãy thử tải lại.")
        marker = self._root / _READY_MARKER
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(MODEL_SHA256)
        progress_callback(1.0, "Bộ dịch đã sẵn sàng.")
