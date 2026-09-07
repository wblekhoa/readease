"""The shell must take the transport wrapper off before it looks a sentence up.

This file used to be a bridge: the Qt shell's `ui/i18n.py` held the complete
English table, the shell that ships held only the static half, and nobody
checked the two agreed. Both halves reached `app/src/i18n.ts` in `906d785`,
and the Qt shell is now gone, so there is one table and no bridge to guard.
The size-of-the-table teeth moved with the coverage guard, to
`tests/test_translation_coverage.py::TheOracleWasFoundTests`.

What is left is the part that was never about two tables: a table nobody can
consult is the same defect as a table nobody wrote. `engine.rs` puts
`engine refused <method>: ` on the front of every sentence it carries, and an
exact-match lookup cannot fire while that prefix is still there.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHELL_I18N = PROJECT_ROOT / "app" / "src" / "i18n.ts"
ENGINE_RS = PROJECT_ROOT / "app" / "src-tauri" / "src" / "engine.rs"


class TheShellStripsTheTransportWrapperTests(unittest.TestCase):
    def test_the_wrapper_the_shell_strips_is_the_wrapper_the_boundary_writes(
        self,
    ) -> None:
        self.assertIn("engine refused", SHELL_I18N.read_text(encoding="utf-8"))
        self.assertIn(
            'return Err(format!("engine refused {method}: {said}"));',
            ENGINE_RS.read_text(encoding="utf-8"),
            "the wrapper the shell strips is no longer the wrapper the "
            "boundary writes, so every named sentence falls back to raw",
        )


if __name__ == "__main__":
    unittest.main()
