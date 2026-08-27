#!/usr/bin/env python3
"""Build a deterministic license payload from the actual locked environment."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import sys
import sysconfig
import xml.etree.ElementTree as ElementTree


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISTRIBUTIONS = {
    "Nuitka",
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "kaldi-native-fbank",
    "numpy",
    "onnxruntime",
    "perth",
    "shiboken6",
    "soundfile",
    "soxr",
    "tokenizers",
    "vieneu",
}
PYSIDE_DISTRIBUTIONS = {
    "pyside6",
    "pyside6-addons",
    "pyside6-essentials",
    "shiboken6",
}
MANUAL_RECEIPTS = {
    "perth": (ROOT / "legal" / "PERTH_LICENSE.txt",),
    "tokenizers": (ROOT / "legal" / "APACHE-2.0.txt",),
    **{
        name: (
            ROOT / "legal" / "GNU_GPL_v3.txt",
            ROOT / "legal" / "GNU_LGPL_v3.txt",
            ROOT / "legal" / "QT_THIRD_PARTY_NOTICES.md",
        )
        for name in PYSIDE_DISTRIBUTIONS
    },
}


def _normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _digest(path: Path) -> str:
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _report_distributions(path: Path) -> set[str]:
    root = ElementTree.parse(path).getroot()
    if root.attrib.get("completion") != "yes":
        raise RuntimeError("Nuitka compilation report is incomplete")
    names: set[str] = set()
    for module in root.findall(".//module"):
        value = module.attrib.get("distribution", "")
        names.update(item.strip() for item in value.split(",") if item.strip())
    for usage in root.findall(".//distribution-usage"):
        if usage.attrib.get("name"):
            names.add(usage.attrib["name"])
    return names


def _is_license_receipt(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/").casefold()
    name = Path(normalized).name
    return (
        "/licenses/" in f"/{normalized}"
        or normalized.startswith("licensing/")
        or name.startswith(("license", "licence", "copying", "notice", "copyright"))
        or "thirdpartynotice" in name
    )


def _distribution_receipts(distribution: metadata.Distribution) -> tuple[Path, ...]:
    receipts: list[Path] = []
    for entry in distribution.files or ():
        if not _is_license_receipt(str(entry)):
            continue
        path = Path(distribution.locate_file(entry)).resolve()
        if path.is_file() and path.stat().st_size <= 10 * 1024 * 1024:
            receipts.append(path)
    return tuple(sorted(set(receipts), key=str))


def _source_url(distribution: metadata.Distribution) -> str:
    for value in distribution.metadata.get_all("Project-URL") or ():
        label, separator, url = value.partition(",")
        if separator and label.strip().casefold() in {"repository", "source", "homepage"}:
            return url.strip()
    return distribution.metadata.get("Home-page") or "See locked package metadata"


def _receipt_record(path: Path) -> dict[str, str]:
    try:
        display = str(path.relative_to(ROOT))
    except ValueError:
        display = path.name
    return {"path": display, "sha256": _digest(path)}


def _component(
    *,
    name: str,
    version: str,
    license_name: str,
    source: str,
    bundled: bool,
    receipts: tuple[Path, ...],
) -> dict[str, object]:
    if not receipts:
        raise RuntimeError(f"no license receipt for component: {name}")
    return {
        "name": name,
        "version": version,
        "license": license_name,
        "source": source,
        "bundled": bundled,
        "receipts": [_receipt_record(path) for path in receipts],
    }


def _readable(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def build_payload(output: Path, report: Path | None) -> None:
    static_files = {
        "LICENSE": ROOT / "LICENSE",
        "NOTICE.md": ROOT / "NOTICE.md",
        "THIRD_PARTY_NOTICES.md": ROOT / "THIRD_PARTY_NOTICES.md",
        "BINARY_DISTRIBUTION.md": ROOT / "legal" / "BINARY_DISTRIBUTION.md",
    }
    for path in (
        *static_files.values(),
        ROOT / "legal" / "GNU_GPL_v3.txt",
        ROOT / "legal" / "GNU_LGPL_v3.txt",
        ROOT / "legal" / "APACHE-2.0.txt",
        ROOT / "legal" / "QT_THIRD_PARTY_NOTICES.md",
        ROOT / "legal" / "MODEL_PROVENANCE.md",
    ):
        if not path.is_file() or path.stat().st_size < 1:
            raise RuntimeError(f"missing legal source: {path}")

    names = _report_distributions(report) if report else set(DEFAULT_DISTRIBUTIONS)
    resolved: dict[str, metadata.Distribution] = {}
    for requested_name in sorted(names, key=str.casefold):
        distribution = metadata.distribution(requested_name)
        canonical = distribution.metadata.get("Name") or requested_name
        resolved[_normalized_name(canonical)] = distribution

    components: list[dict[str, object]] = []
    receipt_paths: set[Path] = {
        ROOT / "legal" / "GNU_GPL_v3.txt",
        ROOT / "legal" / "GNU_LGPL_v3.txt",
        ROOT / "legal" / "APACHE-2.0.txt",
        ROOT / "legal" / "QT_THIRD_PARTY_NOTICES.md",
        ROOT / "legal" / "MODEL_PROVENANCE.md",
    }
    components.append(
        _component(
            name="ReadEase",
            version="0.1.0",
            license_name="PolyForm-Noncommercial-1.0.0",
            source="This source tree",
            bundled=True,
            receipts=(ROOT / "LICENSE",),
        )
    )

    python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    components.append(
        _component(
            name="CPython",
            version=sys.version.split()[0],
            license_name="PSF-2.0 and bundled third-party terms",
            source="https://www.python.org/downloads/source/",
            bundled=True,
            receipts=(python_license,),
        )
    )
    receipt_paths.add(python_license)

    pyside = metadata.distribution("PySide6")
    qt_receipts = (
        ROOT / "legal" / "GNU_GPL_v3.txt",
        ROOT / "legal" / "GNU_LGPL_v3.txt",
        ROOT / "legal" / "QT_THIRD_PARTY_NOTICES.md",
    )
    components.extend(
        (
            _component(
                name="PySide6 / Qt",
                version=pyside.version,
                license_name="LGPL-3.0 selected",
                source="https://code.qt.io/cgit/pyside/pyside-setup.git/",
                bundled=True,
                receipts=qt_receipts,
            ),
            _component(
                name="QtPdf / PDFium",
                version=pyside.version,
                license_name="LGPL-3.0 selected; embedded third-party terms",
                source="https://doc.qt.io/qt-6/qtpdf-licensing.html",
                bundled=True,
                receipts=qt_receipts,
            ),
        )
    )

    model_receipts = (
        ROOT / "legal" / "APACHE-2.0.txt",
        ROOT / "legal" / "MODEL_PROVENANCE.md",
    )
    components.extend(
        (
            _component(
                name="VieNeu-TTS v3 Turbo model",
                version="2da0efab622a1722125991736524f080b751ef5b",
                license_name="Apache-2.0 (publisher declaration)",
                source="https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo",
                bundled=False,
                receipts=model_receipts,
            ),
            _component(
                name="MOSS Audio Tokenizer Nano ONNX",
                version="ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae",
                license_name="Apache-2.0 (publisher declaration)",
                source="https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
                bundled=False,
                receipts=model_receipts,
            ),
        )
    )

    for normalized, distribution in sorted(resolved.items()):
        if normalized in PYSIDE_DISTRIBUTIONS or normalized == "nuitka":
            continue
        receipts = _distribution_receipts(distribution)
        if not receipts:
            receipts = MANUAL_RECEIPTS.get(normalized, ())
        receipt_paths.update(receipts)
        display_name = distribution.metadata.get("Name") or normalized
        if normalized == "vieneu":
            display_name = "VieNeu SDK"
        components.append(
            _component(
                name=display_name,
                version=distribution.version,
                license_name=(
                    distribution.metadata.get("License-Expression")
                    or distribution.metadata.get("License")
                    or "See included receipt"
                ),
                source=_source_url(distribution),
                bundled=True,
                receipts=receipts,
            )
        )

    nuitka = metadata.distribution("Nuitka")
    nuitka_receipts = tuple(
        path
        for path in _distribution_receipts(nuitka)
        if path.name in {"LICENSE-RUNTIME.txt", "NOTICE.txt"}
    )
    receipt_paths.update(nuitka_receipts)
    components.append(
        _component(
            name="Nuitka runtime",
            version=nuitka.version,
            license_name="Nuitka runtime exception and notices",
            source="https://github.com/Nuitka/Nuitka",
            bundled=True,
            receipts=nuitka_receipts,
        )
    )

    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"legal output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for destination_name, source in static_files.items():
        (output / destination_name).write_bytes(source.read_bytes())

    sections: list[str] = []
    seen_digests: set[str] = set()
    for path in sorted(receipt_paths, key=str):
        digest = _digest(path)
        if digest in seen_digests:
            continue
        seen_digests.add(digest)
        sections.append(f"===== {path.name} | sha256:{digest} =====\n{_readable(path)}")
    (output / "THIRD_PARTY_LICENSES.txt").write_text(
        "\n\n".join(sections) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "source_license": "PolyForm-Noncommercial-1.0.0",
        "binary_distribution_status": "candidate-requires-signing-and-legal-review",
        "lock_sha256": _digest(ROOT / "uv.lock"),
        "nuitka_report_sha256": _digest(report) if report else None,
        "components": sorted(components, key=lambda item: str(item["name"]).casefold()),
    }
    (output / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "LICENSE_PAYLOAD PASS "
        f"components={len(components)} receipts={len(seen_digests)} output={output}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    if arguments.report is not None and not arguments.report.is_file():
        parser.error(f"report does not exist: {arguments.report}")
    try:
        build_payload(arguments.output, arguments.report)
    except (OSError, RuntimeError, metadata.PackageNotFoundError, ElementTree.ParseError) as error:
        print(f"LICENSE_PAYLOAD RED {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
