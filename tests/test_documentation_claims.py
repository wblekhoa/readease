"""What the documents promise must be what the app does.

These used to live beside the Qt shell's translation tests because that is
where the tab's name was read from. The name now comes out of the shell that
ships (`app/src/i18n.ts`, changed in `cc9c3f8`) and the Qt shell is going, so
the guard moves to where nothing is about to be deleted under it.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


class AppleBooksDisclosureTests(unittest.TestCase):
    """The Move notes tab reads a person's Books library; the docs must say so.

    A surface that reaches into another app's data is exactly where a stale
    privacy document becomes a lie, so these pin the claim to the behaviour.
    """

    ROOT = Path(__file__).resolve().parents[1]

    def _prose(self, name: str) -> str:
        # Collapse wrapping: these are claims, and a claim does not stop being
        # made because the line broke in the middle of it.
        return " ".join((self.ROOT / name).read_text(encoding="utf-8").split())

    def test_privacy_states_what_is_read_and_when(self) -> None:
        privacy = self._prose("PRIVACY.md")
        self.assertIn("Apple Books library", privacy)
        self.assertIn("Nothing is read until you open that tab", privacy)
        self.assertIn("Previewing never opens the originals for writing", privacy)

    def test_privacy_discloses_the_write_and_every_bound_on_it(self) -> None:
        """The write is the part someone would most regret not being told about.

        Each bound here is enforced somewhere in code; if one is ever dropped,
        this is the reminder that a promise was made about it in writing.
        """

        privacy = self._prose("PRIVACY.md")
        self.assertIn("does write to Apple Books", privacy)
        for bound in (
            "only runs when you press the button",
            "refuses while Apple Books is running",
            "only ever inserts",
            "one transaction",
            "iCloud",
        ):
            self.assertIn(bound, privacy, f"PRIVACY.md no longer promises: {bound}")

    def test_the_documented_backup_folder_is_the_one_the_code_writes_to(self) -> None:
        """Where to look when you want your notes back is not a place to guess.

        The app root keeps its pre-rebrand folder name on purpose, so the
        plausible-looking "ReadEase/" path is wrong in exactly the situation
        someone would be reading this document.
        """

        from vieneu_reader.config import default_app_root

        backups = default_app_root() / "AppleBooksBackups"
        documented = f"~/Library/Application Support/{backups.parent.name}/AppleBooksBackups/"
        for name in ("PRIVACY.md", "README.md", "README.en.md"):
            self.assertIn(documented, self._prose(name), f"{name} points elsewhere")

    def test_privacy_does_not_promise_an_undo_icloud_can_take_away(self) -> None:
        """The backup stops being a clean undo once Apple Books has synced.

        Saying "built to be undone" without that bound is the overclaim this
        document exists to avoid.
        """

        privacy = self._prose("PRIVACY.md")
        self.assertIn("clean undo only while Apple Books has not launched", privacy)
        self.assertIn("delete them inside Apple Books", privacy)

    def _shipped_tab_name(self) -> tuple[str, str]:
        """The tab's two names, read out of the shell that actually ships.

        They used to be read out of the Qt localizer, which is on its way out;
        a name taken from a shell nobody runs would stop being the name on the
        screen the moment the two drifted. `app/src/i18n.ts` is what the reader
        sees, so that is where the claim has to be pinned.
        """

        source = (self.ROOT / "app" / "src" / "i18n.ts").read_text(encoding="utf-8")
        found = re.search(
            r'"nav\.transfer":\s*\[\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\]',
            source,
        )
        self.assertIsNotNone(
            found,
            "app/src/i18n.ts no longer declares nav.transfer; the documents "
            "below have nothing left to be checked against",
        )
        assert found is not None  # narrowed for the type checker
        return found.group(1), found.group(2)

    def test_every_surface_calls_the_tab_the_same_thing(self) -> None:
        """One name, taken from the app rather than retyped here.

        The tab moves notes now; it was still called "Compare notes" in the app
        and "Move notes" in PRIVACY.md, so someone looking for how to move their
        notes found a tab that said it only compared them. Reading the name out
        of the shipping shell means renaming it again cannot leave a document
        behind.
        """

        vietnamese, english = self._shipped_tab_name()
        for name, expected in (
            ("README.md", vietnamese),
            ("README.en.md", english),
            ("PRIVACY.md", english),
        ):
            body = self._prose(name)
            with self.subTest(document=name):
                self.assertIn(
                    expected,
                    body,
                    f"{name} does not call the tab {expected!r}",
                )
        for name in ("README.md", "README.en.md"):
            self.assertIn("PRIVACY.md", (self.ROOT / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
