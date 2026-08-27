from __future__ import annotations

import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unicodedata
import unittest

import vieneu_reader
from vieneu_reader.provenance import REQUIRED_NOTICE
from vieneu_reader.ui.i18n import (
    _RUNTIME_EN,
    _RUNTIME_PATTERNS,
    _TEXT,
    Language,
    LanguagePreferenceStore,
    Localizer,
)


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
        ("ui/window.py", "🇻🇳 Tiếng Việt"),
        (
            "speech/self_check.py",
            "Xin chào. ReadEase đang kiểm tra giọng đọc tiếng Việt.",
        ),
        ("ui/controller.py", "Mời bạn xem Hình "),
    }
)

# An f-string piece is translated as part of the whole message, so a piece of a
# known pattern is already covered. These unescaped sources are only ever used
# for that literal containment check; they are never compiled again.
PATTERN_LITERALS: tuple[str, ...] = tuple(
    pattern.pattern.replace("\\", "") for pattern, _replacement in _RUNTIME_PATTERNS
)

VIETNAMESE_TEXT: frozenset[str] = frozenset(
    vietnamese for vietnamese, _english in _TEXT.values()
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
    if text in _RUNTIME_EN or text in VIETNAMESE_TEXT:
        return True
    if any(pattern.fullmatch(text) for pattern, _replacement in _RUNTIME_PATTERNS):
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
        if module == "ui/i18n.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstrings = docstring_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or id(node) in docstrings:
                continue
            if isinstance(node.value, str) and is_vietnamese(node.value):
                constants.append((module, node.lineno, node.value))
    return sorted(constants)


class LocalizerTests(unittest.TestCase):
    def test_static_and_runtime_messages_have_vietnamese_and_english(self) -> None:
        vietnamese = Localizer(Language.VIETNAMESE)
        english = Localizer(Language.ENGLISH)

        self.assertEqual(vietnamese.text("nav.library"), "Thư viện")
        self.assertEqual(english.text("nav.library"), "Library")
        self.assertEqual(english.text("player.play"), "Read")
        self.assertEqual(
            english.runtime("Chương 2/3 · Đoạn 4/5"),
            "Chapter 2/3 · Paragraph 4/5",
        )
        self.assertEqual(
            english.runtime("Đang đọc đoạn 2/7"),
            "Reading part 2/7",
        )
        self.assertEqual(
            english.runtime("PDF không có lớp văn bản; bản MVP chưa hỗ trợ OCR."),
            "This PDF has no text layer; OCR is not supported yet.",
        )
        self.assertEqual(
            english.runtime("Mô hình đọc tiếng Việt đã sẵn sàng."),
            "The Vietnamese voice model is ready.",
        )
        self.assertEqual(
            english.runtime("Adam - Nam Bộ"),
            "Adam - Southern Vietnamese",
        )
        self.assertEqual(
            english.runtime("Trúc Ly - Bắc Bộ"),
            "Trúc Ly - Northern Vietnamese",
        )
        self.assertEqual(
            english.runtime("Sẵn sàng tải giọng đọc."),
            "Ready to download voice data.",
        )
        self.assertEqual(
            english.runtime("EPUB chứa đường dẫn không an toàn."),
            "The EPUB contains an unsafe path.",
        )
        self.assertEqual(
            english.runtime("Nguồn EPUB được quản lý đã thay đổi."),
            "The managed EPUB source has changed.",
        )
        self.assertEqual(
            english.runtime("Không thể khóa thư viện cục bộ để nhập sách."),
            "Could not lock the local library for import.",
        )
        # These two are built character-for-character in the controller and
        # translated by exact match, so drift silently ships Vietnamese.
        self.assertEqual(
            english.runtime(
                "Không tìm thấy nội dung đang chọn. Hãy chọn chữ trong Apple "
                "Books rồi nhấn phím tắt đọc."
            ),
            "No selected text was found. Select text in Apple Books, then "
            "press the read shortcut.",
        )
        self.assertEqual(
            english.runtime(
                "Không đăng ký được phím tắt này; macOS hoặc ứng dụng khác "
                "đang dùng nó. Hãy chọn tổ hợp khác."
            ),
            "This shortcut could not be registered; macOS or another app is "
            "already using it. Choose a different combination.",
        )

    def test_read_on_copy_note_claims_no_more_than_the_code_can_do(self) -> None:
        # The Apple Books check is "which app is in front", sampled a few times
        # a second, so a copy made elsewhere and followed by a fast switch can
        # still be read. The note must not promise otherwise in either
        # language.
        for language, forbidden in (
            (Language.VIETNAMESE, ("không bao giờ",)),
            (Language.ENGLISH, ("never", "always", "cannot be read")),
        ):
            note = Localizer(language).text("external.privacy_note_on")
            for claim in forbidden:
                self.assertNotIn(claim, note.lower(), f"{language}: {claim}")
            self.assertIn(
                "macos",
                note.lower(),
                "the note has to say why the check is imperfect",
            )

    def test_language_store_defaults_safely_and_persists_supported_language(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = LanguagePreferenceStore(path)

            self.assertEqual(store.load(), Language.VIETNAMESE)
            self.assertTrue(store.save(Language.ENGLISH))
            self.assertEqual(store.load(), Language.ENGLISH)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"language": "en"},
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

            path.write_text('{"language":"unsupported"}', encoding="utf-8")
            self.assertEqual(store.load(), Language.VIETNAMESE)

    def test_saving_a_language_keeps_the_other_saved_settings(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                '{"selection_shortcut": {"key_code": 38, "modifiers": 4352}}',
                encoding="utf-8",
            )

            self.assertTrue(LanguagePreferenceStore(path).save(Language.ENGLISH))

            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {
                    "language": "en",
                    "selection_shortcut": {"key_code": 38, "modifiers": 4352},
                },
            )


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


if __name__ == "__main__":
    unittest.main()
