from __future__ import annotations

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PackagePreparationTests(unittest.TestCase):
    def test_approved_icon_builds_into_a_valid_icns_file(self) -> None:
        source = ROOT / "assets" / "branding" / "readease-icon-master.png"
        self.assertTrue(source.is_file())
        with TemporaryDirectory() as directory:
            output = Path(directory) / "ReadEase.icns"
            subprocess.run(
                [ROOT / "scripts" / "build-icon.sh", source, output],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 50_000)

    def test_native_selection_bridge_has_a_build_and_test_gate(self) -> None:
        build_script = ROOT / "scripts" / "build-native-selection-bridge.sh"
        test_script = ROOT / "scripts" / "test-native-selection-bridge.sh"
        source = ROOT / "native" / "macos" / "ReadEaseSelectionBridge.m"
        native_source = ROOT / "native" / "macos" / "ReadEaseSelectionNative.m"

        self.assertTrue(build_script.is_file())
        self.assertTrue(test_script.is_file())
        self.assertTrue(source.is_file())
        self.assertTrue(native_source.is_file())
        verify = (ROOT / "scripts" / "verify.sh").read_text(encoding="utf-8")
        self.assertIn("test-native-selection-bridge.sh", verify)

    def test_user_guide_and_notices_cover_local_first_run(self) -> None:
        guide = (ROOT / "README.md").read_text(encoding="utf-8")
        english_guide = (ROOT / "README.en.md").read_text(encoding="utf-8")
        install_guide = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        english_install_guide = (ROOT / "INSTALL.en.md").read_text(encoding="utf-8")
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

        for phrase in (
            "ReadEase — Thư Âm",
            "không cần API key",
            "PDF",
            "EPUB",
            "330 MB",
            "macOS 15",
            "Application Support/VieNeu Reader",
        ):
            self.assertIn(phrase.casefold(), guide.casefold())
        self.assertIn("INSTALL.md", guide)
        self.assertIn("README.en.md", guide)
        for phrase in (
            "Open Anyway",
            "Move to Trash",
            "Privacy & Security",
        ):
            self.assertIn(phrase.casefold(), install_guide.casefold())
        for phrase in (
            "Download ReadEase",
            "Apple Silicon",
            "No API key",
            "Apple Books",
            "PolyForm Noncommercial",
        ):
            self.assertIn(phrase.casefold(), english_guide.casefold())
        for phrase in (
            "Open Anyway",
            "Move to Trash",
        ):
            self.assertIn(phrase.casefold(), english_install_guide.casefold())
        for dependency in ("VieNeu", "pypdfium2", "ONNX Runtime", "Tauri", "PyInstaller"):
            self.assertIn(dependency, notices)

        verify = (ROOT / "scripts" / "verify.sh").read_text(encoding="utf-8")
        self.assertNotIn("SwigPy", verify)

    def test_the_app_never_listens_and_never_carries_a_key(self) -> None:
        """No server, no embedded credential - the two halves that still hold.

        This guard used to ban the string "api_key" outright, on the promise
        in PRIVACY.md: "does not require an API key, run an HTTP server, send
        telemetry, or upload book content". Outside voices (2026-09-04) make
        one of those four conditional: a reader who switches on a paid voice
        sends the text of what they chose to read to the provider THEY picked,
        on THEIR key. Nothing goes to the ReadEase publisher, nothing is
        required, nothing happens by default.

        Banning the string would only have pushed the same code under another
        name, so what it was protecting is asserted directly instead: no
        credential is ever embedded, and nothing listens. The wording in
        PRIVACY.md and both READMEs is the owner's to change - see the PARK
        list in ai-memory/plans/external-ai-voices.md.
        """

        sources = {
            path.relative_to(ROOT): path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "src" / "vieneu_reader").rglob("*.py"))
        }
        joined = "\n".join(sources.values()).lower()

        self.assertNotIn("socketserver", joined)
        self.assertNotIn("uvicorn.run", joined)
        self.assertNotIn(".listen(", joined)
        # The self-check used to be reachable through a `VIENEU_READER_
        # TTS_SELF_CHECK` env var read by the Qt bootstrapper. That
        # bootstrapper is gone; `speech/self_check.py` and its tests are
        # not, but nothing in the shipping app calls them, so there is no
        # longer a hook here to pin. See khe hở #11 in the campaign sổ.

        # A key belongs to the person, never to the build. Any literal shaped
        # like one of the providers' credentials is a key that shipped.
        for prefix in ("sk-", "sk_", "xi-api-key:"):
            for path, source in sources.items():
                for line in source.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    self.assertNotIn(
                        f'"{prefix}', stripped,
                        f"{path} looks like it carries a credential",
                    )

    def test_only_one_directory_may_reach_the_network(self) -> None:
        """Outbound HTTP lives in speech/external/ or it does not exist.

        The privacy claim a reader can still check for themselves is about
        WHERE, not whether: everything that can leave this Mac is in one
        directory, so an audit is reading one folder rather than trusting a
        sentence. Model download is the standing exception - it predates this
        and PRIVACY.md already describes it.
        """

        allowed = {
            Path("src/vieneu_reader/speech/external"),
            # The voice model is fetched by the vendored SDK on prepare, which
            # PRIVACY.md §Network use already sets out.
            Path("src/vieneu_reader/speech/vieneu.py"),
        }
        offenders = []
        for path in sorted((ROOT / "src" / "vieneu_reader").rglob("*.py")):
            relative = path.relative_to(ROOT)
            if any(
                relative == allowance or allowance in relative.parents
                for allowance in allowed
            ):
                continue
            source = path.read_text(encoding="utf-8")
            for marker in ("urllib.request", "http.client", "requests.post", "socket.socket"):
                if marker in source:
                    offenders.append(f"{relative}: {marker}")
        self.assertEqual(offenders, [], "network access outside speech/external/")


if __name__ == "__main__":
    unittest.main()
