from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.ui.i18n import (
    Language,
    LanguagePreferenceStore,
    Localizer,
)


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


if __name__ == "__main__":
    unittest.main()
