"""The launch check must always end, even when the app never quits itself.

A friend's install stopped at step 5 with no output at all. The built app is
launched there and told to quit after 1.5 seconds; the timer that does that is
armed only after the window exists, so anything blocking before it - a
first-launch Gatekeeper scan of a 300 MB bundle, a dialog - left the script
waiting forever with nothing on screen.
"""

import os
import time
from pathlib import Path
import stat
import subprocess
from tempfile import TemporaryDirectory
import unittest

ORPHAN_PROBE = f"bundle-gate-orphan-probe-{os.getpid()}"


ROOT = Path(__file__).resolve().parents[2]
VERIFY_APP = ROOT / "scripts" / "verify-app.sh"

PLIST = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
    '<plist version="1.0"><dict>'
    "<key>CFBundleExecutable</key><string>app_main</string>"
    "</dict></plist>\n"
)


def _executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class BundleGateNeverHangsTests(unittest.TestCase):
    def _run(self, app_body: str, timeout_seconds: str):
        with TemporaryDirectory() as name:
            temp = Path(name)
            fake_bin = temp / "bin"
            fake_bin.mkdir()
            # The three checks before the launch are covered by their own tests;
            # here they only have to be out of the way.
            _executable(fake_bin / "uv", "#!/bin/sh\nexit 0\n")
            # A helper named after this test run: grepping for a bare "sleep"
            # would also see one another test legitimately owns right then.
            helper = fake_bin / ORPHAN_PROBE
            helper.write_text("#!/bin/sh\nexec sleep \"$1\"\n", encoding="utf-8")
            helper.chmod(0o755)
            app_body = app_body.replace("__HELPER__", str(helper))

            bundle = temp / "ReadEase.app"
            (bundle / "Contents" / "MacOS").mkdir(parents=True)
            (bundle / "Contents" / "Info.plist").write_text(PLIST, encoding="utf-8")
            _executable(bundle / "Contents" / "MacOS" / "app_main", app_body)

            return subprocess.run(
                [str(VERIFY_APP), str(bundle)],
                capture_output=True,
                text=True,
                check=False,
                # Twice the gate's own budget: if the gate works, this never bites.
                timeout=60,
                env={
                    **os.environ,
                    "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                    "READEASE_BUNDLE_LAUNCH_TIMEOUT": timeout_seconds,
                    # The gate makes its own temp dirs and refuses to clean any
                    # path outside TMPDIR, so leave the real one in place.
                },
            )

    def test_nothing_the_app_started_is_left_running(self) -> None:
        """The gate stops the app, and the app is not always the only process:
        ReadEase starts a selection helper. Killing just the one this script
        launched would strand the rest on every run."""
        # A helper the app starts, then the app's own wait: the gate has to
        # stop both, not only the process it launched.
        completed = self._run("#!/bin/sh\n__HELPER__ 600 &\nsleep 600\n", "3")

        self.assertNotEqual(completed.returncode, 0)
        # Give the group kill a moment to land before looking.
        time.sleep(1)
        survivors = subprocess.run(
            ["pgrep", "-f", ORPHAN_PROBE],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            survivors.stdout.strip(),
            "",
            "the gate left a process behind: " + survivors.stdout,
        )

    def test_an_app_that_never_quits_is_stopped_and_reported(self) -> None:
        completed = self._run("#!/bin/sh\nsleep 600\n", "3")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("did not quit within 3s", completed.stderr)

    def test_the_stuck_app_is_not_left_running_afterwards(self) -> None:
        marker = "readease-gate-hang-probe"
        completed = self._run(f"#!/bin/sh\nexec sleep 601 # {marker}\n", "3")

        self.assertNotEqual(completed.returncode, 0)
        survivors = subprocess.run(
            ["pgrep", "-f", marker], capture_output=True, text=True, check=False
        )
        self.assertEqual(survivors.stdout.strip(), "", "a stuck app was left behind")

    def test_an_app_that_quits_on_its_own_still_passes(self) -> None:
        completed = self._run("#!/bin/sh\nsleep 1\n", "30")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("BUNDLE_GATE PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
