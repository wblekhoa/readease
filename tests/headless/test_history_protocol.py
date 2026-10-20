"""The engine's history methods and their two settings (RE-HIST-001…004)."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from vieneu_reader.headless.server import serve
from vieneu_reader.storage.history import HistoryStore
from tests.headless.test_export import ToneEngine


class HistoryProtocolTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.settings = root / "settings.json"
        self.history = HistoryStore(root / "history.sqlite3")
        self.addCleanup(self.history.close)

    def run_requests(self, *requests):
        lines = "".join(json.dumps({"id": index + 1, **request}) + "\n" for index, request in enumerate(requests))
        writer = io.StringIO()
        serve(io.StringIO(lines), writer, ToneEngine(), settings_path=self.settings, history=self.history)
        replies = [json.loads(line) for line in writer.getvalue().splitlines()]
        return {reply["id"]: reply for reply in replies if "ok" in reply}

    # RE-HIST-001
    def test_on_by_default_a_paste_and_a_scan_are_kept_and_listed_newest_first(self):
        replies = self.run_requests(
            {"method": "history.add", "params": {"kind": "paste", "text": "Đoạn dán."}},
            {"method": "history.add", "params": {"kind": "scan", "text": "Bản dịch.", "original": "Original.", "target": "vi"}},
            {"method": "history.list", "params": {}},
        )
        self.assertTrue(replies[1]["result"]["saved"])
        listed = replies[3]["result"]
        self.assertTrue(listed["enabled"])
        self.assertEqual(listed["days"], 30)
        self.assertEqual([(e["kind"], e["text"], e["original"]) for e in listed["entries"]],
                         [("scan", "Bản dịch.", "Original."), ("paste", "Đoạn dán.", None)])

    # RE-HIST-001
    def test_switched_off_nothing_new_is_written(self):
        replies = self.run_requests(
            {"method": "config.set", "params": {"key": "history_enabled", "value": False}},
            {"method": "history.add", "params": {"kind": "paste", "text": "Không lưu."}},
            {"method": "history.list", "params": {}},
        )
        self.assertFalse(replies[2]["result"]["saved"])
        self.assertEqual(replies[3]["result"]["entries"], [])
        self.assertFalse(replies[3]["result"]["enabled"])

    # RE-HIST-003
    def test_the_chosen_days_apply_and_an_unknown_value_falls_back_to_thirty(self):
        replies = self.run_requests(
            {"method": "config.set", "params": {"key": "history_days", "value": 90}},
            {"method": "history.list", "params": {}},
            {"method": "config.set", "params": {"key": "history_days", "value": 12}},
            {"method": "history.list", "params": {}},
        )
        self.assertEqual(replies[2]["result"]["days"], 90)
        self.assertEqual(replies[4]["result"]["days"], 30)

    # RE-HIST-004
    def test_one_entry_or_a_whole_kind_can_be_deleted(self):
        replies = self.run_requests(
            {"method": "history.add", "params": {"kind": "paste", "text": "Một."}},
            {"method": "history.add", "params": {"kind": "scan", "text": "Hai."}},
            {"method": "history.add", "params": {"kind": "scan", "text": "Ba."}},
            {"method": "history.clear", "params": {"kind": "scan"}},
            {"method": "history.list", "params": {}},
        )
        self.assertEqual(replies[4]["result"]["deleted"], 2)
        entry = replies[5]["result"]["entries"][0]
        self.assertEqual(entry["text"], "Một.")
        again = self.run_requests({"method": "history.delete", "params": {"id": entry["id"]}},
                                  {"method": "history.list", "params": {}})
        self.assertTrue(again[1]["result"]["deleted"])
        self.assertEqual(again[2]["result"]["entries"], [])

    def test_bad_requests_are_refused_by_name(self):
        replies = self.run_requests(
            {"method": "history.add", "params": {"kind": "book", "text": "Không."}},
            {"method": "history.add", "params": {"kind": "paste", "text": "  "}},
            {"method": "history.delete", "params": {"id": "x"}},
        )
        self.assertFalse(replies[1]["ok"])
        self.assertFalse(replies[2]["ok"])
        self.assertFalse(replies[3]["ok"])


if __name__ == "__main__":
    unittest.main()
