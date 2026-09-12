from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[2]


class LicenseContractTests(unittest.TestCase):
    def test_public_repository_has_privacy_security_and_contribution_guides(self) -> None:
        expected = {
            "PRIVACY.md": ("local", "clipboard", "model"),
            "SECURITY.md": ("security advisory", "book content", "model"),
            "CONTRIBUTING.md": (
                "scripts/verify.sh",
                "uv.lock",
                "PolyForm-Noncommercial-1.0.0",
            ),
        }
        for filename, phrases in expected.items():
            content = (ROOT / filename).read_text(encoding="utf-8")
            for phrase in phrases:
                self.assertIn(phrase.casefold(), content.casefold())

    def test_source_declares_polyform_noncommercial_with_notice(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as source:
            project = tomllib.load(source)["project"]

        self.assertEqual(project["license"], "PolyForm-Noncommercial-1.0.0")
        self.assertEqual(project["license-files"], ["LICENSE", "NOTICE.md"])
        self.assertEqual(project["readme"], "README.md")
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("PolyForm Noncommercial License 1.0.0", license_text)
        self.assertIn("Any noncommercial purpose is a permitted purpose.", license_text)
        self.assertIn("Changes and New Works License", license_text)
        self.assertGreater(len(license_text), 3_000)
        self.assertEqual(
            sha256((ROOT / "LICENSE").read_bytes()).hexdigest(),
            "c0ea4a896d2c8c394b29f9427589996db826cd501c512279ff0ed3ef48fabbe5",
        )

        notice = (ROOT / "NOTICE.md").read_text(encoding="utf-8")
        required_notice = (
            "Required Notice: Copyright © 2026 Lê Khoa. "
            "ReadEase — Thư Âm original scaffold. "
            "Provenance ID READEASE-THU-AM-NC-2026-01. "
            "Noncommercial use only under PolyForm Noncommercial 1.0.0."
        )
        self.assertIn(required_notice, notice)
        self.assertIn("commercial use", notice.casefold())
        self.assertIn("third-party", notice.casefold())

        apache_receipt = (ROOT / "legal" / "spdx" / "Apache-2.0.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("Apache License", apache_receipt)
        self.assertIn("Version 2.0, January 2004", apache_receipt)
        self.assertGreater(len(apache_receipt), 10_000)

    def test_both_readmes_name_the_licence_above_the_pitch(self) -> None:
        """A reader decides whether they may use this before they read what it does."""
        for filename, permission in (
            ("README.md", "phi thương mại"),
            ("README.en.md", "noncommercial"),
        ):
            head = (ROOT / filename).read_text(encoding="utf-8")[:500]
            self.assertIn("PolyForm Noncommercial 1.0.0", head, filename)
            self.assertIn("(LICENSE)", head, filename)
            self.assertIn(permission, head.casefold(), filename)

    def test_binary_distribution_receipt_describes_the_tauri_bundle(self) -> None:
        distribution = (ROOT / "legal" / "BINARY_DISTRIBUTION.md").read_text(
            encoding="utf-8"
        )
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for phrase in (
            "Tauri",
            "PyInstaller",
            "THIRD_PARTY_INVENTORY.md",
            "THIRD_PARTY_LICENSES.txt",
            "THIRD_PARTY_MANIFEST.json",
            "MPL-2.0",
            "Bootloader",
            "no Qt",
        ):
            self.assertIn(phrase, distribution, phrase)
        for phrase in ("VieNeu", "ONNX Runtime", "pypdfium2", "PDFium", "Tauri", "symphonia", "MODEL_PROVENANCE.md"):
            self.assertIn(phrase, notices, phrase)
        # The Qt shell is gone; a receipt that still promised LGPL relinking
        # would be describing a binary nobody builds.
        for gone in ("LGPL-3.0", "relink", "QtPdf", "Nuitka"):
            self.assertNotIn(gone, distribution, gone)

    def test_license_payload_is_generated_from_what_the_bundle_contains(self) -> None:
        """The payload is read off the artefact: the frozen engine's TOC and Cargo.lock.

        Needs a frozen engine on this machine (`scripts/build-sidecar.sh`); the
        bundle gate checks the same payload inside a finished bundle.
        """

        engine_build = ROOT / "build" / "engine-build" / "readease-engine"
        if not list(engine_build.glob("PYZ-*.toc")):
            self.skipTest("no frozen engine under build/engine-build - run scripts/build-sidecar.sh")
        cargo_lock = ROOT / "app" / "src-tauri" / "Cargo.lock"
        with TemporaryDirectory() as directory:
            output = Path(directory) / "Legal"
            completed = subprocess.run(
                [
                    sys.executable,
                    ROOT / "scripts" / "package-license-payload.py",
                    "--output", output,
                    "--engine-build", engine_build,
                    "--cargo-lock", cargo_lock,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            required = {
                "LICENSE",
                "NOTICE.md",
                "THIRD_PARTY_NOTICES.md",
                "THIRD_PARTY_INVENTORY.md",
                "THIRD_PARTY_LICENSES.txt",
                "THIRD_PARTY_MANIFEST.json",
                "BINARY_DISTRIBUTION.md",
            }
            self.assertEqual({path.name for path in output.iterdir()}, required)
            self.assertEqual(
                (output / "NOTICE.md").read_bytes(),
                (ROOT / "NOTICE.md").read_bytes(),
            )
            manifest = json.loads(
                (output / "THIRD_PARTY_MANIFEST.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["source_license"], "PolyForm-Noncommercial-1.0.0")
            self.assertEqual(
                manifest["cargo_lock_sha256"], sha256(cargo_lock.read_bytes()).hexdigest()
            )
            self.assertEqual(
                manifest["uv_lock_sha256"], sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
            )
            components = {
                (component["name"], component["version"]): component
                for component in manifest["components"]
            }
            names = {name for name, _ in components}
            for name in (
                "ReadEase",
                "CPython",
                "PyInstaller bootloader",
                "VieNeu SDK",
                "VieNeu-TTS v3 Turbo model",
                "MOSS Audio Tokenizer Nano ONNX",
                "onnxruntime",
                "pypdfium2",
                "tokenizers",
                "tauri",
                "wry",
            ):
                self.assertIn(name, names, name)
            for gone in ("PySide6 / Qt", "QtPdf / PDFium", "Nuitka runtime", "shiboken6"):
                self.assertNotIn(gone, names, gone)

            # Every crate the host links is in the inventory - the check that
            # keeps this payload from going stale a second time.
            lock = tomllib.loads(cargo_lock.read_text(encoding="utf-8"))
            crates = {
                (package["name"], package["version"])
                for package in lock["package"]
                if "source" in package
            }
            self.assertGreater(len(crates), 400)
            self.assertTrue(crates.issubset(components), sorted(crates - set(components))[:10])
            self.assertEqual(
                sum(component["kind"] == "crate" for component in manifest["components"]),
                len(crates),
            )
            kinds = {component["kind"] for component in manifest["components"]}
            self.assertEqual(kinds, {"first-party", "runtime", "tool", "model", "python", "crate"})
            self.assertGreater(
                sum(component["kind"] == "python" for component in manifest["components"]), 30
            )
            for component in manifest["components"]:
                self.assertTrue(component["receipts"], component["name"])
                self.assertTrue(component["source"], component["name"])
            self.assertEqual(
                components[("ReadEase", "0.1.0")]["license"], "PolyForm-Noncommercial-1.0.0"
            )
            for name in ("VieNeu-TTS v3 Turbo model", "MOSS Audio Tokenizer Nano ONNX"):
                component = next(c for c in manifest["components"] if c["name"] == name)
                self.assertFalse(component["bundled"])
                self.assertIn(
                    "legal/spdx/Apache-2.0.txt",
                    {receipt["path"] for receipt in component["receipts"]},
                )
            licenses = (output / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")
            self.assertGreater(len(licenses), 1_000_000)
            self.assertIn("Version 2.0, January 2004", licenses)
            self.assertIn("Mozilla Public License Version 2.0", licenses)
            self.assertNotIn("PolyForm Noncommercial License", licenses)
            inventory = (output / "THIRD_PARTY_INVENTORY.md").read_text(encoding="utf-8")
            for name in ("VieNeu SDK", "tauri", "symphonia-core", "PyInstaller bootloader"):
                self.assertIn(f"| {name} |", inventory, name)

    def test_public_source_audit_passes_the_allowlisted_export_surface(self) -> None:
        completed = subprocess.run(
            [sys.executable, ROOT / "scripts" / "audit-public-release.py", "--strict"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PUBLIC_RELEASE_AUDIT PASS", completed.stdout)
        history = "requires-clean-squash" if (ROOT / ".git").exists() else "clean-export"
        self.assertIn(f"history={history}", completed.stdout)


if __name__ == "__main__":
    unittest.main()
