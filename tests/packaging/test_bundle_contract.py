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


def _is_macho(path: Path) -> bool:
    with path.open("rb") as source:
        return source.read(4) in MACHO_MAGICS


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
        self.assertFalse(any("mupdf" in path.casefold() for path in bundle_paths))
        # Qt's own names left with the Qt shell - the shipped bundle is Rust +
        # WebKit + a PyInstaller sidecar and carries none of them. What stays
        # is about the ENGINE, which did not change shells.
        for forbidden in ("soxr_ext.so", "_soundfile.py"):
            self.assertFalse(any(forbidden in path for path in bundle_paths))
        for absent in ("QtPdf", "QtVirtualKeyboard", "PySide6", "libshiboken"):
            self.assertFalse(
                any(absent in path for path in bundle_paths),
                f"{absent} is Qt-era and must not be in a Tauri bundle",
            )

    def test_onnxruntime_dylib_is_dropped_because_no_macho_links_it(self) -> None:
        shipped = [
            str(path.relative_to(BUNDLE))
            for path in BUNDLE.rglob("*")
            if "libonnxruntime" in path.name
        ]
        machos = 0
        linkers = []
        for path in sorted(BUNDLE.rglob("*"), key=str):
            if path.is_symlink() or not path.is_file() or not _is_macho(path):
                continue
            machos += 1
            result = subprocess.run(
                ["otool", "-L", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
            if "libonnxruntime" in result.stdout:
                linkers.append(str(path.relative_to(BUNDLE)))

        self.assertEqual(shipped, [])
        self.assertGreater(machos, 0)
        self.assertEqual(linkers, [])

    def test_bundle_carries_its_licence_and_notices(self) -> None:
        """The payload in the bundle is the one generated for THIS bundle.

        Four static documents match the source tree byte for byte; the three
        generated ones are bound to the locks this tree was built from, and
        every crate the host links appears in the inventory - the check that
        keeps the shipped attribution from going stale.
        """

        import tomllib
        from hashlib import sha256

        legal = BUNDLE / "Contents" / "Resources" / "Legal"
        static = {"LICENSE", "NOTICE.md", "THIRD_PARTY_NOTICES.md"}
        generated = {
            "THIRD_PARTY_INVENTORY.md",
            "THIRD_PARTY_LICENSES.txt",
            "THIRD_PARTY_MANIFEST.json",
        }
        self.assertTrue(legal.is_dir(), f"no licence payload at {legal}")
        self.assertEqual(
            {path.name for path in legal.iterdir()},
            static | generated | {"BINARY_DISTRIBUTION.md"},
        )
        for name in sorted(static):
            self.assertEqual(
                (legal / name).read_bytes(),
                (ROOT / name).read_bytes(),
                f"{name} in the bundle differs from the one in the source tree",
            )
        self.assertEqual(
            (legal / "BINARY_DISTRIBUTION.md").read_bytes(),
            (ROOT / "legal" / "BINARY_DISTRIBUTION.md").read_bytes(),
        )
        cargo_lock = ROOT / "app" / "src-tauri" / "Cargo.lock"
        manifest = json.loads((legal / "THIRD_PARTY_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["cargo_lock_sha256"], sha256(cargo_lock.read_bytes()).hexdigest())
        self.assertEqual(manifest["uv_lock_sha256"], sha256((ROOT / "uv.lock").read_bytes()).hexdigest())
        shipped = {(c["name"], c["version"]) for c in manifest["components"]}
        crates = {
            (package["name"], package["version"])
            for package in tomllib.loads(cargo_lock.read_text(encoding="utf-8"))["package"]
            if "source" in package
        }
        self.assertTrue(crates.issubset(shipped), sorted(crates - shipped)[:10])
        for name in ("VieNeu SDK", "onnxruntime", "pypdfium2", "PyInstaller bootloader"):
            self.assertIn(name, {n for n, _ in shipped}, name)
        self.assertGreater((legal / "THIRD_PARTY_LICENSES.txt").stat().st_size, 1_000_000)

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
