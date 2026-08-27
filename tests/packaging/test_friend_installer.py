from __future__ import annotations

import os
from pathlib import Path
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


class FriendInstallerTests(unittest.TestCase):
    def _run_harness(
        self,
        *arguments: str,
        arch: str = "arm64",
        macos: str = "15.4",
        available_kib: int = 8 * 1024 * 1024,
        xcode_ready: bool = True,
        include_uv: bool = True,
        curl_succeeds: bool = False,
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
                "TMPDIR": str(temp),
            }
            completed = subprocess.run(
                [scripts / INSTALLER.name, *arguments],
                cwd=project,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            actions = action_log.read_text(encoding="utf-8") if action_log.exists() else ""
            return completed, actions

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


if __name__ == "__main__":
    unittest.main()
