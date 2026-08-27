from __future__ import annotations

import os
import pty
from pathlib import Path
import select
import shutil
import stat
import subprocess
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "install-from-source.sh"
DOUBLE_CLICK_INSTALLER = ROOT / "Install ReadEase.command"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class _InstallerHarness:
    """Runs the real installer against faked system tools."""

    @staticmethod
    def _run_on_a_terminal(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        answers: str,
    ) -> subprocess.CompletedProcess[str]:
        """Drive the installer through a real pty so `[[ -t 0 ]]` is true.

        A pty merges stdout and stderr; combined output lands in .stdout.
        """
        master, slave = pty.openpty()
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True,
        )
        os.close(slave)
        if answers:
            os.write(master, answers.encode("utf-8"))
        chunks: list[bytes] = []
        while True:
            readable, _, _ = select.select([master], [], [], 60)
            if not readable:
                break
            try:
                piece = os.read(master, 4096)
            except OSError:
                break
            if not piece:
                break
            chunks.append(piece)
        returncode = process.wait(timeout=60)
        os.close(master)
        return subprocess.CompletedProcess(
            command,
            returncode,
            b"".join(chunks).decode("utf-8", "replace"),
            "",
        )

    def _run_harness(
        self,
        *arguments: str,
        arch: str = "arm64",
        macos: str = "15.4",
        available_kib: int = 8 * 1024 * 1024,
        xcode_ready: bool = True,
        include_uv: bool = True,
        curl_succeeds: bool = False,
        existing_version: str | None = None,
        legacy_app: bool = False,
        stale_workspaces: int = 0,
        quarantined: bool = False,
        tty_answers: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            project = temp / "ReadEase"
            scripts = project / "scripts"
            fake_bin = temp / "bin"
            scripts.mkdir(parents=True)
            fake_bin.mkdir()
            shutil.copy2(INSTALLER, scripts / INSTALLER.name)
            (project / "uv.lock").write_text("version = 1\n", encoding="utf-8")
            (project / "pyproject.toml").write_text(
                '[project]\nname = "vieneu-reader"\n',
                encoding="utf-8",
            )
            (project / "scripts" / "audit-public-release.py").write_text(
                "raise SystemExit(0)\n",
                encoding="utf-8",
            )

            # Hermetic install root: never read the developer's real ~/Applications.
            install_root = temp / "Applications"
            install_root.mkdir()
            if existing_version is not None:
                contents = install_root / "ReadEase.app" / "Contents"
                contents.mkdir(parents=True)
                (contents / "Info.plist").write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0"><dict>'
                    "<key>CFBundleShortVersionString</key>"
                    f"<string>{existing_version}</string>"
                    "</dict></plist>\n",
                    encoding="utf-8",
                )
            if legacy_app:
                (install_root / "VieNeu Reader.app" / "Contents").mkdir(parents=True)
            for index in range(stale_workspaces):
                stale = temp / f"readease-source-install.stale{index}"
                stale.mkdir()
                (stale / "filler").write_text("x" * 4096, encoding="utf-8")

            if quarantined:
                # What a browser-downloaded ZIP looks like once expanded.
                subprocess.run(
                    ["xattr", "-w", "com.apple.quarantine", "0083;0;Safari;", str(project)],
                    check=True,
                )

            action_log = temp / "actions.log"
            _write_executable(
                scripts / "export-public-source.py",
                """#!/usr/bin/env python3
import pathlib
import shutil
import sys
source = pathlib.Path(__file__).resolve().parents[1]
destination = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])
destination.mkdir()
(destination / 'scripts').mkdir()
for name in ('build-app.sh', 'install-app.sh'):
    shutil.copy2(source / 'scripts' / name, destination / 'scripts' / name)
""",
            )
            for name, marker in (
                ("build-app.sh", "build"),
                ("install-app.sh", "install"),
            ):
                _write_executable(
                    scripts / name,
                    f'#!/bin/sh\nprintf "{marker}\\n" >> "$READEASE_TEST_LOG"\n',
                )

            _write_executable(
                fake_bin / "uname",
                """#!/bin/sh
case "$1" in
  -s) printf 'Darwin\\n' ;;
  -m) printf '%s\\n' "$READEASE_FAKE_ARCH" ;;
  *) exit 2 ;;
esac
""",
            )
            _write_executable(
                fake_bin / "sw_vers",
                """#!/bin/sh
[ "$1" = "-productVersion" ] || exit 2
printf '%s\\n' "$READEASE_FAKE_MACOS"
""",
            )
            _write_executable(
                fake_bin / "df",
                """#!/bin/sh
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\n'
printf 'fixture 99999999 1 %s 1%% /\\n' "$READEASE_FAKE_AVAILABLE_KIB"
""",
            )
            _write_executable(
                fake_bin / "xcrun",
                """#!/bin/sh
if [ "$READEASE_FAKE_XCODE" = "1" ]; then
  printf '/usr/bin/clang\\n'
  exit 0
fi
exit 1
""",
            )
            _write_executable(
                fake_bin / "curl",
                """#!/bin/sh
[ "$READEASE_FAKE_CURL" = "1" ] && exit 0
exit 7
""",
            )
            if include_uv:
                _write_executable(
                    fake_bin / "uv",
                    """#!/bin/sh
if [ "$1" = "--version" ]; then
  printf 'uv 0.9.13\\n'
  exit 0
fi
if [ "$1" = "run" ]; then
  shift
  while [ "$1" != "python" ]; do shift; done
  shift
  exec /usr/bin/python3 "$@"
fi
exit 2
""",
                )

            environment = {
                **os.environ,
                "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                "READEASE_FAKE_ARCH": arch,
                "READEASE_FAKE_MACOS": macos,
                "READEASE_FAKE_AVAILABLE_KIB": str(available_kib),
                "READEASE_FAKE_XCODE": "1" if xcode_ready else "0",
                "READEASE_FAKE_CURL": "1" if curl_succeeds else "0",
                "READEASE_TEST_LOG": str(action_log),
                "READEASE_INSTALL_ROOT": str(install_root),
                "TMPDIR": str(temp),
            }
            if tty_answers is None:
                completed = subprocess.run(
                    [scripts / INSTALLER.name, *arguments],
                    cwd=project,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            else:
                completed = self._run_on_a_terminal(
                    [str(scripts / INSTALLER.name), *arguments],
                    cwd=project,
                    env=environment,
                    answers=tty_answers,
                )
            actions = action_log.read_text(encoding="utf-8") if action_log.exists() else ""
            return completed, actions


class FriendInstallerTests(_InstallerHarness, unittest.TestCase):
    def test_double_click_installer_is_executable_and_delegates(self) -> None:
        self.assertTrue(DOUBLE_CLICK_INSTALLER.is_file())
        self.assertTrue(DOUBLE_CLICK_INSTALLER.stat().st_mode & stat.S_IXUSR)
        source = DOUBLE_CLICK_INSTALLER.read_text(encoding="utf-8")
        self.assertIn("scripts/install-from-source.sh", source)
        self.assertIn("-t 0", source)

    def test_preflight_rejects_unsupported_architecture(self) -> None:
        completed, actions = self._run_harness("--check", arch="x86_64")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported_arch", completed.stderr)
        self.assertEqual(actions, "")

    def test_preflight_rejects_macos_14(self) -> None:
        completed, actions = self._run_harness("--check", macos="14.7.6")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported_macos", completed.stderr)
        self.assertEqual(actions, "")

    def test_preflight_requires_six_gibibytes_of_free_space(self) -> None:
        completed, actions = self._run_harness(
            "--check",
            available_kib=(6 * 1024 * 1024) - 1,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("insufficient_disk", completed.stderr)
        self.assertEqual(actions, "")

    def test_preflight_explains_missing_xcode_command_line_tools(self) -> None:
        completed, actions = self._run_harness("--check", xcode_ready=False)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("missing_xcode_tools", completed.stderr)
        self.assertIn("xcode-select --install", completed.stderr)
        self.assertEqual(actions, "")

    def test_check_mode_has_no_build_or_install_side_effect(self) -> None:
        completed, actions = self._run_harness("--check")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READEASE_PREFLIGHT PASS", completed.stdout)
        self.assertEqual(actions, "")

    def test_happy_path_builds_and_installs_from_an_ephemeral_clean_export(self) -> None:
        completed, actions = self._run_harness()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(actions, "build\ninstall\n")
        self.assertIn("READEASE_SOURCE_INSTALL PASS", completed.stdout)
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('UV_CACHE_DIR="$work_root/uv-cache"', source)
        self.assertIn('UV_PYTHON_INSTALL_DIR="$work_root/uv-python"', source)
        self.assertNotIn("uv cache clean", source)

    def test_missing_uv_uses_a_pinned_fail_closed_download(self) -> None:
        completed, actions = self._run_harness(include_uv=False)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("uv_download_failed", completed.stderr)
        self.assertEqual(actions, "")
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("UV_VERSION=\"0.9.13\"", source)
        self.assertIn("uv-aarch64-apple-darwin.tar.gz", source)
        self.assertIn("UV_ARCHIVE_SHA256=", source)
        self.assertIn("shasum -a 256", source)
        self.assertNotIn("curl | sh", source)

    def test_build_script_is_source_checkout_safe_and_lock_bound(self) -> None:
        source = (ROOT / "scripts" / "build-app.sh").read_text(encoding="utf-8")

        self.assertNotIn("git branch --show-current", source)
        self.assertNotIn("branch must match auto/*", source)
        self.assertIn("uv sync --locked", source)
        self.assertIn("--managed-python", source)
        self.assertIn("--python 3.13", source)


class InstallerClarityTests(_InstallerHarness, unittest.TestCase):
    """Progress, existing-install detection, and residue guidance."""

    def test_check_reports_when_no_previous_install_exists(self) -> None:
        completed, actions = self._run_harness("--check")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READEASE_EXISTING none", completed.stdout)
        self.assertEqual(actions, "")

    def test_check_reports_an_existing_install_and_that_it_is_replaced(self) -> None:
        completed, _ = self._run_harness("--check", existing_version="0.1.0")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READEASE_EXISTING installed version=0.1.0", completed.stdout)
        # The user must be told the outcome, not left guessing.
        self.assertIn("replaces it", completed.stdout)

    def test_check_reports_a_legacy_bundle_that_will_be_removed(self) -> None:
        completed, _ = self._run_harness("--check", legacy_app=True)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READEASE_LEGACY present", completed.stdout)

    def test_check_reports_stale_failed_build_workspaces_without_deleting(self) -> None:
        completed, _ = self._run_harness("--check", stale_workspaces=2)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READEASE_STALE_BUILD count=2", completed.stdout)
        # Report-only: it prints a command, it must never remove anything itself.
        self.assertIn("rm -R", completed.stdout)
        # --check is a dry run: it reports, it never removes.
        self.assertNotIn("removed=", completed.stdout)

    def test_check_detects_gatekeeper_quarantine_and_gives_the_exact_fix(self) -> None:
        completed, _ = self._run_harness("--check", quarantined=True)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READEASE_QUARANTINE present", completed.stdout)
        self.assertIn("xattr -d com.apple.quarantine", completed.stdout)
        self.assertIn("git clone", completed.stdout)

    def test_check_reports_no_quarantine_for_a_git_clone(self) -> None:
        completed, _ = self._run_harness("--check")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READEASE_QUARANTINE none", completed.stdout)

    def test_a_brand_new_machine_installs_without_asking_anything(self) -> None:
        """Nothing installed, nothing stale: never interrupt the person."""
        completed, actions = self._run_harness(tty_answers="")

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(actions, "build\ninstall\n")
        self.assertNotIn("[Y/n]", completed.stdout)
        self.assertNotIn("[y/N]", completed.stdout)

    def test_an_existing_install_is_confirmed_on_a_terminal(self) -> None:
        completed, actions = self._run_harness(
            existing_version="0.1.0",
            tty_answers="y\n",
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("[Y/n]", completed.stdout)
        self.assertEqual(actions, "build\ninstall\n")

    def test_declining_the_replacement_stops_before_building(self) -> None:
        completed, actions = self._run_harness(
            existing_version="0.1.0",
            tty_answers="n\n",
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("READEASE_SOURCE_INSTALL CANCELLED", completed.stdout)
        self.assertEqual(actions, "")

    def test_stale_workspaces_can_be_cleaned_when_the_person_agrees(self) -> None:
        completed, actions = self._run_harness(
            stale_workspaces=2,
            tty_answers="y\n",
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("READEASE_STALE_BUILD removed=2", completed.stdout)
        self.assertEqual(actions, "build\ninstall\n")

    def test_a_non_interactive_run_never_blocks_on_a_question(self) -> None:
        """AI-assistant and CI runs have no tty; they must not hang."""
        completed, actions = self._run_harness(
            existing_version="0.1.0",
            stale_workspaces=1,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("non-interactive", completed.stdout)
        self.assertEqual(actions, "build\ninstall\n")
        # The safe default keeps diagnostics; only a person may remove them.
        self.assertNotIn("removed=", completed.stdout)

    def test_install_emits_ordered_progress_steps(self) -> None:
        completed, actions = self._run_harness()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(actions, "build\ninstall\n")
        steps = [
            line.split()[1]
            for line in completed.stdout.splitlines()
            if line.startswith("READEASE_STEP ")
        ]
        self.assertEqual(steps, ["1/5", "2/5", "3/5", "4/5", "5/5"])

    def test_failed_install_explains_how_to_reclaim_the_preserved_workspace(self) -> None:
        completed, _ = self._run_harness(include_uv=False)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("READEASE_BUILD_PRESERVED", completed.stderr)
        # A preserved workspace is multi-gigabyte; never leave it unexplained.
        self.assertIn("rm -R", completed.stderr)


if __name__ == "__main__":
    unittest.main()
