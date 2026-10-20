"""Export: a reading written to a WAV with subtitles beside it."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import wave

import numpy as np

from vieneu_reader.domain.models import AudioChunk, Voice
from vieneu_reader.headless.export import (
    Cue,
    ExportSink,
    Said,
    integrated_loudness,
    read_wav_info,
    split_cue,
    srt_text,
)
from vieneu_reader.headless.server import serve
from vieneu_reader.playback.time_stretch import SAMPLE_RATE


class ToneEngine:
    """Half a second of a quiet 440 Hz tone per sentence: audible to the
    K-weighted meter, unlike a constant."""

    engine_version = "tone-1"

    def __init__(self) -> None:
        self.requests: list[str] = []

    def voices(self):
        return (Voice(id="adam", label="Adam - Nam Bộ"),)

    def stream(self, text, voice_id, settings):
        self.requests.append(text)
        t = np.arange(SAMPLE_RATE // 2) / SAMPLE_RATE
        tone = (0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        yield AudioChunk(pcm=tone.tobytes(), sample_rate=SAMPLE_RATE)


def run(requests, engine):
    reader = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
    writer = io.StringIO()
    serve(reader, writer, engine)
    return [json.loads(line) for line in writer.getvalue().splitlines()]


class LoudnessMeterTests(unittest.TestCase):
    # RE-PLAY-012
    def test_full_scale_997_hz_sine_reads_minus_3_01(self):
        # The reference point of BS.1770: a full-scale 997 Hz sine in one
        # channel measures -3.01 LKFS.
        t = np.arange(SAMPLE_RATE * 5) / SAMPLE_RATE
        sine = np.sin(2 * np.pi * 997 * t)
        self.assertAlmostEqual(integrated_loudness(sine, SAMPLE_RATE), -3.01, delta=0.05)
        self.assertAlmostEqual(integrated_loudness(sine * 0.1, SAMPLE_RATE), -23.01, delta=0.05)

    # RE-PLAY-012
    def test_peaky_speech_reaches_the_target_under_the_ceiling(self):
        from vieneu_reader.headless.export import PEAK_CEILING_DBFS, TARGET_LUFS, normalised

        # A voice's crest: peaks ~15 dB over the loudness, as VieNeu measured
        # (15.7 dB, 14/10).
        rng = np.random.default_rng(7)
        t = np.arange(int(SAMPLE_RATE * 0.25)) / SAMPLE_RATE
        parts = []
        for index in range(30):
            burst = 0.02 * np.sin(2 * np.pi * (150 + 15 * index) * t) * np.hanning(t.size)
            burst[rng.integers(0, t.size, 3)] += 0.02
            parts += [burst, np.zeros(SAMPLE_RATE // 10)]
        quiet = np.concatenate(parts).astype(np.float32)
        loud, loudness = normalised(quiet, SAMPLE_RATE)
        self.assertAlmostEqual(loudness, TARGET_LUFS, delta=0.2)
        self.assertLessEqual(20 * np.log10(np.abs(loud).max()), PEAK_CEILING_DBFS + 1e-3)

    # RE-PLAY-012
    def test_the_limiter_never_takes_more_than_its_share(self):
        from vieneu_reader.headless.export import MAX_LIMIT_DB, PEAK_CEILING_DBFS, normalised

        # Spikes 26 dB over a quiet body: reaching the target would flatten
        # the voice, so the file is left quieter instead.
        body = 0.005 * np.sin(2 * np.pi * 200 * np.arange(SAMPLE_RATE * 3) / SAMPLE_RATE)
        body[::4800] = 0.1
        out, _ = normalised(body.astype(np.float32), SAMPLE_RATE)
        lifted_db = 20 * np.log10(np.abs(out).max() / 0.1)
        self.assertLessEqual(lifted_db, PEAK_CEILING_DBFS + MAX_LIMIT_DB - 20 * np.log10(0.1) + 0.01)

    # RE-PLAY-012
    def test_the_limiter_holds_after_a_peak_and_starts_only_just_before_it(self):
        from vieneu_reader.headless.export import _held_gain

        peaks = np.full(40, 0.1)
        peaks[20] = 2.0  # one block a ceiling of 1.0 must pull down by half
        held = _held_gain(peaks, 1.0)
        self.assertAlmostEqual(held[20], 0.5)
        self.assertAlmostEqual(held[19], 0.5)      # one block of look-ahead
        self.assertAlmostEqual(held[26], 0.5)      # still held 30 ms after
        self.assertAlmostEqual(held[32], 0.5)      # and at 60 ms
        self.assertEqual(held[33], 1.0)            # then let go
        self.assertEqual(held[14], 1.0)            # 30 ms before: untouched

    def test_silence_has_no_loudness(self):
        self.assertEqual(integrated_loudness(np.zeros(SAMPLE_RATE), SAMPLE_RATE), float("-inf"))


class CueTests(unittest.TestCase):
    # RE-PLAY-013
    def test_long_sentence_splits_into_whole_word_cues_covering_the_span(self):
        text = "Một câu rất dài " * 12
        pieces = split_cue(Cue(0, 48000, text.strip()), limit=40)
        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(len(p.text) <= 40 for p in pieces))
        self.assertEqual(pieces[0].start, 0)
        self.assertEqual(pieces[-1].end, 48000)
        for before, after in zip(pieces, pieces[1:]):
            self.assertEqual(before.end, after.start)
        self.assertEqual(" ".join(p.text for p in pieces), text.strip())

    # RE-PLAY-013
    def test_srt_numbers_and_times_cues(self):
        srt = srt_text([Cue(0, 24000, "Xin chào."), Cue(48000, 96000, "Tạm biệt.")], SAMPLE_RATE)
        self.assertIn("1\n00:00:00,000 --> 00:00:00,500\nXin chào.\n", srt)
        self.assertIn("2\n00:00:01,000 --> 00:00:02,000\nTạm biệt.\n", srt)

    # RE-PLAY-013
    def test_sink_cue_covers_voice_not_the_rest_after_it(self):
        sink = ExportSink(SAMPLE_RATE)
        self.addCleanup(sink.close)
        sink.begin("Câu một.")
        sink.open_sentence(Said("Câu một.", "Câu một.", 1.0, 1.0))
        sink.add(np.ones(100, dtype=np.float32).tobytes())
        sink.close_sentence()
        sink.end()
        sink.add(np.zeros(50, dtype=np.float32).tobytes())
        self.assertEqual([(c.start, c.end) for c in sink.cues], [(0, 100)])


class ExportProtocolTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "giong-doc.wav")

    def export(self, text, **extra):
        params = {"text": text, "voice_id": "adam", "path": self.path,
                  "voice_label": "Adam", "software": "ReadEase 0.1.22"}
        params.update(extra)
        return run([{"id": 1, "method": "export.text", "params": params}], ToneEngine())

    # RE-PLAY-010 RE-PLAY-011 RE-PLAY-013
    def test_export_writes_a_marked_wav_and_timed_subtitles(self):
        replies = self.export("**Xin chào.** Đây là bản đọc thử. Hết.")
        reply = next(r for r in replies if r.get("id") == 1 and "ok" in r)
        self.assertTrue(reply["ok"], reply)
        result = reply["result"]
        self.assertFalse(result["stopped"])
        self.assertEqual(result["path"], self.path)
        # Nothing went down the pipe as audio: a file is not the speakers.
        self.assertFalse([r for r in replies if r.get("event") in ("chunk", "position")])
        progress = [r for r in replies if r.get("event") == "export_progress"]
        self.assertEqual(progress[-1]["done"], progress[-1]["total"])

        with wave.open(self.path) as handle:
            self.assertEqual(handle.getframerate(), SAMPLE_RATE)
            self.assertEqual(handle.getsampwidth(), 2)
            self.assertEqual(handle.getnchannels(), 1)
            pcm = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
        samples = pcm.astype(np.float64) / 32767
        self.assertAlmostEqual(integrated_loudness(samples, SAMPLE_RATE), -14.0, delta=0.3)
        self.assertAlmostEqual(result["lufs"], -14.0, delta=0.1)

        tags = read_wav_info(self.path)
        self.assertIn("AI-generated speech", tags["ICMT"])
        self.assertIn("Adam", tags["ICMT"])
        self.assertEqual(tags["ISFT"], "ReadEase 0.1.22")
        self.assertIn("AI-generated", tags["IKEY"])

        with open(result["subtitles"], encoding="utf-8") as handle:
            srt = handle.read()
        # The written words, Markdown read as meant: no asterisks on screen.
        self.assertIn("Xin chào.", srt)
        self.assertNotIn("**", srt)
        self.assertIn("Đây là bản đọc thử.", srt)
        self.assertEqual(result["cues"], 3)

    # RE-PLAY-014
    def test_rejects_a_path_that_is_not_an_absolute_wav(self):
        replies = self.export("Xin chào.", path="relative.wav")
        self.assertFalse(replies[-1]["ok"])
        replies = self.export("Xin chào.", path=os.path.join(self.folder, "a.mp3"))
        self.assertFalse(replies[-1]["ok"])
        self.assertFalse(os.path.exists(os.path.join(self.folder, "a.mp3")))

    # RE-PLAY-014
    def test_rejects_a_rate_outside_the_reading_range(self):
        replies = self.export("Xin chào.", rate=3.0)
        self.assertFalse(replies[-1]["ok"])
        self.assertFalse(os.path.exists(self.path))

    # RE-PLAY-014
    def test_a_stop_before_the_export_starts_writes_nothing(self):
        # A stop covers what was queued before it: an export waiting behind a
        # reading is dropped, answered as stopped, and leaves no file.
        engine = ToneEngine()
        replies = run([
            {"id": 1, "method": "read", "params": {"text": "Một. Hai. Ba.", "voice_id": "adam"}},
            {"id": 2, "method": "export.text", "params": {
                "text": "Xin chào.", "voice_id": "adam", "path": self.path}},
            {"id": 3, "method": "stop"},
        ], engine)
        answer = next(r for r in replies if r.get("id") == 2 and "ok" in r)
        self.assertTrue(answer["result"]["stopped"])
        self.assertFalse(os.path.exists(self.path))


@unittest.skipUnless(os.path.exists("/usr/bin/afconvert"), "needs macOS's encoder")
class BookExportTests(unittest.TestCase):
    """A book as an audiobook: one mark per chapter (RE-PLAY-020)."""

    def setUp(self):
        from pathlib import Path
        from tests.headless.test_server import build_book
        from vieneu_reader.storage.repository import LibraryRepository

        self.folder = tempfile.mkdtemp()
        root = Path(self.folder)
        self.repository = LibraryRepository(root / "reader.sqlite3")
        self.addCleanup(self.repository.close)
        book = build_book([
            ("Mở đầu", [("Câu thứ nhất.", "paragraph")]),
            ("Chương hai", [("Câu thứ hai.", "paragraph"), ("Câu thứ ba.", "paragraph")]),
            ("Chương ba", [("Câu cuối.", "paragraph")]),
        ])
        source = root / "book.epub"
        source.write_bytes(b"fixture")
        self.repository.add_book(book, source)
        self.out = os.path.join(self.folder, "Sách.m4b")

    def export(self, engine, **extra):
        from tests.headless.test_server import BOOK_ID

        params = {"book_id": BOOK_ID, "voice_id": "adam", "path": self.out,
                  "voice_label": "Adam", "software": "ReadEase 0.1.22"}
        params.update(extra)
        reader = io.StringIO(json.dumps({"id": 1, "method": "export.book", "params": params}) + "\n")
        writer = io.StringIO()
        serve(reader, writer, engine, repository=self.repository)
        replies = [json.loads(line) for line in writer.getvalue().splitlines()]
        return next(r for r in replies if r.get("id") == 1 and "ok" in r)

    # RE-PLAY-020
    def test_the_whole_book_becomes_one_file_with_a_mark_per_chapter(self):
        from vieneu_reader.headless.m4b import read_chapters

        engine = ToneEngine()
        reply = self.export(engine)
        self.assertTrue(reply["ok"], reply)
        result = reply["result"]
        titles = [c["title"] for c in result["chapters"]]
        self.assertEqual(titles, ["Mở đầu", "Chương hai", "Chương ba"])
        starts = [c["start"] for c in result["chapters"]]
        self.assertEqual(starts[0], 0.0)
        self.assertEqual(starts, sorted(starts))
        self.assertLess(starts[-1], result["seconds"])
        with open(self.out, "rb") as made:
            data = made.read()
        written = read_chapters(data)
        self.assertEqual([c.title for c in written], titles)
        for mine, theirs in zip(written, starts):
            self.assertAlmostEqual(mine.start, theirs, delta=0.01)
        self.assertIn(b"AI-generated speech", data)
        # Nothing but the asked-for file is left beside it.
        audio = [name for name in os.listdir(self.folder) if name.rsplit(".", 1)[-1] in ("m4b", "m4a", "wav")]
        self.assertEqual(audio, ["Sách.m4b"])

    def test_a_range_of_chapters_reads_only_those(self):
        engine = ToneEngine()
        reply = self.export(engine, from_chapter=1, chapters=1)
        self.assertTrue(reply["ok"], reply)
        self.assertEqual([c["title"] for c in reply["result"]["chapters"]], ["Chương hai"])
        self.assertTrue(all("Câu thứ" in said for said in engine.requests if said.startswith("Câu")))
        self.assertNotIn("Câu cuối.", engine.requests)

    def test_choosing_the_next_voice_during_export_does_not_load_another_model(self):
        from pathlib import Path
        from unittest.mock import patch
        from vieneu_reader.headless.server import _Session
        from tests.headless.test_server import BOOK_ID
        session = None
        class ChoosingVoice(ToneEngine):
            def stream(inner, text, voice_id, settings):
                session._requests.put(json.dumps({"id": 19, "method": "config.set", "params": {"key": "voice", "value": "kokoro:af_heart"}}))
                yield from super().stream(text, voice_id, settings)
        session = _Session(io.StringIO(), io.StringIO(), ChoosingVoice(), repository=self.repository,
                           settings_path=Path(self.folder) / "settings.json")
        with patch.object(session, "_warm_later") as warm:
            session._export_book(1, {"book_id": BOOK_ID, "voice_id": "adam", "path": self.out})
            self.assertFalse(warm.called, "choosing the next voice loaded another model during export")
            session._config_set(20, {"key": "voice", "value": "adam"})
            warm.assert_called_once()

    def test_an_export_keeps_chapter_chimes_but_never_moves_listening_progress(self):
        from unittest.mock import patch
        from tests.headless.test_server import BOOK_ID
        with patch("vieneu_reader.headless.server.load_chime", return_value=np.zeros(4800, dtype=np.float32)) as chime:
            reply = self.export(ToneEngine())
        self.assertTrue(reply["ok"], reply)
        self.assertTrue(chime.called, "book export lost the chapter sound")
        self.assertIsNone(self.repository.load_progress(BOOK_ID))

    def test_a_disk_error_during_finalisation_returns_instead_of_waiting_forever(self):
        from unittest.mock import patch
        with patch("vieneu_reader.headless.server.tempfile.mkstemp", side_effect=OSError("disk full")):
            reply = self.export(ToneEngine())
        self.assertFalse(reply["ok"], reply)
        self.assertIn("disk full", reply["error"])
        self.assertFalse(os.path.exists(self.out))

    # RE-PLAY-021
    def test_library_responds_during_finalisation_and_cancel_preserves_existing_file(self):
        from unittest.mock import patch
        from vieneu_reader.headless.server import _Session
        from tests.headless.test_server import BOOK_ID
        import threading
        writer = io.StringIO()
        session = _Session(io.StringIO(), writer, ToneEngine(), repository=self.repository)
        checked = threading.Event()
        def slow_write(*args, **kwargs):
            session._requests.put(json.dumps({"id": 9, "method": "library.list"}))
            import time
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                if '"id": 9' in writer.getvalue():
                    checked.set()
                    session._requests.put(json.dumps({"id": 10, "method": "stop"}))
                    while time.monotonic() < deadline and '"id": 10' not in writer.getvalue():
                        time.sleep(0.01)
                    break
                time.sleep(0.01)
            # The finaliser must observe the cancellation before publishing.
            kwargs.get("checkpoint", lambda: None)()
            return -14.0
        from pathlib import Path
        Path(self.out).write_bytes(b"previous audiobook")
        with patch("vieneu_reader.headless.server.write_wav", side_effect=slow_write):
            session._export_book(1, {"book_id": BOOK_ID, "voice_id": "adam", "path": self.out})
        self.assertTrue(checked.is_set(), "library request waited for finalisation")
        reply = [json.loads(line) for line in writer.getvalue().splitlines() if '"ok"' in line and '"id": 1,' in line][-1]
        self.assertTrue(reply["result"]["stopped"], reply)
        self.assertEqual(Path(self.out).read_bytes(), b"previous audiobook")

    def test_refuses_a_path_that_is_not_an_absolute_m4b(self):
        reply = self.export(ToneEngine(), path="relative.m4b")
        self.assertFalse(reply["ok"])
        reply = self.export(ToneEngine(), path=os.path.join(self.folder, "x.wav"))
        self.assertFalse(reply["ok"])
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()


class PronunciationReadingTests(unittest.TestCase):
    """The dictionary reaches what is SAID and priced, never what is shown."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.settings = os.path.join(self.folder, "settings.json")
        with open(self.settings, "w", encoding="utf-8") as handle:
            json.dump({"pronunciations": [{"written": "ReadEase", "spoken": "rít ít"}]}, handle)

    def serve(self, requests, engine, **kwargs):
        from pathlib import Path

        reader = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
        writer = io.StringIO()
        serve(reader, writer, engine, settings_path=Path(self.settings), **kwargs)
        return [json.loads(line) for line in writer.getvalue().splitlines()]

    # RE-PLAY-015
    def test_pasted_text_is_said_and_priced_as_the_reader_wrote_it_should_be(self):
        engine = ToneEngine()
        replies = self.serve([
            {"id": 1, "method": "estimate", "params": {"text": "Mở ReadEase.", "voice_id": "adam"}},
            {"id": 2, "method": "read", "params": {"text": "Mở ReadEase.", "voice_id": "adam"}},
        ], engine)
        self.assertEqual(engine.requests, ["Mở rít ít."])
        estimate = next(r for r in replies if r.get("id") == 1)
        self.assertEqual(estimate["result"]["chars"], len("Mở rít ít."))

    # RE-PLAY-015
    def test_an_export_says_it_and_its_subtitles_keep_the_written_word(self):
        engine = ToneEngine()
        path = os.path.join(self.folder, "a.wav")
        replies = self.serve([{"id": 1, "method": "export.text", "params": {
            "text": "Mở ReadEase.", "voice_id": "adam", "path": path}}], engine)
        self.assertTrue(replies[-1]["ok"], replies[-1])
        self.assertEqual(engine.requests, ["Mở rít ít."])
        with open(path[:-4] + ".srt", encoding="utf-8") as handle:
            self.assertIn("Mở ReadEase.", handle.read())

    # RE-PLAY-015
    def test_a_book_is_said_with_it_too(self):
        from pathlib import Path
        from tests.headless.test_server import BOOK_ID, build_book
        from vieneu_reader.storage.repository import LibraryRepository

        root = Path(self.folder)
        repository = LibraryRepository(root / "reader.sqlite3")
        self.addCleanup(repository.close)
        book = build_book([("Một", [("Đoạn về ReadEase.", "paragraph")])])
        source = root / "book.epub"
        source.write_bytes(b"fixture")
        repository.add_book(book, source)
        engine = ToneEngine()
        replies = self.serve([{"id": 1, "method": "read.book", "params": {
            "book_id": BOOK_ID, "voice_id": "adam", "rate": 1.0}}], engine, repository=repository)
        self.assertTrue(replies[-1]["ok"], replies[-1])
        self.assertIn("Đoạn về rít ít.", engine.requests)


class GrowingEngine(ToneEngine):
    """Each call a different take: the n-th is n quarter-seconds long, so a
    new take is audibly - and measurably - not the old one."""

    def stream(self, text, voice_id, settings):
        self.requests.append(text)
        length = SAMPLE_RATE // 4 * len(self.requests)
        t = np.arange(length) / SAMPLE_RATE
        yield AudioChunk(pcm=(0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float32).tobytes(),
                         sample_rate=SAMPLE_RATE)


def srt_spans(path):
    import re
    spans = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", line)
            if match:
                h, m, s, ms, h2, m2, s2, ms2 = map(int, match.groups())
                spans.append((((h * 60 + m) * 60 + s) * 1000 + ms, ((h2 * 60 + m2) * 60 + s2) * 1000 + ms2))
    return spans


class RetakeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "takes.wav")

    def run_review(self, engine, steps, rate=1.0):
        """Export, then `steps(token)` in the same engine."""
        import threading
        from queue import Queue

        lines: Queue = Queue()
        reader_r, reader_w = os.pipe()
        inbox = os.fdopen(reader_r, "r")
        outbox = os.fdopen(reader_w, "w")

        class Echo(io.StringIO):
            def write(self, text):
                for line in text.splitlines():
                    if line.strip():
                        lines.put(json.loads(line))
                return len(text)

        echo = Echo()
        thread = threading.Thread(target=serve, args=(inbox, echo, engine))
        thread.start()

        def ask(request):
            outbox.write(json.dumps(request) + "\n")
            outbox.flush()
            seen = []
            while True:
                message = lines.get(timeout=20)
                seen.append(message)
                if message.get("id") == request["id"] and "ok" in message:
                    return message, seen

        try:
            reply, _ = ask({"id": 1, "method": "export.text", "params": {
                "text": "Một. Hai. Ba.", "voice_id": "adam", "path": self.path, "rate": rate}})
            self.assertTrue(reply["ok"], reply)
            return reply["result"], steps(reply["result"]["session"], ask)
        finally:
            outbox.close()
            thread.join(timeout=20)
            inbox.close()

    # RE-PLAY-016
    def test_a_new_take_replaces_one_sentence_and_moves_only_what_follows(self):
        engine = GrowingEngine()

        def steps(token, ask):
            before = srt_spans(self.path[:-4] + ".srt")
            retake, _ = ask({"id": 2, "method": "export.retake", "params": {"session": token, "index": 1}})
            saved, _ = ask({"id": 3, "method": "export.save", "params": {"session": token}})
            return before, retake, saved, srt_spans(self.path[:-4] + ".srt")

        result, (before, retake, saved, after) = self.run_review(engine, steps)
        self.assertTrue(result["retake"])
        self.assertEqual([s["text"] for s in result["sentences"]], ["Một.", "Hai.", "Ba."])
        self.assertTrue(retake["ok"], retake)
        self.assertEqual(engine.requests[-1], "Hai.")
        self.assertTrue(saved["ok"], saved)
        # The answer names the review it wrote, as the export's did: the
        # shell clears its "waiting to be written" by it.
        self.assertEqual(saved["result"]["session"], result["session"])
        # Sentence 0 untouched; sentence 1 longer by the new take; 2 moved by
        # exactly that much.
        self.assertEqual(after[0], before[0])
        grown = (after[1][1] - after[1][0]) - (before[1][1] - before[1][0])
        # Takes are 0.25 s x call number: "Hai" was call 2 (0.5 s), its new
        # take is call 4 (1.0 s).
        self.assertAlmostEqual(grown, 1000 - 500, delta=2)
        self.assertAlmostEqual(after[2][0] - before[2][0], grown, delta=2)
        self.assertAlmostEqual(after[2][1] - after[2][0], before[2][1] - before[2][0], delta=2)

    # RE-PLAY-016
    def test_at_a_faster_speed_a_take_still_changes_only_its_own_cue(self):
        engine = GrowingEngine()

        def steps(token, ask):
            before = srt_spans(self.path[:-4] + ".srt")
            ask({"id": 2, "method": "export.retake", "params": {"session": token, "index": 1}})
            ask({"id": 3, "method": "export.save", "params": {"session": token}})
            return before, srt_spans(self.path[:-4] + ".srt")

        _, (before, after) = self.run_review(engine, steps, rate=1.5)
        self.assertEqual(after[0], before[0])
        shift = after[2][0] - before[2][0]
        self.assertGreater(shift, 0)
        self.assertAlmostEqual(after[2][1] - after[2][0], before[2][1] - before[2][0], delta=2)

    # RE-PLAY-016
    def test_play_streams_the_take_in_the_file_not_a_new_one(self):
        engine = GrowingEngine()

        def steps(token, ask):
            calls = len(engine.requests)
            reply, seen = ask({"id": 2, "method": "export.play", "params": {"session": token, "index": 2}})
            pcm = b"".join(__import__("base64").b64decode(m["pcm"]) for m in seen if m.get("event") == "chunk")
            return calls, reply, np.frombuffer(pcm, dtype=np.float32)

        _, (calls, reply, played) = self.run_review(engine, steps)
        self.assertTrue(reply["ok"], reply)
        self.assertEqual(len(engine.requests), calls)  # nothing synthesised
        self.assertEqual(played.size, SAMPLE_RATE // 4 * 3)  # the third take

    # RE-PLAY-016
    def test_a_closed_or_foreign_session_is_refused(self):
        def steps(token, ask):
            wrong, _ = ask({"id": 2, "method": "export.retake", "params": {"session": "nope", "index": 0}})
            ask({"id": 3, "method": "export.close", "params": {}})
            closed, _ = ask({"id": 4, "method": "export.play", "params": {"session": token, "index": 0}})
            return wrong, closed

        _, (wrong, closed) = self.run_review(GrowingEngine(), steps)
        self.assertFalse(wrong["ok"])
        self.assertIn("export_ended", wrong["error"])
        self.assertFalse(closed["ok"])
