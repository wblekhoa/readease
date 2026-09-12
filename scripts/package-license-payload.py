#!/usr/bin/env python3
"""Build the licence payload from what the bundle actually contains.

Three inventories, each read from the artefact rather than from a wish list:

  * the Python engine - every distribution PyInstaller froze into the sidecar,
    read from its own `PYZ-*.toc` / `COLLECT-*.toc` and mapped back to the
    installed distribution through `packages_distributions()`;
  * the Rust host - every crate in `Cargo.lock`, with its licence expression,
    source repository and licence texts read from the local registry cache;
  * the models and tools that do not appear in either lock - the voice models
    (downloaded later, never bundled) and the PyInstaller bootloader that is
    linked into the frozen engine.

Every component must end with a licence receipt. A component whose upstream
ships no licence file gets the canonical SPDX text from `legal/spdx/` and its
copyright line from the package metadata; an SPDX id this tree carries no text
for is an error, not a blank. The payload is deterministic: sorted, hashed,
and the manifest records the digests of both locks so a payload can be tied
to exactly one build.
"""

from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import sys
import sysconfig
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SPDX_TEXTS = ROOT / "legal" / "spdx"
STATIC_FILES = {
    "LICENSE": ROOT / "LICENSE",
    "NOTICE.md": ROOT / "NOTICE.md",
    "THIRD_PARTY_NOTICES.md": ROOT / "THIRD_PARTY_NOTICES.md",
    "BINARY_DISTRIBUTION.md": ROOT / "legal" / "BINARY_DISTRIBUTION.md",
}
MODELS = (
    {
        "name": "VieNeu-TTS v3 Turbo model",
        "version": "2da0efab622a1722125991736524f080b751ef5b",
        "license": "Apache-2.0 (publisher declaration)",
        "source": "https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo",
    },
    {
        "name": "MOSS Audio Tokenizer Nano ONNX",
        "version": "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae",
        "license": "Apache-2.0 (publisher declaration)",
        "source": "https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
    },
)
# The SPDX word for a licence a package names by hand rather than by id.
LICENSE_ALIASES = {
    "apache license": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "mit license": "MIT",
    "bsd license": "BSD-3-Clause",
    "bsd": "BSD-3-Clause",
    "isc license": "ISC",
    "python software foundation license": "PSF-2.0",
    "mit-cmu": "MIT-CMU",
}
_SPDX_ID = re.compile(r"[A-Za-z0-9.+-]+")


class PayloadError(RuntimeError):
    pass


def _digest(path: Path) -> str:
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _readable(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _spdx_alternatives(expression: str) -> list[list[str]]:
    """The licence ids an SPDX expression lets a recipient choose between.

    `A OR B` is a choice: satisfying either is enough, and this build takes
    the first alternative it carries a text for. `A AND B` needs both.
    `X WITH exception` is X for the purpose of which text to ship. Parentheses
    are flattened - the expressions in this tree nest no deeper than
    `MPL-2.0 AND (Apache-2.0 OR MIT)`, and for those the flattening yields the
    same set of required texts.
    """

    # `MIT/Apache-2.0` is the pre-SPDX spelling of `MIT OR Apache-2.0`, and
    # a few older crates still carry it.
    expression = re.sub(r"(?<=[A-Za-z0-9.+-])/(?=[A-Za-z])", " OR ", expression)
    tokens = [t for t in re.split(r"[\s()]+", expression) if t]
    alternatives: list[list[str]] = [[]]
    skip = False
    for token in tokens:
        upper = token.upper()
        if skip:
            skip = False
            continue
        if upper == "WITH":
            skip = True
            continue
        if upper == "OR":
            alternatives.append([])
            continue
        if upper == "AND":
            continue
        alternatives[-1].append(token)
    return [group for group in alternatives if group]


def _canonical_texts(expression: str, component: str) -> tuple[Path, ...]:
    """Canonical SPDX texts for a component that ships none of its own."""

    missing: list[str] = []
    for group in _spdx_alternatives(expression):
        paths = [SPDX_TEXTS / f"{spdx_id}.txt" for spdx_id in group]
        if all(path.is_file() for path in paths):
            return tuple(paths)
        missing.extend(spdx_id for spdx_id, path in zip(group, paths) if not path.is_file())
    raise PayloadError(
        f"{component}: no licence file upstream and no canonical text for "
        f"{', '.join(sorted(set(missing)))} in legal/spdx/ - add one before shipping"
    )


def _is_license_receipt(name: str) -> bool:
    lowered = name.casefold()
    return (
        lowered.startswith(("license", "licence", "copying", "notice", "copyright"))
        or "thirdpartynotice" in lowered
        or lowered.endswith((".license", "-license", "_license"))
    )


# --------------------------------------------------------------------------
# The Python engine
# --------------------------------------------------------------------------

def _toc_entries(path: Path) -> list:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"\[.*\]", text, re.S)
    if match is None:
        raise PayloadError(f"unreadable PyInstaller TOC: {path}")
    return ast.literal_eval(match.group(0))


def _frozen_top_levels(engine_build: Path) -> set[str]:
    tops: set[str] = set()
    pyz = sorted(engine_build.glob("PYZ-*.toc"))
    collect = sorted(engine_build.glob("COLLECT-*.toc"))
    if not pyz or not collect:
        raise PayloadError(f"no PyInstaller TOC files under {engine_build}")
    for entry in _toc_entries(pyz[0]):
        tops.add(str(entry[0]).split(".")[0])
    for entry in _toc_entries(collect[0]):
        tops.add(str(entry[0]).split("/")[0].split(".")[0])
    return tops


def _distribution_license(distribution: metadata.Distribution) -> str:
    expression = distribution.metadata.get("License-Expression")
    if expression:
        return expression
    declared = (distribution.metadata.get("License") or "").strip()
    first = declared.splitlines()[0].strip() if declared else ""
    if first and len(first) <= 60:
        return LICENSE_ALIASES.get(first.casefold(), first)
    for classifier in distribution.metadata.get_all("Classifier") or ():
        if classifier.startswith("License ::"):
            label = classifier.split("::")[-1].strip()
            return LICENSE_ALIASES.get(label.casefold(), label)
    raise PayloadError(f"{distribution.metadata['Name']}: no licence declared in metadata")


def _distribution_receipts(distribution: metadata.Distribution) -> tuple[Path, ...]:
    """The licence texts a distribution ships: its `.dist-info/licenses/`
    directory, or files named like a licence anywhere in it. Source files are
    never receipts - setuptools carries a `licenses/` PACKAGE whose parser
    lists every SPDX id, which is not a licence of anything."""

    receipts: list[Path] = []
    for entry in distribution.files or ():
        parts = str(entry).replace("\\", "/").split("/")
        name = parts[-1]
        if name.casefold().endswith((".py", ".pyc", ".pyi", ".so", ".dylib")):
            continue
        in_dist_info_licenses = (
            len(parts) >= 3 and parts[0].endswith(".dist-info") and parts[1].casefold() == "licenses"
        )
        if not in_dist_info_licenses and not _is_license_receipt(name):
            continue
        path = Path(distribution.locate_file(entry)).resolve()
        if path.is_file() and path.stat().st_size <= 2 * 1024 * 1024:
            receipts.append(path)
    return tuple(sorted(set(receipts), key=str))


def _source_url(distribution: metadata.Distribution) -> str:
    for value in distribution.metadata.get_all("Project-URL") or ():
        label, separator, url = value.partition(",")
        if separator and label.strip().casefold() in {"repository", "source", "source code", "homepage"}:
            return url.strip()
    home = distribution.metadata.get("Home-page")
    if home:
        return home
    name = distribution.metadata["Name"]
    return f"https://pypi.org/project/{name}/{distribution.version}/"


def engine_components(engine_build: Path) -> list[dict[str, object]]:
    tops = _frozen_top_levels(engine_build)
    by_top = metadata.packages_distributions()
    names: dict[str, metadata.Distribution] = {}
    for top in sorted(tops):
        for name in by_top.get(top, ()):
            distribution = metadata.distribution(name)
            names[distribution.metadata["Name"]] = distribution
    components = []
    for name, distribution in sorted(names.items(), key=lambda item: item[0].casefold()):
        if name.casefold() == "vieneu-reader":
            continue  # first-party, listed as ReadEase
        license_name = _distribution_license(distribution)
        receipts = _distribution_receipts(distribution)
        if not receipts:
            receipts = _canonical_texts(license_name, name)
        display = "VieNeu SDK" if name.casefold() == "vieneu" else name
        components.append({
            "name": display,
            "version": distribution.version,
            "kind": "python",
            "license": license_name,
            "source": _source_url(distribution),
            "bundled": True,
            "receipts": receipts,
        })
    return components


# --------------------------------------------------------------------------
# The Rust host
# --------------------------------------------------------------------------

def _registry_roots() -> list[Path]:
    registry = Path.home() / ".cargo" / "registry" / "src"
    return sorted(registry.glob("*")) if registry.is_dir() else []


def crate_components(cargo_lock: Path) -> list[dict[str, object]]:
    lock = tomllib.loads(cargo_lock.read_text(encoding="utf-8"))
    roots = _registry_roots()
    components = []
    for package in lock.get("package", ()):
        name, version = package["name"], package["version"]
        if "source" not in package:
            continue  # the app crate itself, first-party
        crate_dir = next((root / f"{name}-{version}" for root in roots if (root / f"{name}-{version}").is_dir()), None)
        if crate_dir is None:
            raise PayloadError(f"crate {name} {version} is in Cargo.lock but not in the local registry cache")
        manifest = tomllib.loads((crate_dir / "Cargo.toml").read_text(encoding="utf-8", errors="replace"))
        meta = manifest.get("package", {})
        license_name = meta.get("license")
        license_file = meta.get("license-file")
        receipts = tuple(sorted(
            (p for p in crate_dir.iterdir() if p.is_file() and _is_license_receipt(p.name) and p.stat().st_size <= 2 * 1024 * 1024),
            key=str,
        ))
        if license_file and (crate_dir / license_file).is_file():
            receipts = tuple(sorted(set(receipts) | {(crate_dir / license_file).resolve()}, key=str))
        if not license_name:
            license_name = "See licence file" if receipts else None
        if license_name is None:
            raise PayloadError(f"crate {name} {version}: no licence declared and no licence file")
        if not receipts:
            receipts = _canonical_texts(license_name, f"crate {name}")
        authors = meta.get("authors") or []
        components.append({
            "name": name,
            "version": version,
            "kind": "crate",
            "license": license_name,
            "source": meta.get("repository") or f"https://crates.io/crates/{name}/{version}",
            "copyright": "; ".join(str(a) for a in authors) if authors else None,
            "bundled": True,
            "receipts": receipts,
        })
    components.sort(key=lambda item: (str(item["name"]).casefold(), str(item["version"])))
    return components


# --------------------------------------------------------------------------
# Everything else, and the payload
# --------------------------------------------------------------------------

def other_components() -> list[dict[str, object]]:
    python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if not python_license.is_file():
        raise PayloadError(f"CPython licence not found at {python_license}")
    pyinstaller = metadata.distribution("pyinstaller")
    bootloader = tuple(
        p for p in _distribution_receipts(pyinstaller) if p.name.casefold() in {"copying.txt", "license", "license.txt"}
    )
    if not bootloader:
        raise PayloadError("PyInstaller ships no COPYING.txt - the bootloader licence must travel with the frozen engine")
    model_receipts = (ROOT / "legal" / "spdx" / "Apache-2.0.txt", ROOT / "legal" / "MODEL_PROVENANCE.md")
    components: list[dict[str, object]] = [
        {
            "name": "ReadEase", "version": "0.1.0", "kind": "first-party",
            "license": "PolyForm-Noncommercial-1.0.0", "source": "This source tree",
            "bundled": True, "receipts": (ROOT / "LICENSE",),
        },
        {
            "name": "CPython", "version": sys.version.split()[0], "kind": "runtime",
            "license": "PSF-2.0 and bundled third-party terms",
            "source": "https://www.python.org/downloads/source/",
            "bundled": True, "receipts": (python_license,),
        },
        {
            "name": "PyInstaller bootloader", "version": pyinstaller.version, "kind": "tool",
            "license": "GPL-2.0-or-later WITH Bootloader-exception",
            "source": "https://github.com/pyinstaller/pyinstaller",
            "bundled": True, "receipts": bootloader,
        },
    ]
    for model in MODELS:
        components.append({**model, "kind": "model", "bundled": False, "receipts": model_receipts})
    return components


def _receipt_record(path: Path) -> dict[str, str]:
    try:
        display = str(path.relative_to(ROOT))
    except ValueError:
        display = path.name
    return {"path": display, "sha256": _digest(path)}


def build_payload(output: Path, engine_build: Path, cargo_lock: Path) -> dict[str, int]:
    for path in STATIC_FILES.values():
        if not path.is_file() or path.stat().st_size < 1:
            raise PayloadError(f"missing legal source: {path}")
    components = other_components() + engine_components(engine_build) + crate_components(cargo_lock)
    for component in components:
        if not component["receipts"]:
            raise PayloadError(f"no licence receipt for component: {component['name']}")

    if output.exists() and any(output.iterdir()):
        raise PayloadError(f"legal output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for destination_name, source in STATIC_FILES.items():
        (output / destination_name).write_bytes(source.read_bytes())

    # One text per distinct receipt, named for every component that relies on it.
    # A canonical text carries no copyright line of its own, so the header
    # names the holder for every component that relies on it - that line is
    # what MIT and BSD ask to travel with the software.
    by_digest: dict[str, tuple[Path, list[str]]] = {}
    for component in components:
        if component["kind"] == "first-party":
            continue  # ReadEase's own terms are the LICENSE file beside this one
        holder = component.get("copyright")
        label = f"{component['name']} {component['version']}" + (f" (Copyright {holder})" if holder else "")
        for receipt in component["receipts"]:
            digest = _digest(receipt)
            entry = by_digest.setdefault(digest, (receipt, []))
            entry[1].append(label)
    sections = []
    for digest, (path, users) in sorted(by_digest.items(), key=lambda item: (item[1][0].name.casefold(), item[0])):
        header = f"===== {path.name} | sha256:{digest} =====\nApplies to: {'; '.join(sorted(set(users)))}"
        sections.append(f"{header}\n\n{_readable(path)}")
    (output / "THIRD_PARTY_LICENSES.txt").write_text("\n\n".join(sections) + "\n", encoding="utf-8")

    rows = ["# Third-party inventory", "",
            "Generated from the frozen engine's PyInstaller TOC and the Rust host's `Cargo.lock`.",
            "Licence texts: `THIRD_PARTY_LICENSES.txt`. Machine-readable: `THIRD_PARTY_MANIFEST.json`.", ""]
    for kind, title in (("python", "Python engine (frozen by PyInstaller)"), ("crate", "Rust host (Cargo.lock)"),
                        ("runtime", "Runtime"), ("tool", "Tools linked into the bundle"), ("model", "Models (downloaded on first run, never bundled)")):
        chosen = [c for c in components if c["kind"] == kind]
        if not chosen:
            continue
        rows += [f"## {title}", "", "| Component | Version | Licence | Source |", "| --- | ---: | --- | --- |"]
        rows += [f"| {c['name']} | {c['version']} | {c['license']} | <{c['source']}> |" for c in chosen]
        rows.append("")
    (output / "THIRD_PARTY_INVENTORY.md").write_text("\n".join(rows), encoding="utf-8")

    manifest = {
        "schema_version": 2,
        "source_license": "PolyForm-Noncommercial-1.0.0",
        "binary_distribution_status": "ad-hoc-signed-not-notarized",
        "uv_lock_sha256": _digest(ROOT / "uv.lock"),
        "cargo_lock_sha256": _digest(cargo_lock),
        "components": [
            {k: v for k, v in {
                "name": c["name"], "version": c["version"], "kind": c["kind"], "license": c["license"],
                "source": c["source"], "copyright": c.get("copyright"), "bundled": c["bundled"],
                "receipts": [_receipt_record(p) for p in c["receipts"]],
            }.items() if v is not None}
            for c in sorted(components, key=lambda c: (str(c["kind"]), str(c["name"]).casefold(), str(c["version"])))
        ],
    }
    (output / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    counts = {
        "components": len(components),
        "python": sum(c["kind"] == "python" for c in components),
        "crates": sum(c["kind"] == "crate" for c in components),
        "receipts": len(by_digest),
    }
    print(
        "LICENSE_PAYLOAD PASS components={components} python={python} crates={crates} "
        "receipts={receipts} output={output}".format(output=output, **counts)
    )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--engine-build", type=Path, default=ROOT / "build" / "engine-build" / "readease-engine")
    parser.add_argument("--cargo-lock", type=Path, default=ROOT / "app" / "src-tauri" / "Cargo.lock")
    arguments = parser.parse_args()
    try:
        build_payload(arguments.output, arguments.engine_build, arguments.cargo_lock)
    except (OSError, PayloadError, metadata.PackageNotFoundError, tomllib.TOMLDecodeError) as error:
        print(f"LICENSE_PAYLOAD RED {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
