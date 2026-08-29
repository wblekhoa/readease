from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import shlex
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

    def test_spec_locks_native_bundle_identity_and_floor(self) -> None:
        parser = ConfigParser()
        parser.read(ROOT / "pysidedeploy.spec")

        self.assertEqual(parser.get("app", "title"), "ReadEase")
        self.assertEqual(
            parser.get("app", "icon"),
            "assets/branding/readease.icns",
        )
        self.assertEqual(parser.get("app", "project_dir"), "..")
        self.assertEqual(parser.get("app", "input_file"), "app_main.py")
        self.assertEqual(parser.get("app", "exec_directory"), "dist")
        self.assertEqual(parser.get("python", "packages"), "")
        self.assertTrue(
            {"Core", "Gui", "Widgets", "Multimedia", "Pdf"}.issubset(
                set(parser.get("qt", "modules").split(","))
            )
        )
        extra_args = parser.get("nuitka", "extra_args")
        for expected in (
            "--include-package=vieneu_reader",
            "--macos-app-name=ReadEase",
            "--macos-signed-app-name=vn.dolenglish.vieneureader",
            "--macos-app-version=0.1.0",
            "--macos-target-arch=arm64",
        ):
            self.assertIn(expected, extra_args)
        tokens = shlex.split(extra_args)
        self.assertIn("--noinclude-qt-translations", tokens)
        self.assertIn("--disable-cache=ccache", tokens)
        self.assertIn("--nofollow-import-to=librosa", tokens)
        for excluded in ("soxr", "soundfile", "kaldi_native_fbank"):
            self.assertIn(f"--nofollow-import-to={excluded}", tokens)
        self.assertFalse(
            any(token.startswith("--include-data-files=THIRD_PARTY_NOTICES") for token in tokens)
        )
        self.assertIn(
            "--include-package-data=vieneu:assets/voices_v3_turbo.json",
            tokens,
        )
        self.assertFalse(
            any(token.startswith("--noinclude-qt-translations=") for token in tokens)
        )
        self.assertFalse(
            any(token.startswith("--macos-app-macos-min-version") for token in tokens)
        )
        plugins = set(parser.get("qt", "plugins").split(","))
        self.assertNotIn("platforminputcontexts", plugins)

    def test_build_script_cannot_silently_install_nuitka(self) -> None:
        script = (ROOT / "scripts" / "build-app.sh").read_text(encoding="utf-8")
        assets = (ROOT / "scripts" / "package-runtime-assets.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn('metadata.version("Nuitka")', script)
        self.assertIn('version == "4.1.1"', script)
        self.assertIn("pysidedeploy.runtime.spec", script)
        self.assertIn("LSMinimumSystemVersion", script)
        self.assertIn("15.0", script)
        self.assertIn("libonnxruntime.1.dylib", script)
        self.assertIn("trap cleanup_build EXIT", script)
        self.assertIn("onnxruntime_alias_created", script)
        self.assertIn('scripts/package-runtime-assets.sh" "$bundle"', script)
        self.assertIn('scripts/build-native-selection-bridge.sh" "$bundle"', script)
        self.assertIn('scripts/deduplicate-runtime-libraries.sh" "$bundle"', script)
        self.assertIn("voices_v3_turbo.json", assets)
        self.assertIn("sea_g2p.bin", assets)
        self.assertIn("--frozen", assets)
        self.assertIn("package-license-payload.py", assets)
        self.assertIn("nuitka-compilation-report.xml", assets)
        self.assertNotIn("uv add", script)
        self.assertNotIn("pip install", script)
        self.assertNotIn("git add -A", script)
        self.assertNotIn("git push --force", script)
        self.assertNotIn("--no-verify", script)

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

    def test_bundle_has_a_whole_macho_macos_floor_gate(self) -> None:
        audit = ROOT / "scripts" / "audit-macos-compatibility.py"
        verify_app = (ROOT / "scripts" / "verify-app.sh").read_text(
            encoding="utf-8"
        )

        self.assertTrue(audit.is_file())
        self.assertIn("audit-macos-compatibility.py", verify_app)

    def test_installer_stops_the_native_hotkey_helper_before_replacement(self) -> None:
        installer = (ROOT / "scripts" / "install-app.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("ReadEaseSelectionBridge", installer)
        self.assertIn('helper="$candidate/Contents/MacOS/', installer)

    def test_build_and_install_rollbacks_are_ephemeral_not_accumulating_backups(
        self,
    ) -> None:
        build = (ROOT / "scripts" / "build-app.sh").read_text(encoding="utf-8")
        installer = (ROOT / "scripts" / "install-app.sh").read_text(
            encoding="utf-8"
        )

        for script in (build, installer):
            self.assertIn("mktemp -d", script)
            self.assertIn("rollback", script)
            self.assertIn("trap", script)
            self.assertNotIn("rm -rf", script)
        self.assertNotIn("build/archive", build)
        self.assertNotIn("ReadEase Backup $(date", installer)
        self.assertNotIn("VieNeu Reader Backup $(date", installer)

    def test_bundle_verifier_removes_its_ephemeral_smoke_workspace(self) -> None:
        verifier = (ROOT / "scripts" / "verify-app.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("cleanup_smoke", verifier)
        self.assertIn("trap cleanup_smoke EXIT", verifier)
        self.assertIn('rm -R -- "$data_root"', verifier)
        self.assertIn('rm -f -- "$crash_marker"', verifier)
        self.assertNotIn('wait "$app_pid"\ntrap - EXIT', verifier)
        # The app is reaped and the pid cleared, so cleanup does not try again.
        self.assertRegex(verifier, r'wait "\$app_pid"(?: \|\| true)?\napp_pid=""')
        # And the reap is bounded: an app that never quits used to hang here
        # forever, with no output, which is how a friend's install froze.
        self.assertIn("READEASE_BUNDLE_LAUNCH_TIMEOUT", verifier)
        self.assertIn("did not quit within", verifier)

    def test_installer_process_matcher_runs_on_macos_awk(self) -> None:
        installer = (ROOT / "scripts" / "install-app.sh").read_text(
            encoding="utf-8"
        )
        marker = 'awk -v executable="$executable" -v helper="$helper" \'\n'
        program_start = installer.index(marker) + len(marker)
        program_end = installer.index("\n    ';", program_start)
        program = installer[program_start:program_end]
        executable = "/tmp/ReadEase.app/Contents/MacOS/app_main"
        helper = "/tmp/ReadEase.app/Contents/MacOS/ReadEaseSelectionBridge"

        for process_line in (executable, f"{helper} --parent 123"):
            completed = subprocess.run(
                [
                    "awk",
                    "-v",
                    f"executable={executable}",
                    "-v",
                    f"helper={helper}",
                    program,
                ],
                input=f"{process_line}\n",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

        unrelated = subprocess.run(
            [
                "awk",
                "-v",
                f"executable={executable}",
                "-v",
                f"helper={helper}",
                program,
            ],
            input="/tmp/unrelated\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(unrelated.returncode, 1, unrelated.stderr)

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
            "Xcode Command Line Tools",
            "Install ReadEase.command",
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
            "Xcode Command Line Tools",
        ):
            self.assertIn(phrase.casefold(), english_install_guide.casefold())
        for dependency in ("VieNeu", "PySide6", "QtPdf", "ONNX Runtime"):
            self.assertIn(dependency, notices)

        verify = (ROOT / "scripts" / "verify.sh").read_text(encoding="utf-8")
        self.assertNotIn("SwigPy", verify)

    def test_codex_run_action_uses_one_native_build_verify_launch_entrypoint(self) -> None:
        runner = (ROOT / "script" / "build_and_run.sh").read_text(encoding="utf-8")

        self.assertIn('APP_NAME="ReadEase"', runner)
        self.assertIn('BUNDLE_ID="vn.dolenglish.vieneureader"', runner)
        self.assertIn('"$ROOT_DIR/scripts/build-app.sh"', runner)
        self.assertIn('"$ROOT_DIR/scripts/verify-app.sh" "$APP_BUNDLE"', runner)
        self.assertIn('/usr/bin/open -n "$APP_BUNDLE"', runner)
        for mode in ("--debug", "--logs", "--telemetry", "--verify"):
            self.assertIn(mode, runner)
        environment_path = ROOT / ".codex" / "environments" / "environment.toml"
        if environment_path.is_file():
            environment = environment_path.read_text(encoding="utf-8")
            self.assertIn('command = "./script/build_and_run.sh"', environment)

    def test_application_source_has_no_api_key_or_listener_entrypoint(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "src" / "vieneu_reader").rglob("*.py"))
        ).lower()

        self.assertNotIn("api_key", source)
        self.assertNotIn("socketserver", source)
        self.assertNotIn("uvicorn.run", source)
        self.assertNotIn(".listen(", source)
        self.assertIn("vieneu_reader_tts_self_check", source)


if __name__ == "__main__":
    unittest.main()
