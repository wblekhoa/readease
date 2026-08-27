from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = Path(
    os.environ.get(
        "VIENEU_READER_BUNDLE_PATH",
        ROOT / "dist" / "ReadEase.app",
    )
)
BUNDLE_GATE = os.environ.get("VIENEU_READER_BUNDLE_TEST") == "1"


@unittest.skipUnless(BUNDLE_GATE, "bundle gate is opt-in")
class BundleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not BUNDLE.is_dir():
            raise AssertionError(f"bundle does not exist: {BUNDLE}")
        cls.plist_path = BUNDLE / "Contents" / "Info.plist"
        with cls.plist_path.open("rb") as handle:
            cls.plist = plistlib.load(handle)
        cls.executable = (
            BUNDLE / "Contents" / "MacOS" / cls.plist["CFBundleExecutable"]
        )

    def test_bundle_metadata(self) -> None:
        self.assertEqual(
            self.plist["CFBundleIdentifier"],
            "vn.dolenglish.vieneureader",
        )
        self.assertEqual(self.plist["CFBundleName"], "ReadEase")
        self.assertEqual(self.plist["CFBundleDisplayName"], "ReadEase")
        self.assertEqual(self.plist["CFBundleShortVersionString"], "0.1.0")
        self.assertEqual(self.plist["LSMinimumSystemVersion"], "15.0")
        self.assertTrue(self.plist.get("NSHighResolutionCapable", False))
        icon_name = self.plist.get("CFBundleIconFile")
        self.assertTrue(icon_name)
        if not str(icon_name).endswith(".icns"):
            icon_name = f"{icon_name}.icns"
        self.assertTrue((BUNDLE / "Contents" / "Resources" / icon_name).is_file())

    def test_executable_is_native_arm64(self) -> None:
        self.assertTrue(self.executable.is_file())
        result = subprocess.run(
            ["file", str(self.executable)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("arm64", result.stdout)

    def test_bundle_is_strictly_signed(self) -> None:
        subprocess.run(
            ["plutil", "-lint", str(self.plist_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["codesign", "--verify", "--deep", "--strict", str(BUNDLE)],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_native_selection_helper_is_arm64_and_signed(self) -> None:
        helper = BUNDLE / "Contents" / "MacOS" / "ReadEaseSelectionBridge"
        native_library = (
            BUNDLE
            / "Contents"
            / "MacOS"
            / "libReadEaseSelectionNative.dylib"
        )
        self.assertTrue(helper.is_file())
        self.assertTrue(native_library.is_file())
        file_result = subprocess.run(
            ["file", str(helper)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("arm64", file_result.stdout)
        library_result = subprocess.run(
            ["file", str(native_library)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("arm64", library_result.stdout)
        subprocess.run(
            ["codesign", "--verify", "--strict", str(helper)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["codesign", "--verify", "--strict", str(native_library)],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_required_assets_are_bundled_but_models_are_not(self) -> None:
        notices = list(BUNDLE.rglob("THIRD_PARTY_NOTICES.md"))
        voice_assets = list(BUNDLE.rglob("voices_v3_turbo.json"))
        phoneme_assets = list(BUNDLE.rglob("sea_g2p.bin"))
        forbidden_model_names = {
            "vieneu_prefill.onnx",
            "vieneu_decode_step.onnx",
            "vieneu_acoustic_cached.onnx",
            "vieneu_backbone_shared.data",
            "vieneu_v3_heads.npz",
        }
        bundled_names = {path.name for path in BUNDLE.rglob("*") if path.is_file()}
        bundle_paths = {str(path) for path in BUNDLE.rglob("*")}

        self.assertEqual(len(notices), 1)
        self.assertEqual(len(voice_assets), 1)
        self.assertGreater(voice_assets[0].stat().st_size, 1_000)
        self.assertEqual(len(phoneme_assets), 1)
        self.assertGreater(phoneme_assets[0].stat().st_size, 10_000_000)
        self.assertTrue(forbidden_model_names.isdisjoint(bundled_names))
        self.assertTrue((BUNDLE / "Contents" / "MacOS" / "QtPdf").is_file())
        self.assertFalse(any("mupdf" in path.casefold() for path in bundle_paths))
        for forbidden in (
            "QtVirtualKeyboard",
            "QtVirtualKeyboardQml",
            "libqtvirtualkeyboardplugin.dylib",
            "soxr_ext.so",
            "_soundfile.py",
        ):
            self.assertFalse(any(forbidden in path for path in bundle_paths))

    def test_onnxruntime_compatibility_name_is_a_symlink_not_a_duplicate(self) -> None:
        macos = BUNDLE / "Contents" / "MacOS"
        compatibility_name = macos / "libonnxruntime.1.dylib"
        versioned = [
            path
            for path in macos.glob("libonnxruntime.*.dylib")
            if path != compatibility_name
        ]

        self.assertEqual(len(versioned), 1)
        self.assertTrue(compatibility_name.is_symlink())
        self.assertEqual(compatibility_name.resolve(), versioned[0].resolve())

    def test_bundle_contains_a_machine_auditable_license_payload(self) -> None:
        legal = BUNDLE / "Contents" / "Resources" / "Legal"
        required = {
            "LICENSE",
            "NOTICE.md",
            "THIRD_PARTY_NOTICES.md",
            "THIRD_PARTY_LICENSES.txt",
            "THIRD_PARTY_MANIFEST.json",
            "BINARY_DISTRIBUTION.md",
        }

        self.assertEqual({path.name for path in legal.iterdir()}, required)
        self.assertEqual(
            (legal / "LICENSE").read_bytes(),
            (ROOT / "LICENSE").read_bytes(),
        )
        self.assertEqual(
            (legal / "NOTICE.md").read_bytes(),
            (ROOT / "NOTICE.md").read_bytes(),
        )
        manifest = json.loads(
            (legal / "THIRD_PARTY_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(
            manifest["source_license"],
            "PolyForm-Noncommercial-1.0.0",
        )
        self.assertTrue(manifest["components"])

    def test_bundle_contains_deterministic_nontracking_provenance(self) -> None:
        from vieneu_reader.provenance import provenance_payload

        provenance_path = (
            BUNDLE
            / "Contents"
            / "Resources"
            / "Provenance"
            / "READEASE_PROVENANCE.json"
        )
        self.assertTrue(provenance_path.is_file())
        payload = json.loads(provenance_path.read_text(encoding="utf-8"))
        self.assertEqual(payload, provenance_payload())
        self.assertEqual(self.plist["ReadEaseProvenanceID"], payload["provenance_id"])
        self.assertEqual(
            self.plist["ReadEaseLicenseIdentifier"], payload["license_id"]
        )
        self.assertEqual(
            self.plist["ReadEaseRequiredNotice"], payload["required_notice"]
        )
        self.assertFalse(self.plist["ReadEaseProvenanceTracking"])
        self.assertFalse(payload["tracking"])


if __name__ == "__main__":
    unittest.main()
