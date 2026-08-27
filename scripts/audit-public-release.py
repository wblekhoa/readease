#!/usr/bin/env python3
"""Fail-closed checks for a clean source export and optional local bundle."""

from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ElementTree


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "public-source-manifest.json"
FORBIDDEN_SUFFIXES = {
    ".db",
    ".epub",
    ".m4a",
    ".mp3",
    ".onnx",
    ".pdf",
    ".sqlite",
    ".sqlite3",
    ".wav",
}
FORBIDDEN_BUNDLE_NAMES = {
    "QtVirtualKeyboard",
    "QtVirtualKeyboardQml",
    "libqtvirtualkeyboardplugin.dylib",
}
FORBIDDEN_MODEL_NAMES = {
    "moss_audio_tokenizer_decode_full.onnx",
    "vieneu_prefill.onnx",
    "vieneu_decode_step.onnx",
    "vieneu_acoustic_cached.onnx",
    "vieneu_backbone_shared.data",
    "vieneu_v3_heads.npz",
}
PERSONAL_PATH = re.compile(r"/(?:Users|var/folders)/")
EMAIL = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@"
    r"[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z]{2,}(?![A-Za-z0-9])"
)
SECRET = re.compile(r"(?:AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})")
SOURCE_LICENSE = "PolyForm-Noncommercial-1.0.0"
OFFICIAL_LICENSE_SHA256 = (
    "c0ea4a896d2c8c394b29f9427589996db826cd501c512279ff0ed3ef48fabbe5"
)
PROVENANCE_ID = "READEASE-THU-AM-NC-2026-01"
REQUIRED_NOTICE = (
    "Required Notice: Copyright © 2026 Lê Khoa. "
    "ReadEase — Thư Âm original scaffold. "
    "Provenance ID READEASE-THU-AM-NC-2026-01. "
    "Noncommercial use only under PolyForm Noncommercial 1.0.0."
)


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
        raise RuntimeError("unsupported public-source manifest")
    for key in ("root_files", "directories", "excluded_names", "excluded_suffixes"):
        values = payload.get(key)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise RuntimeError(f"invalid public-source manifest field: {key}")
    return payload


def _excluded(path: Path, manifest: dict[str, object]) -> bool:
    excluded_names = set(manifest["excluded_names"])
    excluded_suffixes = set(manifest["excluded_suffixes"])
    return any(
        part in excluded_names or Path(part).suffix in excluded_suffixes
        for part in path.parts
    )


def _public_files(
    root: Path,
    manifest: dict[str, object],
    errors: list[str],
) -> tuple[Path, ...]:
    paths: set[Path] = set()
    for name in manifest["root_files"]:
        path = root / name
        if path.is_file():
            paths.add(path)
        else:
            errors.append(f"missing public source file: {name}")
    for name in manifest["directories"]:
        directory = root / name
        if not directory.is_dir():
            errors.append(f"missing public source directory: {name}")
            continue
        paths.update(
            path
            for path in directory.rglob("*")
            if path.is_file() and not _excluded(path.relative_to(root), manifest)
        )
    return tuple(sorted(paths, key=str))


def _is_git_worktree(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return False
    try:
        return Path(completed.stdout.strip()).resolve() == root.resolve()
    except OSError:
        return False


def _audit_source(root: Path, errors: list[str]) -> tuple[int, str]:
    try:
        manifest = _load_manifest(root)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        errors.append(f"public-source manifest error: {error}")
        return 0, "unknown"
    public_files = _public_files(root, manifest, errors)
    try:
        with (root / "pyproject.toml").open("rb") as source:
            project_license = tomllib.load(source)["project"]["license"]
        license_text = (root / "LICENSE").read_text(encoding="utf-8")
        notice_text = (root / "NOTICE.md").read_text(encoding="utf-8")
        provenance_source_path = (
            root / "src" / "vieneu_reader" / "provenance.py"
        )
        provenance_tree = ast.parse(
            provenance_source_path.read_text(encoding="utf-8"),
            filename=str(provenance_source_path),
        )
        provenance_constants: dict[str, object] = {}
        for node in provenance_tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name):
                try:
                    provenance_constants[target.id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    continue
        if project_license != SOURCE_LICENSE:
            errors.append(f"unexpected first-party source license: {project_license}")
        if "PolyForm Noncommercial License 1.0.0" not in license_text:
            errors.append("root LICENSE is not PolyForm Noncommercial 1.0.0")
        if _digest(root / "LICENSE") != OFFICIAL_LICENSE_SHA256:
            errors.append("root LICENSE does not match the official PolyForm license digest")
        if REQUIRED_NOTICE not in notice_text:
            errors.append("NOTICE.md is missing the required provenance notice")
        expected_constants = {
            "PROVENANCE_SCHEMA_VERSION": 1,
            "PROVENANCE_ID": PROVENANCE_ID,
            "LICENSE_ID": SOURCE_LICENSE,
            "REQUIRED_NOTICE": REQUIRED_NOTICE,
        }
        for name, expected in expected_constants.items():
            if provenance_constants.get(name) != expected:
                errors.append(f"source provenance constant is invalid: {name}")
    except (KeyError, OSError, SyntaxError, tomllib.TOMLDecodeError) as error:
        errors.append(f"first-party license audit failed: {error}")
    history = "requires-clean-squash" if _is_git_worktree(root) else "clean-export"
    if history == "clean-export":
        public_set = set(public_files)
        unexpected: list[Path] = []
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if path.is_file() and path not in public_set and not _excluded(relative, manifest):
                unexpected.append(relative)
        if unexpected:
            examples = ", ".join(str(path) for path in unexpected[:12])
            errors.append(
                "unexpected clean-export artifact"
                f" count={len(unexpected)} examples={examples}"
            )
    checked = 0
    for path in public_files:
        checked += 1
        relative = path.relative_to(root)
        if path.name == ".env" or path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden public artifact: {relative}")
        if path.stat().st_size > 10 * 1024 * 1024:
            errors.append(f"public blob exceeds 10 MiB: {relative}")
        if path.stat().st_size > 2 * 1024 * 1024 and path.suffix.casefold() not in {
            ".icns",
            ".png",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        if PERSONAL_PATH.search(text):
            errors.append(f"personal absolute path: {relative}")
        if EMAIL.search(text):
            errors.append(f"email in public export: {relative}")
        if SECRET.search(text):
            errors.append(f"credential-like value: {relative}")
    return checked, history


def _audit_report(path: Path, errors: list[str]) -> str:
    root = ElementTree.parse(path).getroot()
    if root.attrib.get("completion") != "yes":
        errors.append("Nuitka report is incomplete")
    distributions = {
        item.strip().casefold()
        for module in root.findall(".//module")
        for item in module.attrib.get("distribution", "").split(",")
        if item.strip()
    }
    if any("pymupdf" in name for name in distributions):
        errors.append("Nuitka report contains PyMuPDF")
    return _digest(path)


def _audit_bundle(
    bundle: Path,
    report: Path | None,
    source_root: Path,
    errors: list[str],
) -> str:
    if not bundle.is_dir():
        errors.append(f"bundle does not exist: {bundle}")
        return "missing"
    paths = tuple(path for path in bundle.rglob("*") if path.is_file())
    names = {path.name for path in paths}
    for forbidden in FORBIDDEN_BUNDLE_NAMES | FORBIDDEN_MODEL_NAMES:
        if forbidden in names:
            errors.append(f"forbidden bundle artifact: {forbidden}")
    if any("mupdf" in str(path).casefold() for path in paths):
        errors.append("bundle contains MuPDF")
    if not (bundle / "Contents" / "MacOS" / "QtPdf").is_file():
        errors.append("bundle is missing QtPdf")

    legal = bundle / "Contents" / "Resources" / "Legal"
    required = {
        "BINARY_DISTRIBUTION.md",
        "LICENSE",
        "NOTICE.md",
        "THIRD_PARTY_LICENSES.txt",
        "THIRD_PARTY_MANIFEST.json",
        "THIRD_PARTY_NOTICES.md",
    }
    if not legal.is_dir() or {path.name for path in legal.iterdir()} != required:
        errors.append("bundle legal payload is missing or has unexpected files")
        return "unknown"
    manifest = json.loads(
        (legal / "THIRD_PARTY_MANIFEST.json").read_text(encoding="utf-8")
    )
    if manifest.get("source_license") != SOURCE_LICENSE:
        errors.append("bundle manifest has the wrong first-party source license")
    if _digest(legal / "LICENSE") != _digest(source_root / "LICENSE"):
        errors.append("bundle first-party LICENSE does not match the source")
    if _digest(legal / "NOTICE.md") != _digest(source_root / "NOTICE.md"):
        errors.append("bundle NOTICE.md does not match the source")
    if REQUIRED_NOTICE not in (legal / "NOTICE.md").read_text(encoding="utf-8"):
        errors.append("bundle legal payload is missing the required notice")

    provenance_path = (
        bundle
        / "Contents"
        / "Resources"
        / "Provenance"
        / "READEASE_PROVENANCE.json"
    )
    plist_path = bundle / "Contents" / "Info.plist"
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        with plist_path.open("rb") as handle:
            plist = plistlib.load(handle)
        expected = {
            "schema_version": 1,
            "product": "ReadEase — Thư Âm",
            "provenance_id": PROVENANCE_ID,
            "license_id": SOURCE_LICENSE,
            "required_notice": REQUIRED_NOTICE,
            "scope": "first-party-software-and-scaffold",
            "tracking": False,
        }
        if provenance != expected:
            errors.append("bundle provenance resource is missing or noncanonical")
        if plist.get("ReadEaseProvenanceID") != PROVENANCE_ID:
            errors.append("Info.plist provenance ID does not match the source")
        if plist.get("ReadEaseLicenseIdentifier") != SOURCE_LICENSE:
            errors.append("Info.plist license identifier does not match the source")
        if plist.get("ReadEaseRequiredNotice") != REQUIRED_NOTICE:
            errors.append("Info.plist required notice does not match the source")
        if plist.get("ReadEaseProvenanceTracking") is not False:
            errors.append("Info.plist must declare non-tracking provenance")
    except (OSError, ValueError, json.JSONDecodeError, plistlib.InvalidFileException) as error:
        errors.append(f"bundle provenance audit failed: {error}")
    report_digest = _digest(report) if report else None
    if manifest.get("nuitka_report_sha256") != report_digest:
        errors.append("bundle manifest is not bound to the supplied Nuitka report")

    completed = subprocess.run(
        ["codesign", "-dv", "--verbose=4", str(bundle)],
        check=False,
        capture_output=True,
        text=True,
    )
    signature = completed.stderr + completed.stdout
    return "adhoc" if "Signature=adhoc" in signature else "developer-id-or-unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-distribution-signing", action="store_true")
    arguments = parser.parse_args()
    if (arguments.bundle is None) != (arguments.report is None):
        parser.error("--bundle and --report must be supplied together")

    errors: list[str] = []
    source_root = arguments.source_root.expanduser().resolve()
    checked, history = _audit_source(source_root, errors)
    report_digest = None
    signing = "not-checked"
    if arguments.report is not None:
        report_digest = _audit_report(arguments.report, errors)
        signing = _audit_bundle(
            arguments.bundle,
            arguments.report,
            source_root,
            errors,
        )
    if arguments.require_distribution_signing and signing != "developer-id-or-unknown":
        errors.append("Developer ID signing is required for public binary distribution")

    if errors:
        for error in errors:
            print(f"PUBLIC_RELEASE_AUDIT RED {error}", file=sys.stderr)
        return 1
    print(
        "PUBLIC_RELEASE_AUDIT PASS "
        f"files={checked} history={history} signing={signing} "
        f"report_sha256={report_digest or 'not-checked'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
