from __future__ import annotations

import json
from pathlib import Path
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / "scripts" / "export-public-source.py"
MANIFEST = ROOT / "scripts" / "public-source-manifest.json"


class PublicSourceExportTests(unittest.TestCase):
    def test_manifest_is_the_single_allowlist_for_export_and_audit(self) -> None:
        self.assertTrue(MANIFEST.is_file())
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("INSTALL.md", payload["root_files"])
        self.assertIn("INSTALL.en.md", payload["root_files"])
        self.assertIn("Install ReadEase.command", payload["root_files"])
        self.assertIn("README.en.md", payload["root_files"])
        for directory in ("assets", "legal", "native", "script", "scripts", "src", "tests"):
            self.assertIn(directory, payload["directories"])
        self.assertTrue({"__pycache__", ".git"}.issubset(payload["excluded_names"]))

        exporter_source = EXPORTER.read_text(encoding="utf-8")
        audit_source = (ROOT / "scripts" / "audit-public-release.py").read_text(
            encoding="utf-8"
        )
        for source in (exporter_source, audit_source):
            self.assertIn("public-source-manifest.json", source)

    def test_clean_export_and_zip_are_history_free_auditable_and_executable(self) -> None:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            output = temp / "ReadEase-source-0.1.0"
            archive = temp / "ReadEase-source-0.1.0.zip"
            completed = subprocess.run(
                [
                    sys.executable,
                    EXPORTER,
                    "--output",
                    output,
                    "--archive",
                    archive,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PUBLIC_SOURCE_EXPORT PASS", completed.stdout)
            self.assertTrue((output / "INSTALL.md").is_file())
            self.assertTrue((output / "INSTALL.en.md").is_file())
            self.assertTrue((output / "README.md").is_file())
            self.assertTrue((output / "README.en.md").is_file())
            self.assertTrue((output / "uv.lock").is_file())
            command = output / "Install ReadEase.command"
            self.assertTrue(command.is_file())
            self.assertTrue(command.stat().st_mode & stat.S_IXUSR)
            for forbidden in (
                ".git",
                ".codex",
                "ai-memory",
                "build",
                "dist",
                ".venv",
                "docs",
            ):
                self.assertFalse((output / forbidden).exists())
            self.assertFalse(any(path.name == "__pycache__" for path in output.rglob("*")))
            self.assertFalse(any(path.suffix == ".pyc" for path in output.rglob("*")))

            audit = subprocess.run(
                [
                    sys.executable,
                    output / "scripts" / "audit-public-release.py",
                    "--strict",
                    "--source-root",
                    output,
                ],
                cwd=output,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(audit.returncode, 0, audit.stderr)
            self.assertIn("history=clean-export", audit.stdout)

            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as zipped:
                names = set(zipped.namelist())
                command_name = f"{output.name}/Install ReadEase.command"
                self.assertIn(command_name, names)
                command_mode = zipped.getinfo(command_name).external_attr >> 16
                self.assertTrue(command_mode & stat.S_IXUSR)
                self.assertFalse(any("/.git/" in name for name in names))

    def test_export_refuses_to_overwrite_an_existing_destination(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "existing"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("owner data", encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, EXPORTER, "--output", output],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("destination_exists", completed.stderr)
            self.assertEqual(marker.read_text(encoding="utf-8"), "owner data")

    def test_clean_export_audit_ignores_only_declared_build_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "source"
            exported = subprocess.run(
                [sys.executable, EXPORTER, "--output", output],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            generated = (
                output / ".venv" / "placeholder",
                output / "build" / "runtime.spec",
                output / "dist" / "ReadEase.app" / "placeholder",
                output / "src" / "vieneu_reader" / "__pycache__" / "module.pyc",
            )
            for path in generated:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("derived", encoding="utf-8")

            allowed = subprocess.run(
                [
                    sys.executable,
                    output / "scripts" / "audit-public-release.py",
                    "--strict",
                    "--source-root",
                    output,
                ],
                cwd=output,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

            (output / "private-notes.txt").write_text("not allowlisted", encoding="utf-8")
            rejected = subprocess.run(
                [
                    sys.executable,
                    output / "scripts" / "audit-public-release.py",
                    "--strict",
                    "--source-root",
                    output,
                ],
                cwd=output,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("unexpected clean-export artifact", rejected.stderr)

    def test_clean_export_audit_rejects_a_modified_polyform_license(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "source"
            exported = subprocess.run(
                [sys.executable, EXPORTER, "--output", output],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            license_path = output / "LICENSE"
            license_path.write_text(
                license_path.read_text(encoding="utf-8") + "\nmodified\n",
                encoding="utf-8",
            )

            audit = subprocess.run(
                [
                    sys.executable,
                    output / "scripts" / "audit-public-release.py",
                    "--strict",
                    "--source-root",
                    output,
                ],
                cwd=output,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(audit.returncode, 0)
            self.assertIn("official PolyForm license digest", audit.stderr)


if __name__ == "__main__":
    unittest.main()
