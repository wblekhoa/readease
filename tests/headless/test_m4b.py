"""The audiobook writer (RE-PLAY-020): chapters, tags and untouched audio."""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave

from vieneu_reader.headless.m4b import (
    Chapter,
    _boxes,
    _child,
    add_chapters,
    read_chapters,
    write_m4b,
)


def _box(kind: bytes, *parts: bytes) -> bytes:
    body = b"".join(parts)
    return struct.pack(">I4s", 8 + len(body), kind) + body


def _full(kind: bytes, *parts: bytes) -> bytes:
    return _box(kind, b"\x00\x00\x00\x00", *parts)


def _fake_m4a(payload: bytes, chunks: list[int], *, moov_first: bool, co64: bool = False) -> tuple[bytes, list[int]]:
    """A one-track MPEG-4 shell around `payload`, chunk offsets pointing at
    `chunks` (positions inside the payload). Returns the file and the
    absolute offsets it holds."""

    def build(mdat_start: int) -> bytes:
        absolute = [mdat_start + 8 + c for c in chunks]
        table = (_full(b"co64", struct.pack(">I", len(absolute)), struct.pack(f">{len(absolute)}Q", *absolute))
                 if co64 else
                 _full(b"stco", struct.pack(">I", len(absolute)), struct.pack(f">{len(absolute)}I", *absolute)))
        mvhd = _full(b"mvhd", struct.pack(">IIII", 0, 0, 1000, 12000), bytes(76), struct.pack(">I", 2))
        stbl = _box(b"stbl", _full(b"stsd", struct.pack(">I", 0)), table)
        minf = _box(b"minf", _full(b"smhd", bytes(4)), stbl)
        mdia = _box(b"mdia", _full(b"mdhd", bytes(20)), _full(b"hdlr", struct.pack(">I4s12x", 0, b"soun"), b"\x00"), minf)
        trak = _box(b"trak", _full(b"tkhd", bytes(80)), mdia)
        return _box(b"moov", mvhd, trak, _box(b"udta", b"old tags"))

    ftyp = _box(b"ftyp", b"M4A ", bytes(4))
    mdat = _box(b"mdat", payload)
    if moov_first:
        moov = build(0)
        moov = build(len(ftyp) + len(moov))
        data = ftyp + moov + mdat
        start = len(ftyp) + len(moov)
    else:
        start = len(ftyp)
        data = ftyp + mdat + build(start)
    return data, [start + 8 + c for c in chunks]


def _audio_offsets(data: bytes) -> list[int]:
    moov = _child(data, 0, len(data), b"moov")
    for kind, _s, body, end in _boxes(data, moov[1], moov[2]):
        if kind != b"trak":
            continue
        mdia = _child(data, body, end, b"mdia")
        hdlr = _child(data, mdia[1], mdia[2], b"hdlr")
        if data[hdlr[1] + 8:hdlr[1] + 12] != b"soun":
            continue
        minf = _child(data, mdia[1], mdia[2], b"minf")
        stbl = _child(data, minf[1], minf[2], b"stbl")
        for k, _s2, b, _e in _boxes(data, stbl[1], stbl[2]):
            if k in (b"stco", b"co64"):
                n = struct.unpack(">I", data[b + 4:b + 8])[0]
                fmt = "Q" if k == b"co64" else "I"
                width = 8 if k == b"co64" else 4
                return list(struct.unpack(f">{n}{fmt}", data[b + 8:b + 8 + width * n]))
    return []


PAYLOAD = bytes(range(256)) * 8
CHUNKS = [0, 512, 1500]
CHAPTERS = [Chapter("Chương một", 0.0), Chapter("Chương hai: Mùa thu", 4.0), Chapter("Chương ba", 8.0)]


class ChapterBoxTests(unittest.TestCase):
    # RE-PLAY-020
    def test_chapters_round_trip_with_their_titles_and_starts(self):
        for moov_first in (True, False):
            source, _ = _fake_m4a(PAYLOAD, CHUNKS, moov_first=moov_first)
            out = add_chapters(source, CHAPTERS, {"title": "Sách"})
            self.assertEqual(read_chapters(out), CHAPTERS, moov_first)

    def test_every_audio_chunk_still_points_at_the_same_bytes(self):
        for moov_first in (True, False):
            for co64 in (False, True):
                source, before = _fake_m4a(PAYLOAD, CHUNKS, moov_first=moov_first, co64=co64)
                out = add_chapters(source, CHAPTERS, {})
                after = _audio_offsets(out)
                self.assertEqual(len(after), len(before))
                for old, new in zip(before, after):
                    self.assertEqual(out[new:new + 64], source[old:old + 64], (moov_first, co64))

    def test_the_audio_track_lists_the_chapter_track_and_the_file_is_an_audiobook(self):
        source, _ = _fake_m4a(PAYLOAD, CHUNKS, moov_first=True)
        out = add_chapters(source, CHAPTERS, {"title": "Sách", "comment": "AI-generated speech"})
        self.assertEqual(out[8:12], b"M4B ")
        self.assertIn(b"chap", out)
        self.assertIn("AI-generated speech".encode(), out)
        self.assertNotIn(b"old tags", out)  # the encoder's tags are replaced

    def test_a_first_mark_after_zero_moves_to_zero_and_marks_past_the_end_are_dropped(self):
        source, _ = _fake_m4a(PAYLOAD, CHUNKS, moov_first=False)
        out = add_chapters(source, [Chapter("Một", 1.5), Chapter("Hai", 6.0), Chapter("Quá", 99.0)], {})
        self.assertEqual(read_chapters(out), [Chapter("Một", 0.0), Chapter("Hai", 6.0)])

    def test_no_marks_gives_one_chapter_named_after_the_book(self):
        source, _ = _fake_m4a(PAYLOAD, CHUNKS, moov_first=False)
        self.assertEqual(read_chapters(add_chapters(source, [], {"title": "Sách"})), [Chapter("Sách", 0.0)])

    def test_what_is_not_mpeg4_audio_is_refused(self):
        with self.assertRaises(ValueError):
            add_chapters(b"RIFF....WAVEfmt ", CHAPTERS, {})


@unittest.skipUnless(os.path.exists("/usr/bin/afconvert"), "needs macOS's encoder")
class AudiobookFileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.wav = os.path.join(self.folder, "in.wav")
        rate = 48000
        frames = bytearray()
        for tone in (440, 550, 660):
            for i in range(rate * 2):
                frames += struct.pack("<h", int(8000 * math.sin(2 * math.pi * tone * i / rate)))
        with wave.open(self.wav, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(bytes(frames))

    # RE-PLAY-020
    def test_a_real_encode_keeps_the_chapters_and_the_sound(self):
        path = os.path.join(self.folder, "Sách.m4b")
        write_m4b(self.wav, path, [Chapter("Một", 0), Chapter("Hai", 2), Chapter("Ba", 4)], {"title": "Sách"})
        with open(path, "rb") as made:
            self.assertEqual(read_chapters(made.read()), [Chapter("Một", 0.0), Chapter("Hai", 2.0), Chapter("Ba", 4.0)])
        back = os.path.join(self.folder, "back.wav")
        subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@48000", path, back], check=True)
        with wave.open(back) as decoded:
            rate = decoded.getframerate()
            samples = struct.unpack(f"<{decoded.getnframes()}h", decoded.readframes(decoded.getnframes()))
        for chapter, tone in enumerate((440, 550, 660)):
            middle = samples[int((chapter * 2 + 0.5) * rate):int((chapter * 2 + 1.5) * rate)]
            crossings = sum(1 for a, b in zip(middle, middle[1:]) if (a < 0) != (b < 0))
            self.assertAlmostEqual(crossings / 2, tone, delta=5)
        # Only the file asked for is left behind.
        self.assertEqual(sorted(os.listdir(self.folder)), ["Sách.m4b", "back.wav", "in.wav"])

    def test_a_failed_encode_leaves_nothing(self):
        broken = os.path.join(self.folder, "broken.wav")
        with open(broken, "wb") as out:
            out.write(b"not audio")
        path = os.path.join(self.folder, "out.m4b")
        with self.assertRaises(subprocess.CalledProcessError):
            write_m4b(broken, path, [], {})
        self.assertEqual(sorted(os.listdir(self.folder)), ["broken.wav", "in.wav"])


if __name__ == "__main__":
    unittest.main()


class CancelWriterTests(unittest.TestCase):
    def test_cancel_before_encoding_preserves_destination_and_cleans_staging(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "old.m4b"
            out.write_bytes(b"old")
            def cancelled():
                raise InterruptedError("cancelled")
            with self.assertRaises(InterruptedError):
                write_m4b("unused.wav", str(out), [Chapter("One", 0)], {}, checkpoint=cancelled)
            self.assertEqual(out.read_bytes(), b"old")
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["old.m4b"])


    def test_cancel_during_encoding_terminates_the_encoder_and_preserves_destination(self):
        from pathlib import Path
        from unittest.mock import patch
        import sys
        import time
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "old.m4b"
            out.write_bytes(b"old")
            process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
            calls = 0
            def checkpoint():
                nonlocal calls
                calls += 1
                if calls >= 3:
                    raise InterruptedError("cancelled")
            started = time.monotonic()
            with patch("vieneu_reader.headless.m4b.subprocess.Popen", return_value=process):
                with self.assertRaises(InterruptedError):
                    write_m4b("unused.wav", str(out), [Chapter("One", 0)], {}, checkpoint=checkpoint)
            self.assertIsNotNone(process.poll())
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(out.read_bytes(), b"old")
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["old.m4b"])


    def test_a_second_staging_file_failure_cleans_the_first(self):
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "old.m4b"
            out.write_bytes(b"old")
            make = tempfile.mkstemp
            calls = 0
            def failing_second(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("disk full")
                return make(*args, **kwargs)
            with patch("vieneu_reader.headless.m4b.tempfile.mkstemp", side_effect=failing_second):
                with self.assertRaises(OSError):
                    write_m4b("unused.wav", str(out), [Chapter("One", 0)], {})
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["old.m4b"])
