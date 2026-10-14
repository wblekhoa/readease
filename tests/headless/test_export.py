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
        sink.begin("Câu một.")
        sink.add(np.ones(100, dtype=np.float32).tobytes())
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


if __name__ == "__main__":
    unittest.main()
