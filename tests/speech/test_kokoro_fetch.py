"""The English model's downloader, against a local HTTP server: streamed to
a temp name, hashed as it lands, reported every megabyte, renamed only when
the hash matches, and gone without a trace when the report raises."""

from __future__ import annotations

import hashlib
import http.server
import os
import tempfile
import threading
import unittest
from pathlib import Path

from vieneu_reader.speech.kokoro import REPORT_EVERY, EnglishModelError, _fetch


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # noqa: D401 - silence
        pass


class FetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.served = tempfile.TemporaryDirectory()
        cls.payload = os.urandom(3 * REPORT_EVERY + 12_345)
        (Path(cls.served.name) / "model.bin").write_bytes(cls.payload)
        handler = lambda *args, **kwargs: _Quiet(*args, directory=cls.served.name, **kwargs)  # noqa: E731
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/model.bin"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.served.cleanup()

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.target = Path(self.folder.name) / "Models" / "kokoro" / "model.bin"

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_a_matching_file_lands_whole_with_progress_along_the_way(self) -> None:
        reports: list[int] = []

        _fetch(self.url, self.target, hashlib.sha256(self.payload).hexdigest(), reports.append)

        self.assertEqual(self.target.read_bytes(), self.payload)
        self.assertEqual(reports[-1], len(self.payload))
        self.assertGreaterEqual(len(reports), 3)
        self.assertEqual(reports, sorted(reports))
        self.assertEqual(list(self.target.parent.glob(".download-*")), [])
        self.assertEqual(oct(self.target.stat().st_mode & 0o777), "0o600")

    def test_a_file_that_does_not_match_never_replaces_the_target(self) -> None:
        with self.assertRaises(EnglishModelError):
            _fetch(self.url, self.target, "0" * 64)

        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.target.parent.glob(".download-*")), [])

    def test_no_pin_means_no_hash_check(self) -> None:
        _fetch(self.url, self.target, None)

        self.assertEqual(self.target.read_bytes(), self.payload)

    def test_a_cancel_raised_from_progress_leaves_nothing_behind(self) -> None:
        class Cancelled(BaseException):
            pass

        def report(landed: int) -> None:
            raise Cancelled()

        with self.assertRaises(Cancelled):
            _fetch(self.url, self.target, None, report)

        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.target.parent.glob(".download-*")), [])

    def test_a_missing_file_is_an_error_not_an_empty_model(self) -> None:
        with self.assertRaises(Exception):
            _fetch(self.url.replace("model.bin", "gone.bin"), self.target, None)

        self.assertFalse(self.target.exists())
