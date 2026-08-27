from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
import plistlib
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[2]


class _FakeApplication:
    def __init__(self) -> None:
        self.properties: dict[str, object] = {}

    def setProperty(self, name: str, value: object) -> None:  # Qt-compatible shape
        self.properties[name] = value


class ProvenanceContractTests(unittest.TestCase):
    def _module(self):
        return importlib.import_module("vieneu_reader.provenance")

    def test_payload_is_static_project_provenance_not_an_install_fingerprint(self) -> None:
        provenance = self._module()

        self.assertEqual(
            provenance.REQUIRED_NOTICE,
            "Required Notice: Copyright © 2026 Lê Khoa. "
            "ReadEase — Thư Âm original scaffold. "
            "Provenance ID READEASE-THU-AM-NC-2026-01. "
            "Noncommercial use only under PolyForm Noncommercial 1.0.0.",
        )

        first = provenance.provenance_payload()
        second = provenance.provenance_payload()
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            {
                "schema_version": 1,
                "product": "ReadEase — Thư Âm",
                "provenance_id": "READEASE-THU-AM-NC-2026-01",
                "license_id": "PolyForm-Noncommercial-1.0.0",
                "required_notice": provenance.REQUIRED_NOTICE,
                "scope": "first-party-software-and-scaffold",
                "tracking": False,
            },
        )
        serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "username",
            "hostname",
            "device_id",
            "installation_id",
            "serial_number",
            "timestamp",
            "email",
        ):
            self.assertNotIn(forbidden, serialized.casefold())

    def test_runtime_sets_hidden_qt_properties_without_io(self) -> None:
        provenance = self._module()
        application = _FakeApplication()

        provenance.apply_provenance(application)

        self.assertEqual(
            application.properties,
            {
                "ReadEaseProvenanceID": provenance.PROVENANCE_ID,
                "ReadEaseLicenseIdentifier": provenance.LICENSE_ID,
                "ReadEaseRequiredNotice": provenance.REQUIRED_NOTICE,
                "ReadEaseProvenanceTracking": False,
            },
        )

        source_path = ROOT / "src" / "vieneu_reader" / "provenance.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(
            imports.isdisjoint(
                {
                    "datetime",
                    "getpass",
                    "http",
                    "os",
                    "pathlib",
                    "platform",
                    "requests",
                    "socket",
                    "subprocess",
                    "time",
                    "urllib",
                    "uuid",
                }
            )
        )

    def test_application_applies_provenance_before_building_runtime(self) -> None:
        source = (ROOT / "src" / "vieneu_reader" / "__main__.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("from vieneu_reader.provenance import apply_provenance", source)
        self.assertLess(
            source.index("apply_provenance(application)"),
            source.index("runtime = build_runtime"),
        )

    def test_packager_writes_matching_resource_and_plist_metadata(self) -> None:
        provenance = self._module()
        script = ROOT / "scripts" / "package-provenance.py"
        self.assertTrue(script.is_file())

        with TemporaryDirectory() as directory:
            bundle = Path(directory) / "ReadEase.app"
            contents = bundle / "Contents"
            contents.mkdir(parents=True)
            plist_path = contents / "Info.plist"
            with plist_path.open("wb") as handle:
                plistlib.dump({"CFBundleName": "ReadEase"}, handle)

            completed = subprocess.run(
                [sys.executable, script, "--bundle", bundle],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PROVENANCE_PACKAGE PASS", completed.stdout)
            payload_path = (
                contents
                / "Resources"
                / "Provenance"
                / "READEASE_PROVENANCE.json"
            )
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload, provenance.provenance_payload())
            with plist_path.open("rb") as handle:
                plist = plistlib.load(handle)
            self.assertEqual(plist["ReadEaseProvenanceID"], provenance.PROVENANCE_ID)
            self.assertEqual(plist["ReadEaseLicenseIdentifier"], provenance.LICENSE_ID)
            self.assertEqual(plist["ReadEaseRequiredNotice"], provenance.REQUIRED_NOTICE)
            self.assertFalse(plist["ReadEaseProvenanceTracking"])

    def test_build_and_clean_export_include_the_provenance_contract(self) -> None:
        runtime_assets = (ROOT / "scripts" / "package-runtime-assets.sh").read_text(
            encoding="utf-8"
        )
        manifest = json.loads(
            (ROOT / "scripts" / "public-source-manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn("package-provenance.py", runtime_assets)
        self.assertIn("NOTICE.md", manifest["root_files"])

        privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn("READEASE-THU-AM-NC-2026-01", privacy)
        self.assertIn("not generated from the user", privacy)
        self.assertIn("not transmitted anywhere", privacy)


if __name__ == "__main__":
    unittest.main()
