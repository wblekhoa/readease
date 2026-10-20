"""Paste and scan history kept on this Mac (RE-HIST-001…004)."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from vieneu_reader.storage.history import DAY_MS, HistoryStore


class HistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "history.sqlite3"
        self.store = HistoryStore(self.path)
        self.addCleanup(self.store.close)

    # RE-HIST-001
    def test_a_paste_and_a_scan_survive_a_new_store_over_the_same_file(self):
        self.store.add("paste", "Đoạn văn đã dán.", at=1000)
        self.store.add("scan", "Bản dịch.", original="Original text.", target="vi", at=2000)
        self.store.close()
        reopened = HistoryStore(self.path)
        self.addCleanup(reopened.close)
        rows = reopened.list(now=3000, days=0)
        self.assertEqual([(r.kind, r.text, r.original, r.target) for r in rows],
                         [("scan", "Bản dịch.", "Original text.", "vi"), ("paste", "Đoạn văn đã dán.", None, None)])

    # RE-HIST-001
    def test_the_file_is_private_to_this_user(self):
        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(mode & 0o077, 0, oct(mode))

    # RE-HIST-002
    def test_reading_the_same_text_again_moves_it_up_instead_of_adding_a_copy(self):
        first = self.store.add("paste", "Cùng một đoạn.", at=1000)
        self.store.add("paste", "Đoạn khác.", at=2000)
        again = self.store.add("paste", "  Cùng một   đoạn. ", at=3000)
        self.assertEqual(again.id, first.id)
        # Spacing does not make it new; the latest wording is what is kept,
        # line breaks and all.
        self.assertEqual([r.text for r in self.store.list(now=4000, days=0)], ["Cùng một   đoạn.", "Đoạn khác."])
        # The same words pasted and scanned are two different entries.
        self.store.add("scan", "Cùng một đoạn.", at=5000)
        self.assertEqual(len(self.store.list(now=6000, days=0)), 3)

    # RE-HIST-002
    def test_a_translated_scan_whose_original_has_line_breaks_is_one_entry(self):
        self.store.add("scan", "Hello you.", original="Xin chào\nbạn.", target="en", at=1)
        self.store.add("scan", "Hello you.", original="Xin chào\nbạn.", target="en", at=2)
        self.assertEqual(len(self.store.list(now=3, days=0)), 1)

    # RE-HIST-003
    def test_entries_older_than_the_chosen_days_are_deleted_not_just_hidden(self):
        now = 100 * DAY_MS
        self.store.add("paste", "Cũ.", at=now - 31 * DAY_MS)
        self.store.add("paste", "Mới.", at=now - 2 * DAY_MS)
        self.assertEqual([r.text for r in self.store.list(now=now, days=30)], ["Mới."])
        # Gone from the file, so a later "keep forever" does not bring it back.
        self.assertEqual([r.text for r in self.store.list(now=now, days=0)], ["Mới."])

    # RE-HIST-003
    def test_keep_forever_keeps_everything(self):
        self.store.add("paste", "Rất cũ.", at=1)
        self.assertEqual(len(self.store.list(now=1000 * DAY_MS, days=0)), 1)

    # RE-HIST-004
    def test_one_entry_or_everything_can_be_deleted(self):
        keep = self.store.add("paste", "Giữ.", at=1)
        gone = self.store.add("scan", "Xoá.", at=2)
        self.assertTrue(self.store.delete(gone.id))
        self.assertFalse(self.store.delete(gone.id))
        self.assertEqual([r.id for r in self.store.list(now=3, days=0)], [keep.id])
        self.store.add("scan", "Thêm.", at=4)
        self.assertEqual(self.store.clear(kind="scan"), 1)
        self.assertEqual([r.kind for r in self.store.list(now=5, days=0)], ["paste"])
        self.assertEqual(self.store.clear(), 1)
        self.assertEqual(self.store.list(now=6, days=0), [])

    def test_empty_text_and_unknown_kinds_are_refused(self):
        with self.assertRaises(ValueError):
            self.store.add("paste", "   ", at=1)
        with self.assertRaises(ValueError):
            self.store.add("book", "Không phải.", at=1)

    def test_the_list_is_bounded(self):
        for index in range(5):
            self.store.add("paste", f"Đoạn {index}.", at=index)
        self.assertEqual([r.text for r in self.store.list(now=10, days=0, limit=2)], ["Đoạn 4.", "Đoạn 3."])


if __name__ == "__main__":
    unittest.main()
