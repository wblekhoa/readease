from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectContractTests(unittest.TestCase):
    def test_project_metadata_pins_supported_runtime_and_dependencies(self) -> None:
        pyproject_path = PROJECT_ROOT / "pyproject.toml"

        self.assertTrue(pyproject_path.is_file())
        with pyproject_path.open("rb") as pyproject_file:
            project = tomllib.load(pyproject_file)["project"]

        self.assertEqual(project["requires-python"], ">=3.13,<3.14")
        # This list is spelled out so a dependency cannot arrive unnoticed.
        # numpy was added deliberately when playback started stretching audio
        # to change speed without changing pitch; vieneu already brought it,
        # so the bundle did not grow - only the declaration is new.
        self.assertEqual(
            project["dependencies"],
            [
                "vieneu==3.6.3",
                "PySide6>=6.8,<7",
                "numpy>=2,<3",
                # pypdfium2 replaced QtPdf for PDF extraction so the headless
                # sidecar can import books without a Qt runtime (Tauri plan,
                # milestone B). The Qt shell has retired; PySide6 stays
                # until `integrations/macos_selection.py`,
                # `integrations/macos_settings.py` and
                # `playback/qt_audio.py` are decided - they still import
                # it and are the owner's call, not a cleanup.
                "pypdfium2>=5.13.0",
            ],
        )

    def test_verification_script_exists_and_is_executable(self) -> None:
        verification_script = PROJECT_ROOT / "scripts" / "verify.sh"

        self.assertTrue(verification_script.is_file())
        self.assertNotEqual(verification_script.stat().st_mode & 0o111, 0)


if __name__ == "__main__":
    unittest.main()
