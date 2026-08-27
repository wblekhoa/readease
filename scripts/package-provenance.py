#!/usr/bin/env python3
"""Embed deterministic, non-tracking ReadEase provenance in a macOS bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import plistlib
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vieneu_reader.provenance import (  # noqa: E402
    LICENSE_ID,
    PROVENANCE_ID,
    REQUIRED_NOTICE,
    provenance_payload,
)


def package_provenance(bundle: Path) -> Path:
    bundle = bundle.expanduser().resolve()
    if bundle.suffix != ".app" or not bundle.is_dir():
        raise RuntimeError(f"invalid app bundle: {bundle}")
    plist_path = bundle / "Contents" / "Info.plist"
    if not plist_path.is_file():
        raise RuntimeError(f"missing Info.plist: {plist_path}")

    with plist_path.open("rb") as handle:
        plist = plistlib.load(handle)
    plist.update(
        {
            "ReadEaseProvenanceID": PROVENANCE_ID,
            "ReadEaseLicenseIdentifier": LICENSE_ID,
            "ReadEaseRequiredNotice": REQUIRED_NOTICE,
            "ReadEaseProvenanceTracking": False,
        }
    )
    with plist_path.open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=True)

    output = (
        bundle
        / "Contents"
        / "Resources"
        / "Provenance"
        / "READEASE_PROVENANCE.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            provenance_payload(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        output = package_provenance(arguments.bundle)
    except (OSError, RuntimeError, ValueError, plistlib.InvalidFileException) as error:
        print(f"PROVENANCE_PACKAGE RED {error}", file=sys.stderr)
        return 1
    print(
        "PROVENANCE_PACKAGE PASS "
        f"id={PROVENANCE_ID} tracking=0 output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
