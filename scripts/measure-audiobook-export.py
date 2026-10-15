#!/usr/bin/env python3
"""Measure audiobook export overhead with synthetic audio, not model speed.

Run: PYTHONPATH=src:. uv run --frozen python scripts/measure-audiobook-export.py
Creates 300 chapters / 6,000 paragraphs in a temporary folder; no user library,
model or network is used. The fixture and all output are removed on exit.
"""
from __future__ import annotations

import io
import json
import resource
import sys
import tempfile
import threading
import time
from pathlib import Path

from tests.headless.test_export import ToneEngine
from tests.headless.test_server import BOOK_ID, build_book
from vieneu_reader.headless.server import _Session
from vieneu_reader.storage.repository import LibraryRepository


class Probe(io.StringIO):
    """Collect only timings and the receipt, never all generated audio."""

    def __init__(self):
        super().__init__()
        self.sent = {}
        self.latencies = []
        self.progress = 0
        self.phase = "synthesising"
        self.result = {}

    def write(self, line):
        data = json.loads(line)
        if data.get("event") == "export_progress":
            self.progress += 1
            self.phase = data.get("phase")
        request_id = data.get("id")
        if request_id in self.sent and "ok" in data:
            elapsed = (time.monotonic() - self.sent.pop(request_id)) * 1000
            self.latencies.append((self.phase, elapsed))
        if request_id == 1 and "ok" in data:
            self.result = data
        return len(line)

    def flush(self):
        pass


def main():
    with tempfile.TemporaryDirectory(prefix="readease-performance-") as folder:
        root = Path(folder)
        repository = LibraryRepository(root / "test.sqlite3")
        book = build_book([
            (f"Chương {i + 1}", [
                (f"Đây là đoạn văn số {j + 1} dùng để đo hiệu năng.", "paragraph")
                for j in range(20)
            ]) for i in range(300)
        ])
        source = root / "fixture.epub"
        source.write_bytes(b"fixture")
        repository.add_book(book, source)
        writer = Probe()
        session = _Session(io.StringIO(), writer, ToneEngine(), repository=repository)
        done = threading.Event()

        def probe():
            request_id = 100
            while not done.wait(0.1):
                request_id += 1
                writer.sent[request_id] = time.monotonic()
                session._requests.put(json.dumps({"id": request_id, "method": "library.list"}))

        thread = threading.Thread(target=probe)
        thread.start()
        rss_unit = 1024 ** 2 if sys.platform == "darwin" else 1024
        baseline = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        began = time.monotonic()
        try:
            session._export_book(1, {"book_id": BOOK_ID, "voice_id": "adam", "path": str(root / "long.m4b")})
        finally:
            done.set()
            thread.join()
            repository.close()
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result = writer.result.get("result", {})
        measured = {
            "wall_s": round(time.monotonic() - began, 2),
            "audio_minutes": round(result.get("seconds", 0) / 60, 1),
            "peak_rss_mb": round(peak / rss_unit, 1),
            "peak_growth_mb": round((peak - baseline) / rss_unit, 1),
            "chapters": len(result.get("chapters", [])),
            "progress_events": writer.progress,
            "ok": writer.result.get("ok"),
            "lufs": result.get("lufs"),
        }
        for phase in ("synthesising", "normalising", "encoding"):
            values = sorted(value for at, value in writer.latencies if at == phase)
            measured[phase] = {
                "probes": len(values),
                "p95_ms": round(values[min(len(values) - 1, int(len(values) * .95))], 1) if values else None,
                "max_ms": round(max(values), 1) if values else None,
            }
        print(json.dumps(measured, ensure_ascii=False, indent=2))
        if not writer.result.get("ok"):
            raise RuntimeError(writer.result)


if __name__ == "__main__":
    main()
