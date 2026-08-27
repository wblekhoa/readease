from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from vieneu_reader.domain.segmenter import MAX_PASTED_TEXT_CHARS
from vieneu_reader.ui.paste_view import PasteTextView


class PasteTextViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_read_action_requires_valid_text_within_the_safe_limit(self) -> None:
        view = PasteTextView()
        self.addCleanup(view.close)

        self.assertFalse(view.read_button.isEnabled())
        self.assertEqual(view.counter_label.text(), "0 / 100.000 ký tự")
        self.assertIn("không được lưu vào cache", view.description.text())

        view.text_edit.setPlainText(" \n\t ")
        self.application.processEvents()
        self.assertFalse(view.read_button.isEnabled())

        view.text_edit.setPlainText("Xin chào từ ReadEase.")
        self.application.processEvents()
        self.assertTrue(view.read_button.isEnabled())
        self.assertEqual(view.text(), "Xin chào từ ReadEase.")

        view.text_edit.setPlainText("a" * (MAX_PASTED_TEXT_CHARS + 1))
        self.application.processEvents()
        self.assertFalse(view.read_button.isEnabled())
        self.assertIn("Vượt giới hạn", view.counter_label.text())

    def test_editor_preserves_long_multiline_content(self) -> None:
        view = PasteTextView()
        self.addCleanup(view.close)
        source = "\n\n".join(
            [f"Đoạn {index}: nội dung tiếng Việt." for index in range(80)]
        )

        view.text_edit.setPlainText(source)

        self.assertEqual(view.text(), source)
        self.assertGreater(len(view.text()), 240)


if __name__ == "__main__":
    unittest.main()
