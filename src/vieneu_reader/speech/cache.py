"""Atomic complete-segment float32 audio cache."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import asdict
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from threading import RLock

from vieneu_reader.domain.models import AudioChunk
from vieneu_reader.domain.segmenter import normalize_paragraph

from .contracts import SynthesisSettings


_CACHE_KEY = re.compile(r"[0-9a-f]{64}")
_CACHE_FILE_NAME = re.compile(r"[0-9a-f]{64}\.f32")
_CACHE_TEMP_NAME = re.compile(r"\.[0-9a-f]{64}-[a-z0-9_]{8}\.part")


def audio_cache_key(
    text: str,
    voice_id: str,
    engine_version: str,
    model_revision: str,
    settings: SynthesisSettings,
    reading_revision: str = "",
) -> str:
    payload = {
        "engine_version": engine_version,
        "model_revision": model_revision,
        # How the text was turned into sound, which is not the engine's
        # business: the same voice reading the same paragraph one sentence at
        # a time is different audio.
        "reading_revision": reading_revision,
        "settings": asdict(settings),
        "text": normalize_paragraph(text),
        "voice_id": voice_id,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class AudioCache:
    _process_cache_lock = RLock()

    def __init__(self, root: Path, max_bytes: int = 1024 * 1024 * 1024):
        if max_bytes <= 0:
            raise ValueError("audio cache quota must be positive")
        self._root = Path(root)
        self._max_bytes = max_bytes
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._root.chmod(0o700)
        with self._cache_guard():
            self._scavenge_scratch()
            self._evict_oldest()

    def _path(self, key: str) -> Path:
        if _CACHE_KEY.fullmatch(key) is None:
            raise ValueError("invalid audio cache key")
        return self._root / f"{key}.f32"

    def get(self, key: str) -> AudioChunk | None:
        path = self._path(key)
        with self._cache_guard():
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            flags |= getattr(os, "O_NONBLOCK", 0)
            try:
                descriptor = os.open(path, flags)
            except OSError:
                return None
            try:
                metadata = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                    or metadata.st_size <= 0
                    or metadata.st_size > self._max_bytes
                    or metadata.st_size % 4
                ):
                    return None
                remaining = metadata.st_size
                pieces: list[bytes] = []
                while remaining:
                    piece = os.read(descriptor, min(remaining, 1024 * 1024))
                    if not piece:
                        return None
                    pieces.append(piece)
                    remaining -= len(piece)
                if os.fstat(descriptor).st_size != metadata.st_size:
                    return None
            finally:
                os.close(descriptor)
            try:
                os.utime(path, None, follow_symlinks=False)
            except OSError:
                pass
            return AudioChunk(pcm=b"".join(pieces))

    @contextmanager
    def _cache_guard(self):
        lock_path = self._root / ".cache.lock"
        with self._process_cache_lock:
            flags = os.O_CREAT | os.O_RDWR
            flags |= getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(lock_path, flags, 0o600)
            try:
                metadata = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                ):
                    raise OSError("audio cache lock is not an owned regular file")
                os.fchmod(descriptor, 0o600)
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            except BaseException:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
            try:
                yield
            except BaseException as primary_error:
                try:
                    os.close(descriptor)
                except OSError:
                    primary_error.add_note(
                        "Could not close the audio cache lock after the primary error."
                    )
                raise
            else:
                try:
                    os.close(descriptor)
                except OSError:
                    # A cache write may already be atomically committed. A
                    # close report cannot safely redefine it as a failed write.
                    pass

    def _scavenge_scratch(self) -> None:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        flags |= getattr(os, "O_CLOEXEC", 0)
        root_descriptor = os.open(self._root, flags)
        try:
            with os.scandir(root_descriptor) as entries:
                for entry in entries:
                    if _CACHE_TEMP_NAME.fullmatch(entry.name) is None:
                        continue
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    if (
                        not stat.S_ISREG(metadata.st_mode)
                        or metadata.st_uid != os.getuid()
                    ):
                        continue
                    try:
                        os.unlink(entry.name, dir_fd=root_descriptor)
                    except FileNotFoundError:
                        continue
        finally:
            os.close(root_descriptor)

    def _complete_files(self) -> list[tuple[Path, int, int]]:
        files: list[tuple[Path, int, int]] = []
        with os.scandir(self._root) as entries:
            for entry in entries:
                if _CACHE_FILE_NAME.fullmatch(entry.name) is None:
                    continue
                try:
                    metadata = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                ):
                    continue
                files.append(
                    (
                        self._root / entry.name,
                        metadata.st_size,
                        metadata.st_mtime_ns,
                    )
                )
        return files

    def _evict_oldest(self) -> None:
        files = self._complete_files()
        total = sum(size for _path, size, _modified in files)
        for path, size, _modified in sorted(
            files,
            key=lambda item: (item[2], item[0].name),
        ):
            if total <= self._max_bytes:
                break
            path.unlink()
            total -= size

    def _make_room_for(self, incoming_bytes: int, final_path: Path) -> None:
        files = [item for item in self._complete_files() if item[0] != final_path]
        total = sum(size for _path, size, _modified in files)
        for path, size, _modified in sorted(
            files,
            key=lambda item: (item[2], item[0].name),
        ):
            if total + incoming_bytes <= self._max_bytes:
                break
            path.unlink()
            total -= size
        if total + incoming_bytes > self._max_bytes:
            raise OSError("audio cache could not make room within its quota")

    def put_complete(
        self,
        key: str,
        chunks: Iterable[AudioChunk],
        *,
        commit_guard: Callable[[], AbstractContextManager[None]] | None = None,
    ) -> Path:
        final_path = self._path(key)
        with self._cache_guard():
            self._scavenge_scratch()
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{key}-",
                suffix=".part",
                dir=self._root,
            )
            temporary_path = Path(temporary_name)
            wrote = 0
            try:
                with os.fdopen(descriptor, "wb") as output:
                    for chunk in chunks:
                        if (
                            chunk.sample_rate != 48_000
                            or chunk.channels != 1
                            or chunk.sample_format != "float32"
                        ):
                            raise ValueError(
                                "audio cache accepts mono 48 kHz float32 only"
                            )
                        if not chunk.pcm or len(chunk.pcm) % 4:
                            raise ValueError(
                                "audio chunk must contain complete float32 samples"
                            )
                        if wrote + len(chunk.pcm) > self._max_bytes:
                            raise ValueError("audio segment exceeds the cache quota")
                        output.write(chunk.pcm)
                        wrote += len(chunk.pcm)
                    if wrote == 0:
                        raise ValueError("empty audio cannot be cached")
                    output.flush()
                    os.fsync(output.fileno())
                self._make_room_for(wrote, final_path)
                guard = commit_guard() if commit_guard is not None else nullcontext()
                with guard:
                    temporary_path.replace(final_path)
                result = final_path
            except BaseException as primary_error:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    primary_error.add_note(
                        "Could not remove incomplete audio cache scratch."
                    )
                raise
            else:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass
                return result
