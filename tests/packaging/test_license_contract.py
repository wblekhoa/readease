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

        apache_receipt = (ROOT / "legal" / "APACHE-2.0.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("Apache License", apache_receipt)
        self.assertIn("Version 2.0, January 2004", apache_receipt)
        self.assertGreater(len(apache_receipt), 10_000)

    def test_checked_in_binary_distribution_contract_names_lgpl_obligations(self) -> None:
        distribution = (ROOT / "legal" / "BINARY_DISTRIBUTION.md").read_text(
            encoding="utf-8"
        )
        qt_notice = (ROOT / "legal" / "QT_THIRD_PARTY_NOTICES.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "LGPL-3.0",
            "relink",
            "reverse engineering",
            "Qt 6.11.2",
            "QtPdf",
            "soxr",
            "source code",
        ):
            self.assertIn(phrase.casefold(), distribution.casefold())
        for phrase in ("PDFium", "FFmpeg", "Chromium", "third-party"):
            self.assertIn(phrase.casefold(), qt_notice.casefold())

    def test_license_payload_is_generated_from_the_locked_environment(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "Legal"
            completed = subprocess.run(
                [
                    sys.executable,
                    ROOT / "scripts" / "package-license-payload.py",
                    "--output",
                    output,
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
            self.assertEqual(manifest["schema_version"], 1)
            self.assertEqual(
                manifest["source_license"],
                "PolyForm-Noncommercial-1.0.0",
            )
            names = {component["name"] for component in manifest["components"]}
            for name in (
                "ReadEase",
                "CPython",
                "PySide6 / Qt",
                "QtPdf / PDFium",
                "VieNeu SDK",
                "VieNeu-TTS v3 Turbo model",
                "MOSS Audio Tokenizer Nano ONNX",
                "onnxruntime",
                "soxr",
                "Nuitka runtime",
            ):
                self.assertIn(name, names)
            components = {
                component["name"]: component for component in manifest["components"]
            }
            self.assertEqual(
                components["ReadEase"]["license"],
                "PolyForm-Noncommercial-1.0.0",
            )
            for name in (
                "tokenizers",
                "VieNeu-TTS v3 Turbo model",
                "MOSS Audio Tokenizer Nano ONNX",
            ):
                receipt_paths = {
                    receipt["path"] for receipt in components[name]["receipts"]
                }
                self.assertIn("legal/APACHE-2.0.txt", receipt_paths)
                self.assertNotIn("LICENSE", receipt_paths)
            licenses = (output / "THIRD_PARTY_LICENSES.txt").read_text(
                encoding="utf-8"
            )
            self.assertGreater(len(licenses), 40_000)
            self.assertIn("Version 2.0, January 2004", licenses)
            self.assertNotIn("PolyForm Noncommercial License", licenses)

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
