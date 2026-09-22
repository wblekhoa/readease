"""Nothing a person wrote may reach the log file.

The owner's rule (21/09): the log carries technical lines only - no document
titles, no passages, no paths into their library. The host already keeps it
(`app/src-tauri/src/log.rs` captures stderr; `engine.rs` logs devices and
timings), and the sidecar writes one line, about a chime that would not
load. Nothing enforced it, so the next `eprintln!` written in a hurry could
put a title in a file people are asked to attach to bug reports.

This reads the sources rather than a running app on purpose: the rule is
about what the code CAN write, and a test that runs a reading would only
prove the lines it happened to take.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: What a line must never interpolate. `title`/`text`/`path` name a person's
#: own words or where they keep them; `segment`/`passage` are the words
#: themselves. `book_id` and `segment_id` are hashes, not content - they are
#: how a bug report is matched to a row, and they stay allowed.
FORBIDDEN = re.compile(
    r"\{[^}]*\b(?:title|titles|text|passage|segment(?!_id)|content|excerpt|"
    r"path|paths|filename|file_name|source_path|book(?!_id))\b[^}]*\}",
    re.IGNORECASE,
)


def rust_log_lines(source: str) -> list[str]:
    """Every `eprintln!`/`println!` argument list in a Rust file."""

    return [match.group(1) for match in re.finditer(r"e?println!\(([^;]*)\)\s*;", source, re.S)]


def python_stderr_lines(source: str) -> list[str]:
    """Every `print(..., file=sys.stderr)` argument list in a Python file."""

    return [
        match.group(1)
        for match in re.finditer(r"print\((.*?file=sys\.stderr[^)]*)\)", source, re.S)
    ]


class LogPrivacyTests(unittest.TestCase):
    def test_the_host_never_logs_a_document_or_a_path(self) -> None:
        checked = 0
        for path in sorted((ROOT / "app/src-tauri/src").glob("*.rs")):
            source = path.read_text(encoding="utf-8")
            # The test module at the bottom of engine.rs prints nothing a
            # user ever sees; it is excluded so fixtures may say "title".
            source = source.split("#[cfg(test)]")[0]
            for line in rust_log_lines(source):
                checked += 1
                self.assertIsNone(
                    FORBIDDEN.search(line),
                    f"{path.name} logs something a person wrote: {line.strip()[:120]}",
                )
        self.assertGreater(checked, 5, "no log lines found - did the pattern rot?")

    def test_the_sidecar_never_logs_a_document_or_a_path(self) -> None:
        for path in sorted((ROOT / "src/vieneu_reader").rglob("*.py")):
            for line in python_stderr_lines(path.read_text(encoding="utf-8")):
                self.assertIsNone(
                    FORBIDDEN.search(line),
                    f"{path.relative_to(ROOT)} logs something a person wrote: {line.strip()[:120]}",
                )

    def test_the_guard_would_notice_a_title_in_a_log_line(self) -> None:
        # Red on purpose: the shapes this test exists to refuse.
        self.assertIsNotNone(FORBIDDEN.search('"[read] {} started", book.title'.replace("book.title", "{title}")))
        self.assertIsNotNone(FORBIDDEN.search('"[import] {path} failed"'))
        self.assertIsNotNone(FORBIDDEN.search('f"could not read {source_path}"'))
        # And the shapes it must allow: ids, counts, device names, versions.
        for allowed in ('"[audio] opened \\"{}\\"", output.name', '"[read] {read_id} done"',
                        'f"progress {segment_id} saved"', '"[engine] pipe closed"'):
            self.assertIsNone(FORBIDDEN.search(allowed), allowed)


if __name__ == "__main__":
    unittest.main()
