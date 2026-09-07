"""The shipping shell must carry every engine sentence the engine can say.

Two tables held the same words for a while and nobody checked they agreed.
The Qt shell's `ui/i18n.py` had a complete English table; the shell that
actually ships had only the static half of it, so an English interface printed
the engine's Vietnamese - `TranslationCoverageTests` stayed green throughout,
because it guards that a translation EXISTS, not that anyone reads it.

This is the bridge between the two while both exist. When the Qt shell goes,
`app/src/i18n.ts` becomes the only table and the coverage guard reads it there;
until then, a sentence added on the Python side and forgotten on the shell side
is a reader seeing Vietnamese, and it should be a red test instead.

Read by regex rather than import: the far side is TypeScript, and a Python test
cannot import it. Same shape as the tab-name guard.
"""

from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHELL_I18N = PROJECT_ROOT / "app" / "src" / "i18n.ts"
QT_I18N = PROJECT_ROOT / "src" / "vieneu_reader" / "ui" / "i18n.py"


def _python_tables() -> tuple[dict[str, str], list[tuple[str, str]]]:
    """`_RUNTIME_EN` and `_RUNTIME_PATTERNS`, read without importing.

    `ui/i18n.py` sits inside a package whose imports pull the whole engine in;
    the literals are all this needs, so it parses the file instead.
    """
    tree = ast.parse(QT_I18N.read_text(encoding="utf-8"))
    runtime: dict[str, str] = {}
    patterns: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        if node.target.id == "_RUNTIME_EN":
            runtime = ast.literal_eval(node.value)
        elif node.target.id == "_RUNTIME_PATTERNS":
            for element in node.value.elts:
                call, replacement = element.elts
                patterns.append(
                    (ast.literal_eval(call.args[0]), ast.literal_eval(replacement))
                )
    return runtime, patterns


class ShellCarriesEngineSentencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shell = SHELL_I18N.read_text(encoding="utf-8")
        self.runtime, self.patterns = _python_tables()

    def test_the_tables_were_both_found(self) -> None:
        # A rename on either side would otherwise empty this file's teeth
        # while leaving it green.
        self.assertGreater(len(self.runtime), 100)
        self.assertGreater(len(self.patterns), 10)
        self.assertIn("RUNTIME_EN", self.shell)
        self.assertIn("RUNTIME_PATTERNS", self.shell)

    def test_every_engine_sentence_reached_the_shell(self) -> None:
        missing = [
            vietnamese
            for vietnamese, english in self.runtime.items()
            if json.dumps(vietnamese, ensure_ascii=False) not in self.shell
            or json.dumps(english, ensure_ascii=False) not in self.shell
        ]

        self.assertEqual(
            missing,
            [],
            "these engine sentences have an English translation in the Qt "
            "shell but not in the shell that ships, so a reader with the "
            "interface in English sees them in Vietnamese:\n"
            + "\n".join(missing),
        )

    def test_every_pattern_reached_the_shell(self) -> None:
        missing = []
        for source, replacement in self.patterns:
            # `\1` on the Python side is `$1` on the shell side; the pattern
            # source itself crosses unchanged.
            shell_replacement = re.sub(r"\\(\d)", r"$\1", replacement)
            if json.dumps(source, ensure_ascii=False) not in self.shell:
                missing.append(f"pattern: {source}")
            elif json.dumps(shell_replacement, ensure_ascii=False) not in self.shell:
                missing.append(f"replacement: {shell_replacement}")

        self.assertEqual(missing, [], "\n".join(missing))

    def test_the_shell_strips_the_transport_wrapper(self) -> None:
        # A table nobody consults was the whole defect, and an exact-match
        # lookup cannot fire while `engine refused <method>: ` is still on
        # the front of the sentence. `engine.rs` writes that prefix.
        self.assertIn("engine refused", self.shell)
        self.assertIn(
            'return Err(format!("engine refused {method}: {said}"));',
            (PROJECT_ROOT / "app" / "src-tauri" / "src" / "engine.rs").read_text(
                encoding="utf-8"
            ),
            "the wrapper the shell strips is no longer the wrapper the "
            "boundary writes",
        )


if __name__ == "__main__":
    unittest.main()
