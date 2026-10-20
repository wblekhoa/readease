"""ReadEase's own translator on the wire: status, prepare and remove by name
(RE-PLAY-031). The engine never translates; it hands the host a path."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path

from vieneu_reader.headless.server import serve
from tests.headless.test_server_english import FakeVietnamese


class FakeTranslator:
    def __init__(self, ready: bool = False) -> None:
        self.ready = ready
        self.prepared = 0
        self.removed = 0

    @property
    def is_model_ready(self) -> bool:
        return self.ready

    @property
    def path(self) -> Path:
        return Path("/models/hy-mt2-1.8b-gguf/Hy-MT2-1.8B-Q4_K_M.gguf")

    def installed_size(self) -> int:
        return 1_133_080_448 if self.ready else 0

    def prepare_model(self, progress) -> None:
        for fraction in (0.0, 0.5, 1.0):
            progress(fraction, "…")
        self.prepared += 1
        self.ready = True

    def remove(self) -> bool:
        self.removed += 1
        was, self.ready = self.ready, False
        return was


def run(requests, translator):
    reader = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
    writer = io.StringIO()
    serve(reader, writer, FakeVietnamese(), translator=translator)
    return [json.loads(line) for line in writer.getvalue().splitlines()]


class TranslatorOnTheWireTests(unittest.TestCase):
    # RE-PLAY-031
    def test_status_says_ready_and_the_path_only_once_downloaded(self) -> None:
        absent = run([{"id": 1, "method": "model.status"}], FakeTranslator())[0]["result"]["translator"]
        self.assertEqual((absent["ready"], absent["path"]), (False, None))
        self.assertGreater(absent["download_bytes"], 1_000_000_000)
        present = run([{"id": 1, "method": "model.status"}], FakeTranslator(ready=True))[0]["result"]["translator"]
        self.assertTrue(present["ready"])
        self.assertTrue(present["path"].endswith(".gguf"))

    # RE-PLAY-031
    def test_prepare_and_remove_by_name(self) -> None:
        translator = FakeTranslator()
        replies = run([
            {"id": 7, "method": "model.prepare", "params": {"engine": "translator"}},
            {"id": 8, "method": "model.remove_build", "params": {"engine": "translator"}},
        ], translator)
        self.assertTrue(any(r.get("event") == "model_progress" and r["id"] == 7 for r in replies))
        done = next(r for r in replies if r.get("id") == 7 and "ok" in r)
        self.assertEqual(done["result"], {"ready": True})
        removed = next(r for r in replies if r.get("id") == 8)
        self.assertEqual(removed["result"], {"removed": True})
        self.assertEqual((translator.prepared, translator.removed), (1, 1))

    def test_no_translator_means_no_block_and_a_named_refusal(self) -> None:
        replies = run([{"id": 1, "method": "model.status"},
                       {"id": 2, "method": "model.prepare", "params": {"engine": "translator"}}], None)
        self.assertNotIn("translator", replies[0]["result"])
        self.assertFalse(replies[-1]["ok"])


if __name__ == "__main__":
    unittest.main()
