#!/usr/bin/env python3
"""Create a fail-closed, history-free ReadEase source tree and optional ZIP."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "public-source-manifest.json"


def _digest(path: Path) -> str:
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _load_manifest(root: Path) -> dict[str, object]:
    path = root / "scripts" / MANIFEST_NAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError("unsupported_manifest")
    for key in ("root_files", "directories", "excluded_names", "excluded_suffixes"):
        values = payload.get(key)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise RuntimeError(f"invalid_manifest_{key}")
    return payload


def _excluded(path: Path, manifest: dict[str, object]) -> bool:
    excluded_names = set(manifest["excluded_names"])
    excluded_suffixes = set(manifest["excluded_suffixes"])
    return any(
        part in excluded_names or Path(part).suffix in excluded_suffixes
        for part in path.parts
    )


def _public_files(root: Path, manifest: dict[str, object]) -> tuple[Path, ...]:
    files: set[Path] = set()
    for name in manifest["root_files"]:
        path = root / name
        if not path.is_file():
            raise RuntimeError(f"missing_public_file={name}")
        files.add(path)
    for name in manifest["directories"]:
        directory = root / name
        if not directory.is_dir():
            raise RuntimeError(f"missing_public_directory={name}")
        files.update(
            path
            for path in directory.rglob("*")
            if path.is_file() and not _excluded(path.relative_to(root), manifest)
        )
    return tuple(sorted(files, key=lambda path: str(path.relative_to(root))))


def _copy_source(root: Path, destination: Path, manifest: dict[str, object]) -> int:
    count = 0
    for source in _public_files(root, manifest):
        relative = source.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        count += 1
    return count


def _audit(destination: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            destination / "scripts" / "audit-public-release.py",
            "--strict",
            "--source-root",
            destination,
        ],
        cwd=destination,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"export_audit_failed={detail}")


def _write_zip(source: Path, archive: Path) -> None:
    if archive.exists():
        raise RuntimeError(f"archive_exists={archive}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(source.rglob("*"), key=str):
            if not path.is_file():
                continue
            relative = Path(source.name) / path.relative_to(source)
            info = zipfile.ZipInfo.from_file(path, arcname=str(relative))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            mode = stat.S_IMODE(path.stat().st_mode)
            info.external_attr = (stat.S_IFREG | mode) << 16
            with path.open("rb") as handle:
                output.writestr(info, handle.read())


def export_source(output: Path, archive: Path | None) -> tuple[int, str | None]:
    output = output.expanduser().resolve()
    archive = archive.expanduser().resolve() if archive is not None else None
    if output.exists():
        raise RuntimeError(f"destination_exists={output}")
    if archive is not None and archive.exists():
        raise RuntimeError(f"archive_exists={archive}")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(ROOT)
    with tempfile.TemporaryDirectory(
        prefix=".readease-export.",
        dir=output.parent,
    ) as temporary:
        staging = Path(temporary) / output.name
        staging.mkdir()
        count = _copy_source(ROOT, staging, manifest)
        _audit(staging)
        os.replace(staging, output)
    archive_digest = None
    if archive is not None:
        _write_zip(output, archive)
        archive_digest = _digest(archive)
    return count, archive_digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    try:
        count, archive_digest = export_source(arguments.output, arguments.archive)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"PUBLIC_SOURCE_EXPORT RED {error}", file=sys.stderr)
        return 1
    print(
        "PUBLIC_SOURCE_EXPORT PASS "
        f"files={count} output={arguments.output.expanduser().resolve()} "
        f"archive_sha256={archive_digest or 'not-requested'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
