"""A document may promise the source install only while it can still build.

The source path compiles `pysidedeploy.spec`'s `input_file`. That file went
with the Qt shell on 2026-09-08, so the path now fails after ten to twenty-five
minutes of building - the worst possible way for a friend to find out. The
documents were changed to say so; this is what keeps the two in step.

It is deliberately two-directional. If someone repoints the source path at a
build that works, the loud warnings become the lie instead, and this goes red
until they are taken out.
"""

from __future__ import annotations

import configparser
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Every document that sends a person down the source path.
ADVERTISEMENTS = ("README.md", "README.en.md", "INSTALL.md", "INSTALL.en.md")

# The sentence each one carries while the path is broken. One per document,
# in the language that document is written in.
WARNINGS = {
    "README.md": "Đường cài từ nguồn đang không dựng được",
    "README.en.md": "The source install does not build right now",
    "INSTALL.md": "Đường cài từ nguồn trong tài liệu này đang không dựng được",
    "INSTALL.en.md": "The source install described here does not build right now",
}


class SourceInstallPromiseTests(unittest.TestCase):
    def _build_entry_point(self) -> Path:
        parser = configparser.ConfigParser()
        parser.read(ROOT / "pysidedeploy.spec")
        return ROOT / parser.get("app", "input_file")

    def test_the_documents_agree_with_whether_the_source_path_can_build(self) -> None:
        entry = self._build_entry_point()
        buildable = entry.is_file()

        for name in ADVERTISEMENTS:
            document = (ROOT / name).read_text(encoding="utf-8")
            warned = WARNINGS[name] in document
            with self.subTest(document=name):
                if buildable:
                    self.assertFalse(
                        warned,
                        f"{name} still warns that the source install is broken, "
                        f"but {entry.name} is back and the path can build again",
                    )
                else:
                    self.assertTrue(
                        warned,
                        f"{entry.name} does not exist, so the source path cannot "
                        f"build - and {name} does not say so. A reader following "
                        f"it spends 10-25 minutes to reach a failure.",
                    )

    def test_the_installer_stops_before_the_build_instead_of_during_it(self) -> None:
        """The documents warn; the file a person double-clicks has to as well.

        A friend who never reads the README opens `Install ReadEase.command`.
        Twenty-five minutes of building and then a compiler trace is the worst
        way to learn the path is retired, so the check runs before anything is
        downloaded, and it reads the entry point out of the spec rather than
        naming a file.
        """

        installer = (ROOT / "Install ReadEase.command").read_text(encoding="utf-8")
        buildable = self._build_entry_point().is_file()

        self.assertIn(
            "pysidedeploy.spec",
            installer,
            "the installer no longer asks the spec what it is about to build",
        )
        guarded = "cannot build right now" in installer
        if buildable:
            self.assertFalse(
                guarded,
                "the entry point is back but the installer still refuses to run",
            )
        else:
            self.assertTrue(
                guarded,
                "the entry point is gone and the installer still starts a build "
                "that cannot finish",
            )

    def test_the_entry_point_is_read_from_the_spec_not_guessed(self) -> None:
        # A rename in the spec must move this guard with it, not silently
        # leave it checking a path nothing builds.
        self.assertEqual(self._build_entry_point().name, "app_main.py")


if __name__ == "__main__":
    unittest.main()
