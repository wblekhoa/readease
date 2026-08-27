#!/usr/bin/env python3
"""Ensure no Mach-O in a bundle requires macOS newer than its plist floor."""

from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import re
import subprocess
import sys


MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}
MINOS = re.compile(r"^\s*minos\s+([0-9]+(?:\.[0-9]+)*)\s*$", re.MULTILINE)


def _version(value: str) -> tuple[int, ...]:
    try:
        parts = tuple(int(part) for part in value.split("."))
    except ValueError as error:
        raise RuntimeError(f"invalid version: {value}") from error
    return parts + (0,) * (3 - len(parts))


def _is_macho(path: Path) -> bool:
    try:
        with path.open("rb") as source:
            return source.read(4) in MACHO_MAGICS
    except OSError:
        return False


def audit_bundle(bundle: Path) -> tuple[int, str, Path]:
    plist_path = bundle / "Contents" / "Info.plist"
    if not plist_path.is_file():
        raise RuntimeError(f"missing Info.plist: {plist_path}")
    with plist_path.open("rb") as source:
        plist = plistlib.load(source)
    declared = str(plist.get("LSMinimumSystemVersion", ""))
    declared_version = _version(declared)

    checked = 0
    maximum = (0, 0, 0)
    maximum_text = "0.0"
    maximum_path = plist_path
    offenders: list[tuple[Path, str]] = []
    for path in sorted(bundle.rglob("*"), key=str):
        if path.is_symlink() or not path.is_file() or not _is_macho(path):
            continue
        completed = subprocess.run(
            ["xcrun", "vtool", "-show-build", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"vtool failed for {path}: {completed.stderr.strip()}")
        versions = MINOS.findall(completed.stdout)
        if not versions:
            raise RuntimeError(f"no macOS minimum found for Mach-O: {path}")
        checked += 1
        for value in versions:
            parsed = _version(value)
            if parsed > maximum:
                maximum = parsed
                maximum_text = value
                maximum_path = path
            if parsed > declared_version:
                offenders.append((path, value))
    if checked == 0:
        raise RuntimeError(f"no Mach-O files found in bundle: {bundle}")
    if offenders:
        detail = "; ".join(
            f"{path.relative_to(bundle)} requires {value}"
            for path, value in offenders[:12]
        )
        raise RuntimeError(f"declared={declared}; {detail}")
    return checked, maximum_text, maximum_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    arguments = parser.parse_args()
    bundle = arguments.bundle.expanduser().resolve()
    try:
        checked, maximum, maximum_path = audit_bundle(bundle)
    except (OSError, RuntimeError, ValueError, plistlib.InvalidFileException) as error:
        print(f"MACOS_COMPATIBILITY RED {error}", file=sys.stderr)
        return 1
    print(
        "MACOS_COMPATIBILITY PASS "
        f"macho={checked} max_minos={maximum} "
        f"max_file={maximum_path.relative_to(bundle)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
