"""Every Vietnamese sentence the engine can say must have an English one.

The table used to live in the Qt shell (`ui/i18n.py`) and this guard imported
it. That shell is being removed, and `app/src/i18n.ts` — the shell that
actually ships — is where the two tables now live. So the oracle is read from
there: by regex, because a Python test cannot import TypeScript. Same shape as
the tab-name guard and `test_shell_fault_codes.py`.

Membership is a containment check on the JSON form of the sentence. Both sides
escape the same way (`\\"` inside a string, no `\\u` for Vietnamese), so a
quoted literal matches a whole table entry and nothing smaller.
"""

from __future__ import annotations

import ast
import json
import re
import unicodedata
import unittest
from pathlib import Path

import vieneu_reader
from vieneu_reader.provenance import REQUIRED_NOTICE


PACKAGE_ROOT = Path(vieneu_reader.__file__).resolve().parent
SHELL_I18N = Path(__file__).resolve().parents[1] / "app" / "src" / "i18n.ts"

_SHELL = SHELL_I18N.read_text(encoding="utf-8")


def _region(start: str, end: str) -> str:
    """The source between two declarations, so a match means a table entry.

    A rename on the shell side lands here rather than three tests later with
    an empty table and nothing to report.
    """

    if start not in _SHELL or end not in _SHELL:
        raise AssertionError(
            f"{SHELL_I18N.name} no longer declares {start!r}..{end!r}; this "
            "guard reads the shipping tables by name and has just lost one"
        )
    opened = _SHELL.index(start)
    closed = _SHELL.index(end, opened)
    return _SHELL[opened:closed]


# The static interface table and the engine-sentence table, as source text.
TEXT_REGION = _region("export const TEXT = {", "export type TextKey")
RUNTIME_REGION = _region("const RUNTIME_EN", "const RUNTIME_PATTERNS")
PATTERN_REGION = _region("const RUNTIME_PATTERNS", "const ENGINE_REFUSAL")

# `new RegExp("...")` — the first argument, still JSON-escaped, so `json.loads`
# gives back the pattern source Python can compile.
_TS_STRING = r'"(?:[^"\\]|\\.)*"'
RUNTIME_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(json.loads(literal))
    for literal in re.findall(rf"new RegExp\(({_TS_STRING})", PATTERN_REGION)
)

# An f-string piece is translated as part of the whole message, so a piece of a
# known pattern is already covered. These unescaped sources are only ever used
# for that literal containment check; they are never compiled again.
PATTERN_LITERALS: tuple[str, ...] = tuple(
    pattern.pattern.replace("\\", "") for pattern in RUNTIME_PATTERNS
)


def _is_a_table_entry(text: str, region: str) -> bool:
    return json.dumps(text, ensure_ascii=False) in region


PACKAGE_ROOT = Path(vieneu_reader.__file__).resolve().parent

# The two base letters and the tone marks that make a string Vietnamese.
VIETNAMESE_LETTERS = "đĐăĂâÂêÊôÔơƠưƯ"

# Vietnamese that is correct as it is: the product name, the legally fixed
# notice, the label of the Vietnamese option itself, and the sentences the
# Vietnamese voice speaks instead of the interface showing them.
UNTRANSLATED_BY_DESIGN: frozenset[tuple[str, str]] = frozenset(
    {
        ("identity.py", "ReadEase — Thư Âm"),
        ("provenance.py", "ReadEase — Thư Âm"),
        ("provenance.py", REQUIRED_NOTICE),
        (
            "speech/self_check.py",
            "Xin chào. ReadEase đang kiểm tra giọng đọc tiếng Việt.",
        ),
        # Same class: the two sentences the voice SAYS between sentences of
        # the book, in the language of the book. They carry their English on
        # the next line of the same dict, and
        # `tests/headless/test_server.py::SpokenCueTests` checks that every
        # language the app reads in has a line - which is more than a table
        # lookup ever checked about them.
        ("headless/server.py", "Xem hình {number}."),
        ("headless/server.py", "Nói thêm, {text}"),
        # Abbreviations the sentence splitter matches against. They are data
        # for a matcher, never text anyone reads, so there is nothing to
        # translate; an English build must still not split "ĐH. Bách Khoa".
        ("domain/prosody.py", "đh"),
        # Same class: the conjunctions and reference nouns the enumerator
        # rule matches ("hoặc (b)", "mục (b)") are matcher data for
        # Vietnamese book text, not words the app says to anyone.
        (
            "domain/prosody.py",
            r"\s*(?:,\s*)?\b(hoặc|hay|và|rồi|cũng như)\s+\(([a-z])\)",
        ),
        (
            "domain/prosody.py",
            r"\b(mục|điểm|phần|khoản|ý|câu|trường hợp|phương án|lựa chọn)\s+\(([a-z])\)",
        ),
        ("domain/prosody.py", "cđ"),
        # The Vietnamese alphabet itself, used to recognise which language a
        # book is written in. An alphabet has no translation - the English
        # build needs these exact letters to tell a Vietnamese book from an
        # English one, which is what keeps the Vietnamese model away from
        # English text.
        ("domain/language.py", "ăâđêôơưĂÂĐÊÔƠƯ"),
        # The division words a Roman numeral can stand behind. Matcher data
        # for Vietnamese book text, like the two rules above - an English
        # build reading a Vietnamese book still has to know that "Phần II"
        # is a number.
        *(("domain/prosody.py", cue) for cue in (
            "chương", "quyển", "tập", "mục", "hồi", "kỳ", "phụ lục",
        )),
        # What the voice SAYS in place of a web address, in the language of
        # the book it is reading. Not shown anywhere; there is no screen to
        # translate it on.
        ("domain/prosody.py", "đường dẫn"),
        ("domain/prosody.py", "địa chỉ"),
        ("domain/prosody.py", "địa chỉ "),
        ("domain/prosody.py", " chấm "),
        # The figure-label matcher: the words a Vietnamese (or English) book
        # opens a caption with - "Hình 1.1.", "Figure 3". Matcher data for
        # book text, never shown; an English build reading a Vietnamese book
        # still has to recognise "Hình 1.1" as the book's own label.
        (
            "domain/presentation.py",
            r"^\s*(hình|ảnh|minh họa|figure|fig\.?)\s*(\d+(?:[.\-–]\d+)*[a-z]?)(?!\w)",
        ),
        # The content-pattern detectors: a translator's image annotation and
        # a prose reference to a numbered figure. Matcher data for book text.
        (
            "domain/content_patterns.py",
            r"^\s*(chú giải ảnh|mô tả ảnh|image description)\s*:",
        ),
        (
            "domain/content_patterns.py",
            r"\(\s*(?:xem\s+)?(?:hình|ảnh|minh họa|figure|fig\.?)\s*"
            r"(\d+(?:[.\-–]\d+)*[a-z]?)\s*\)",
        ),
    }
)


def is_vietnamese(text: str) -> bool:
    for character in text:
        if character in VIETNAMESE_LETTERS:
            return True
        decomposed = unicodedata.normalize("NFD", character)
        if len(decomposed) > 1 and decomposed[0].isascii() and decomposed[0].isalpha():
            return True
    return False


def has_english(text: str) -> bool:
    if _is_a_table_entry(text, RUNTIME_REGION) or _is_a_table_entry(text, TEXT_REGION):
        return True
    if any(pattern.fullmatch(text) for pattern in RUNTIME_PATTERNS):
        return True
    return any(text in literal for literal in PATTERN_LITERALS)


def docstring_nodes(tree: ast.Module) -> set[int]:
    documented = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    identifiers: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, documented) or not node.body:
            continue
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            identifiers.add(id(first.value))
    return identifiers


def vietnamese_constants() -> list[tuple[str, int, str]]:
    """Every Vietnamese string the package can put in front of a person."""

    constants: list[tuple[str, int, str]] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        module = path.relative_to(PACKAGE_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstrings = docstring_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or id(node) in docstrings:
                continue
            if isinstance(node.value, str) and is_vietnamese(node.value):
                constants.append((module, node.lineno, node.value))
    return sorted(constants)


class TranslationCoverageTests(unittest.TestCase):
    def test_every_vietnamese_string_has_an_english_translation(self) -> None:
        missing = [
            f"{module}:{line} {value!r}"
            for module, line, value in vietnamese_constants()
            if (module, value) not in UNTRANSLATED_BY_DESIGN and not has_english(value)
        ]

        self.assertEqual(
            missing,
            [],
            "Vietnamese text can reach the interface with no English translation:\n"
            + "\n".join(missing),
        )

    def test_untranslated_allowlist_still_describes_the_source(self) -> None:
        present = {(module, value) for module, _line, value in vietnamese_constants()}

        self.assertEqual(UNTRANSLATED_BY_DESIGN - present, set())


class TheOracleWasFoundTests(unittest.TestCase):
    """A rename on the shell side would otherwise empty this file's teeth.

    Every check above passes trivially against an empty table: nothing is
    missing when nothing is expected. So the sizes are pinned first.
    """

    def test_the_shipping_tables_are_where_this_file_looks(self) -> None:
        self.assertGreater(len(RUNTIME_REGION), 5_000)
        self.assertGreater(len(TEXT_REGION), 5_000)
        self.assertGreater(len(RUNTIME_PATTERNS), 10)
        # A sentence known to be in each table, so a region that stops being
        # the table it is named after does not stay green.
        self.assertTrue(
            _is_a_table_entry(
                "PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR.", RUNTIME_REGION
            )
        )
        self.assertTrue(_is_a_table_entry("Thư viện", TEXT_REGION))


if __name__ == "__main__":
    unittest.main()
