"""The headless engine server: what a Tauri (or any) shell will talk to.

These tests drive the protocol with a fake engine - no Qt, no model - because
the server's job is faithful plumbing: sentences in, PCM frames and pauses out,
and a stop that actually stops.
"""

from __future__ import annotations

import base64
import io
import json
import os
import threading
import time
import unittest

import numpy as np

from vieneu_reader.domain.models import AudioChunk, Voice, stable_id

# The repository refuses invented identities: the hash must be real hex and
# the id must be derived from it, exactly as the importers derive it.
BOOK_HASH = "a" * 64
BOOK_ID = stable_id(BOOK_HASH, "epub")


def build_book(chapter_specs: list[tuple[str, list[tuple[str, str]]]]):
    """A BookDocument with the derived identities the repository enforces.

    Each spec is (chapter_title, [(text, kind), ...]); ids come from
    stable_id exactly as the importers derive them.
    """
    from vieneu_reader.domain.models import BookDocument, Chapter, Segment

    chapters = []
    for chapter_index, (title, segment_specs) in enumerate(chapter_specs):
        chapter_id = stable_id(BOOK_ID, "chapter", str(chapter_index))
        segments = tuple(
            Segment(
                id=stable_id(chapter_id, "segment", str(segment_index)),
                chapter_id=chapter_id,
                ordinal=segment_index,
                text=text,
                kind=kind,
            )
            for segment_index, (text, kind) in enumerate(segment_specs)
        )
        chapters.append(Chapter(
            id=chapter_id, title=title, ordinal=chapter_index,
            segments=segments,
        ))
    return BookDocument(
        id=BOOK_ID, title="Sách thử", source_format="epub",
        source_hash=BOOK_HASH, chapters=tuple(chapters),
    )
from vieneu_reader.domain.prosody import SENTENCE_PAUSE_MS
from vieneu_reader.headless.server import PROTOCOL_VERSION, serve
from vieneu_reader.playback.time_stretch import SAMPLE_RATE


def _chunk(samples: np.ndarray) -> AudioChunk:
    return AudioChunk(pcm=samples.astype(np.float32).tobytes(), sample_rate=SAMPLE_RATE)


def _first_audio(replies) -> dict:
    """The first CHUNK of a reading, past the position that announces it.

    A plain read used to open with audio. It now says where it is first -
    every utterance is addressable, so that a reading can be resumed in
    another voice - and these tests are about what the audio does, not about
    that announcement.
    """
    while True:
        message = json.loads(replies.readline())
        if message.get("event") != "position":
            return message


class FakeEngine:
    engine_version = "fake-1"

    def __init__(self, chunks_per_sentence: int = 2, chunk_delay: float = 0.0):
        self.chunks_per_sentence = chunks_per_sentence
        self.chunk_delay = chunk_delay
        self.requests: list[tuple[str, str]] = []

    def voices(self) -> tuple[Voice, ...]:
        return (Voice(id="adam", label="Adam - Nam Bộ"),)

    def stream(self, text: str, voice_id: str, settings):
        self.requests.append((text, voice_id))
        for _ in range(self.chunks_per_sentence):
            if self.chunk_delay:
                time.sleep(self.chunk_delay)
            yield _chunk(np.full(480, 0.25, dtype=np.float32))


def run_server(requests: list[dict], engine, repository=None, service=None,
               settings_path=None, notes_deps=None) -> list[dict]:
    reader = io.StringIO("".join(json.dumps(request) + "\n" for request in requests))
    writer = io.StringIO()
    serve(reader, writer, engine, repository=repository, service=service,
          settings_path=settings_path, notes_deps=notes_deps)
    return [json.loads(line) for line in writer.getvalue().splitlines()]


class ProtocolTests(unittest.TestCase):
    def test_ping_names_the_contract_a_shell_depends_on(self) -> None:
        replies = run_server([{"id": 1, "method": "ping"}], FakeEngine())

        self.assertEqual(len(replies), 1)
        reply = replies[0]
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["result"]["protocol"], PROTOCOL_VERSION)
        self.assertEqual(reply["result"]["sample_rate"], SAMPLE_RATE)
        self.assertEqual(reply["result"]["engine"], "fake-1")

    def test_voices_come_back_with_ids_and_labels(self) -> None:
        replies = run_server([{"id": 2, "method": "voices"}], FakeEngine())

        self.assertEqual(
            replies[0]["result"]["voices"],
            [{"id": "adam", "label": "Adam - Nam Bộ"}],
        )

    def test_read_streams_voice_frames_with_a_rest_between_sentences(self) -> None:
        engine = FakeEngine(chunks_per_sentence=2)
        replies = run_server(
            [{
                "id": 3,
                "method": "read",
                "params": {"text": "Câu một. Câu hai.", "voice_id": "adam"},
            }],
            engine,
        )

        events = [reply for reply in replies if reply.get("event") == "chunk"]
        done = replies[-1]
        # Two sentences of two frames each, plus one rest between them.
        self.assertEqual(len(events), 5)
        self.assertEqual([event["from_voice"] for event in events],
                         [True, True, False, True, True])
        self.assertTrue(done["ok"])
        self.assertEqual(done["result"]["voiced_frames"], 4)
        self.assertFalse(done["result"]["stopped"])
        # The engine was asked sentence by sentence, so prosody stays honest.
        self.assertEqual([text for text, _ in engine.requests],
                         ["Câu một.", "Câu hai."])
        # The rest is real silence of the canonical length.
        rest = events[2]
        pcm = np.frombuffer(base64.b64decode(rest["pcm"]), dtype=np.float32)
        self.assertEqual(len(pcm), SAMPLE_RATE * SENTENCE_PAUSE_MS // 1000)
        self.assertEqual(float(np.abs(pcm).max()), 0.0)

    def test_a_faster_rate_shortens_the_rest_exactly(self) -> None:
        replies = run_server(
            [{
                "id": 4,
                "method": "read",
                "params": {"text": "Câu một. Câu hai.", "voice_id": "adam",
                            "rate": 2.0},
            }],
            FakeEngine(chunks_per_sentence=1),
        )

        rests = [reply for reply in replies
                 if reply.get("event") == "chunk" and not reply["from_voice"]]
        pcm = np.frombuffer(base64.b64decode(rests[0]["pcm"]), dtype=np.float32)
        self.assertEqual(len(pcm), SAMPLE_RATE * SENTENCE_PAUSE_MS // 1000 // 2)

    def test_unknown_method_answers_instead_of_dying(self) -> None:
        replies = run_server(
            [{"id": 9, "method": "dance"}, {"id": 10, "method": "ping"}],
            FakeEngine(),
        )

        self.assertFalse(replies[0]["ok"])
        self.assertIn("dance", replies[0]["error"])
        # The server survived to answer the next request.
        self.assertTrue(replies[1]["ok"])

    def test_read_speaks_the_speakable_form_not_the_raw_text(self) -> None:
        """The Qt paste path lowercases shouted runs before synthesis, because
        ALL CAPS runs 13-18% longer and less stably. The pipe must read the
        same book aloud the same way."""
        from vieneu_reader.domain.prosody import speakable_text

        raw = "THÔNG BÁO KHẨN CẤP toàn hệ thống."
        engine = FakeEngine(chunks_per_sentence=1)
        run_server(
            [{"id": 7, "method": "read",
              "params": {"text": raw, "voice_id": "adam"}}],
            engine,
        )

        expected = speakable_text(raw)
        self.assertNotEqual(expected, raw, "fixture no longer exercises unshout")
        self.assertEqual(engine.requests[0][0], expected)

    def test_read_book_walks_positions_pauses_and_progress(self) -> None:
        from vieneu_reader.domain.prosody import pause_after_ms
        from vieneu_reader.storage.repository import LibraryRepository
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([
                ("Một", [("Đoạn một của chương đầu.", "paragraph"),
                          ("Đoạn hai của chương đầu.", "paragraph")]),
                ("Hai", [("Đoạn mở chương sau.", "heading")]),
            ])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)
            flat = [segment for chapter in book.chapters
                    for segment in chapter.segments]

            engine = FakeEngine(chunks_per_sentence=1)
            replies = run_server(
                [{"id": 8, "method": "read.book",
                  "params": {"book_id": BOOK_ID, "voice_id": "adam",
                              "rate": 1.0}}],
                engine, repository=repository,
            )

            positions = [reply["segment_id"] for reply in replies
                         if reply.get("event") == "position"]
            self.assertEqual(positions, [segment.id for segment in flat])

            done = replies[-1]
            self.assertTrue(done["ok"])
            self.assertFalse(done["result"]["stopped"])

            # The rest before the next chapter's heading must be the prosody
            # table's own answer, not a hardcoded number.
            rests = [reply for reply in replies
                     if reply.get("event") == "chunk"
                     and not reply["from_voice"]]
            expected_ms = pause_after_ms(flat[1], flat[2])
            longest = max(
                len(base64.b64decode(rest["pcm"])) // 4 for rest in rests
            )
            self.assertEqual(longest, SAMPLE_RATE * expected_ms // 1000)

            progress = repository.load_progress(BOOK_ID)
            self.assertIsNotNone(progress)
            self.assertEqual(progress.segment_id, flat[-1].id)
            self.assertEqual(progress.voice_id, "adam")

    def test_read_book_without_a_voice_writes_no_progress(self) -> None:
        """Progress is saved at every position before the voice speaks, so a
        request the voice would reject must be refused up front. On 02/09 a
        probe with no voice_id left a row with an empty voice - and the
        library loader, which requires one, then failed library.list for
        every book."""
        from vieneu_reader.storage.repository import LibraryRepository
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([("Một", [("Đoạn một.", "paragraph")])])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)

            engine = FakeEngine(chunks_per_sentence=1)
            replies = run_server(
                [{"id": 12, "method": "read.book", "params": {"book_id": book.id}},
                 {"id": 13, "method": "library.list"}],
                engine, repository=repository,
            )

            self.assertFalse(replies[0]["ok"])
            self.assertIn("voice", replies[0]["error"])
            self.assertEqual(engine.requests, [])
            self.assertIsNone(repository.load_progress(book.id))
            # The library is still usable afterwards.
            self.assertTrue(replies[1]["ok"])

    def test_read_book_with_an_impossible_rate_writes_no_progress(self) -> None:
        """The loader's other refusal: a stored rate outside 0.5-2.0."""
        from vieneu_reader.storage.repository import LibraryRepository
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([("Một", [("Đoạn một.", "paragraph")])])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)

            engine = FakeEngine(chunks_per_sentence=1)
            replies = run_server(
                [{"id": 14, "method": "read.book",
                  "params": {"book_id": book.id, "voice_id": "adam", "rate": 5}},
                 {"id": 15, "method": "library.list"}],
                engine, repository=repository,
            )

            self.assertFalse(replies[0]["ok"])
            self.assertIn("rate", replies[0]["error"])
            self.assertEqual(engine.requests, [])
            self.assertIsNone(repository.load_progress(book.id))
            self.assertTrue(replies[1]["ok"])

    def test_read_book_resumes_from_saved_progress(self) -> None:
        from vieneu_reader.storage.repository import LibraryRepository, Progress
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([
                ("Một", [(f"Đoạn số {index}.", "paragraph")
                          for index in range(3)]),
            ])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)
            flat = list(book.chapters[0].segments)
            repository.save_progress(Progress(
                book_id=BOOK_ID, segment_id=flat[1].id,
                playback_rate=1.0, voice_id="adam",
            ))

            replies = run_server(
                [{"id": 9, "method": "read.book",
                  "params": {"book_id": BOOK_ID, "voice_id": "adam"}}],
                FakeEngine(chunks_per_sentence=1), repository=repository,
            )

            positions = [reply["segment_id"] for reply in replies
                         if reply.get("event") == "position"]
            self.assertEqual(positions, [flat[1].id, flat[2].id])

    def test_library_list_names_books_and_the_saved_position(self) -> None:
        from vieneu_reader.storage.repository import LibraryRepository, Progress
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([("Một", [("Một.", "paragraph")])])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)
            first = book.chapters[0].segments[0]
            repository.save_progress(Progress(
                book_id=BOOK_ID, segment_id=first.id,
                playback_rate=1.25, voice_id="adam",
            ))

            replies = run_server(
                [{"id": 10, "method": "library.list"},
                 {"id": 11, "method": "book.open",
                  "params": {"book_id": BOOK_ID}}],
                FakeEngine(), repository=repository,
            )

            listing = replies[0]["result"]["books"]
            self.assertEqual(len(listing), 1)
            row = listing[0]
            self.assertEqual(row["id"], BOOK_ID)
            self.assertEqual(row["title"], "Sách thử")
            self.assertEqual(row["source_format"], "epub")
            self.assertEqual(row["segment_id"], first.id)
            # Two books can share a title; what tells them apart is when they
            # arrived, how big the copy is, and their shape.
            self.assertEqual(row["chapters"], 1)
            self.assertEqual(row["size_bytes"], len(b"fixture"))
            self.assertRegex(row["imported_at"], r"^\d{4}-\d{2}-\d{2}")
            opened = replies[1]["result"]
            self.assertEqual(opened["book"]["title"], "Sách thử")
            self.assertEqual(
                opened["book"]["chapters"][0]["segments"][0]["text"], "Một.")
            self.assertEqual(opened["progress"]["segment_id"], first.id)
            self.assertEqual(opened["progress"]["rate"], 1.25)

    def test_import_and_remove_walk_through_the_real_service(self) -> None:
        """The pipe must import with the same locks, dedupe and managed copy
        the Qt app uses, and removal must not touch the source file."""
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService
        from vieneu_reader.storage.repository import LibraryRepository
        from tests.importers.epub_fixture import make_epub
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = AppPaths.create(root / "data")
            repository = LibraryRepository(paths.database)
            service = LibraryService(paths, repository)
            sources = root / "sources"
            sources.mkdir()
            source = make_epub(sources)

            replies = run_server(
                [{"id": 20, "method": "library.import",
                  "params": {"path": str(source)}},
                 {"id": 21, "method": "library.list"}],
                FakeEngine(), repository=repository, service=service,
            )

            imported = replies[0]["result"]
            self.assertTrue(replies[0]["ok"])
            self.assertFalse(imported["was_existing"])
            self.assertEqual(len(replies[1]["result"]["books"]), 1)
            book_id = imported["book_id"]

            # Importing the same file again is a no-op with a truthful flag.
            again = run_server(
                [{"id": 22, "method": "library.import",
                  "params": {"path": str(source)}}],
                FakeEngine(), repository=repository, service=service,
            )
            self.assertTrue(again[0]["result"]["was_existing"])

            removed = run_server(
                [{"id": 23, "method": "library.remove",
                  "params": {"book_id": book_id}},
                 {"id": 24, "method": "library.list"}],
                FakeEngine(), repository=repository, service=service,
            )
            self.assertTrue(removed[0]["ok"])
            self.assertEqual(removed[1]["result"]["books"], [])
            # The user's own file is never the app's to delete.
            self.assertTrue(source.exists())
            # And the managed copy is gone with the record.
            self.assertEqual(list(paths.books.glob("*")), [])

    def test_import_reports_a_broken_book_as_an_error_reply(self) -> None:
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService
        from vieneu_reader.storage.repository import LibraryRepository
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = AppPaths.create(root / "data")
            repository = LibraryRepository(paths.database)
            service = LibraryService(paths, repository)
            broken = root / "hong.epub"
            broken.write_bytes(b"not an epub at all")

            replies = run_server(
                [{"id": 25, "method": "library.import",
                  "params": {"path": str(broken)}}],
                FakeEngine(), repository=repository, service=service,
            )

            self.assertFalse(replies[0]["ok"])
            self.assertTrue(replies[0]["error"])

    def test_model_status_reports_the_build_in_use(self) -> None:
        engine = FakeEngine()
        engine.precision = "fp32"
        engine.is_model_ready = lambda: True
        engine.installed_builds = lambda: {"fp32": 625_000_000}

        replies = run_server([{"id": 30, "method": "model.status"}], engine)

        result = replies[0]["result"]
        self.assertTrue(result["ready"])
        self.assertEqual(result["precision"], "fp32")
        self.assertEqual(result["installed"], {"fp32": 625_000_000})

    def test_a_crashing_handler_answers_and_the_server_survives(self) -> None:
        """model.status once killed the whole server on a fresh data root:
        one handler exception must become one error reply, never a dead pipe."""
        engine = FakeEngine()

        def explode() -> bool:
            raise RuntimeError("marker files unreadable")

        engine.is_model_ready = explode
        replies = run_server(
            [{"id": 40, "method": "model.status"},
             {"id": 41, "method": "ping"}],
            engine,
        )

        self.assertFalse(replies[0]["ok"])
        self.assertIn("marker", replies[0]["error"])
        self.assertTrue(replies[1]["ok"], "the server died with the handler")

    def test_config_round_trips_only_known_keys(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            replies = run_server(
                [{"id": 50, "method": "config.set",
                  "params": {"key": "tauri_selection_shortcut",
                              "value": "alt+super+k"}},
                 {"id": 51, "method": "config.get",
                  "params": {"key": "tauri_selection_shortcut"}},
                 {"id": 52, "method": "config.get",
                  "params": {"key": "password"}}],
                FakeEngine(), settings_path=settings,
            )

        self.assertTrue(replies[0]["ok"])
        self.assertEqual(replies[1]["result"]["value"], "alt+super+k")
        # An open key-value store over a pipe is an attack surface; only the
        # keys the shell actually owns exist.
        self.assertFalse(replies[2]["ok"])

    def test_model_prepare_streams_progress_then_finishes(self) -> None:
        engine = FakeEngine()

        def prepare(report):
            report(0.5, "Đang tải…")
            report(1.0, "Xong.")

        engine.prepare_model = prepare
        replies = run_server([{"id": 60, "method": "model.prepare"}], engine)

        events = [r for r in replies if r.get("event") == "model_progress"]
        self.assertEqual([e["progress"] for e in events], [0.5, 1.0])
        self.assertTrue(replies[-1]["ok"])

    def test_a_download_can_be_abandoned_from_the_shell(self) -> None:
        """453MB with no way out is not a download, it is a hostage.

        The Qt setup screen could cancel; the rewrite lost that until
        2026-09-02. The progress callback is the cancel point, because it is
        the only moment a long download hands control back.
        """
        engine = FakeEngine()
        reported: list[float] = []

        def prepare(report):
            for step in range(1, 40):
                report(step / 40, "Đang tải…")
                reported.append(step / 40)

        engine.prepare_model = prepare
        replies = run_server([
            {"id": 70, "method": "model.prepare"},
            {"id": 71, "method": "stop"},
        ], engine)

        done = [r for r in replies if r.get("id") == 70 and "ok" in r]
        self.assertEqual(len(done), 1)
        self.assertTrue(done[0]["result"]["cancelled"])
        self.assertFalse(done[0]["result"]["ready"])
        # It really stopped early rather than finishing and claiming a cancel.
        self.assertLess(len(reported), 40)

    def test_set_precision_persists_and_demands_a_restart(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.speech.preferences import VoiceQualityPreferenceStore

        with TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            replies = run_server(
                [{"id": 61, "method": "model.set_precision",
                  "params": {"precision": "fp32"}}],
                FakeEngine(), settings_path=settings,
            )
            self.assertTrue(replies[0]["result"]["restart_required"])
            self.assertEqual(VoiceQualityPreferenceStore(settings).load(), "fp32")

    def _notes_fixture(self, *, copyable: int, already: int = 0,
                        books_running=False, backup_fails=False,
                        copy_raises=None):
        """Injectable notes machinery mirroring the real shapes."""
        from types import SimpleNamespace
        from vieneu_reader.integrations import apple_books as reading
        from vieneu_reader.integrations import apple_books_writer as writing

        annotations = []
        for index in range(copyable):
            annotations.append(SimpleNamespace(
                kind=2, has_note=False, note=None,
                selected_text=f"đoạn {index}", location=f"loc-{index}",
            ))
        items = [SimpleNamespace(annotation=a, verdict="same-edition")
                 for a in annotations]
        for index in range(already):
            a = SimpleNamespace(kind=2, has_note=False, note=None,
                                 selected_text="cũ", location=f"old-{index}")
            items.append(SimpleNamespace(annotation=a, verdict="already-there"))
        plan = SimpleNamespace(
            source=SimpleNamespace(title="Bản A"),
            target=SimpleNamespace(title="Bản B"),
            same_edition=True,
            items=tuple(items),
            copyable=tuple(i for i in items if i.verdict == "same-edition"),
        )
        written = {"count": 0}

        def copy(database, source, target, *, backup, only_locations,
                 books_is_running):
            if copy_raises is not None:
                raise copy_raises
            written["count"] = len(only_locations)
            return len(only_locations)

        def back_up(database, destination):
            if backup_fails:
                raise OSError("disk full")
            return destination / "backup.sqlite"

        deps = {
            "library": SimpleNamespace(
                books=lambda: (),
                annotation_database=__import__("pathlib").Path("/tmp/fake.sqlite"),
            ),
            "plan": lambda source, target: plan,
            "copy": copy,
            "back_up": back_up,
            "prune": lambda root: 0,
            "books_running": lambda: books_running,
            "errors": reading,
            "writer_errors": writing,
        }
        return deps, written

    def test_notes_transfer_backs_up_then_copies_only_the_copyable(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        deps, written = self._notes_fixture(copyable=3, already=2)
        with TemporaryDirectory() as directory:
            replies = run_server(
                [{"id": 70, "method": "notes.transfer",
                  "params": {"source": "a", "target": "b"}}],
                FakeEngine(), settings_path=Path(directory) / "settings.json",
                notes_deps=deps,
            )
        result = replies[0]["result"]
        self.assertEqual(result["outcome"], "copied")
        self.assertEqual(result["written"], 3)
        self.assertEqual(written["count"], 3)

    def test_notes_transfer_refuses_while_books_is_open(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        deps, written = self._notes_fixture(copyable=3, books_running=True)
        with TemporaryDirectory() as directory:
            replies = run_server(
                [{"id": 71, "method": "notes.transfer",
                  "params": {"source": "a", "target": "b"}}],
                FakeEngine(), settings_path=Path(directory) / "settings.json",
                notes_deps=deps,
            )
        self.assertEqual(replies[0]["result"]["outcome"], "books_open")
        self.assertEqual(written["count"], 0)

    def test_notes_transfer_writes_nothing_when_backup_fails(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        deps, written = self._notes_fixture(copyable=3, backup_fails=True)
        with TemporaryDirectory() as directory:
            replies = run_server(
                [{"id": 72, "method": "notes.transfer",
                  "params": {"source": "a", "target": "b"}}],
                FakeEngine(), settings_path=Path(directory) / "settings.json",
                notes_deps=deps,
            )
        self.assertEqual(replies[0]["result"]["outcome"], "backup_failed")
        self.assertEqual(written["count"], 0, "wrote despite no backup")

    def test_notes_transfer_reports_all_already_there(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        deps, _ = self._notes_fixture(copyable=0, already=4)
        with TemporaryDirectory() as directory:
            replies = run_server(
                [{"id": 73, "method": "notes.transfer",
                  "params": {"source": "a", "target": "b"}}],
                FakeEngine(), settings_path=Path(directory) / "settings.json",
                notes_deps=deps,
            )
        result = replies[0]["result"]
        self.assertEqual(result["outcome"], "all_already_there")
        self.assertEqual(result["count"], 4)

    def test_the_server_imports_without_qt_installed(self) -> None:
        """The packaged sidecar ships without PySide6. The venv hides this
        class of break - PySide6 is always importable here - so the test
        poisons the import instead."""
        import subprocess
        import sys as _sys

        probe = (
            "import sys; sys.modules['PySide6'] = None; "
            "import vieneu_reader.headless.server; print('QT_FREE_OK')"
        )
        result = subprocess.run(
            [_sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=60,
            env={"PYTHONPATH": "src", "HOME": "/tmp", "PATH": "/usr/bin:/bin"},
            cwd=str(__import__("pathlib").Path(__file__).resolve().parents[2]),
        )
        self.assertIn("QT_FREE_OK", result.stdout, result.stderr[-500:])

    def test_reading_a_book_announces_each_picture_where_it_sits(self) -> None:
        """A listener cannot see the page. When the reading reaches a picture
        the voice says "Xem hình N." - numbered per chapter, placed before or
        after its anchor as the book laid it out - and the position event for
        that cue carries the figure id so the shell can show the picture at
        the moment the ear hears the cue (owner's call, 2026-09-02).
        """
        from types import SimpleNamespace
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.storage.repository import LibraryRepository

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([(
                "Một",
                [("Đoạn đầu.", "paragraph"), ("Đoạn hai.", "paragraph")],
            )])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)
            first, second = book.chapters[0].segments
            figures = (
                SimpleNamespace(
                    id="fig-a", number=41, chapter_id=book.chapters[0].id,
                    anchor_segment_id=first.id, placement="after",
                    media_type="image/png", alt_text="Image",
                    alt_is_generic=True, asset_path="a.png",
                ),
                SimpleNamespace(
                    id="fig-b", number=42, chapter_id=book.chapters[0].id,
                    anchor_segment_id=second.id, placement="before",
                    media_type="image/png", alt_text="Sơ đồ thật",
                    alt_is_generic=False, asset_path="b.png",
                ),
            )
            presentation = SimpleNamespace(chapters=[SimpleNamespace(
                chapter_id=book.chapters[0].id, figures=figures,
            )])
            service = SimpleNamespace(
                presentation_for=lambda book, path: presentation,
                assets_for=lambda book, path, figures: {},
            )
            engine = FakeEngine()
            replies = run_server([
                {"id": 90, "method": "book.open", "params": {"book_id": book.id}},
                {"id": 91, "method": "read.book",
                 "params": {"book_id": book.id, "voice_id": "adam"}},
            ], engine, repository=repository, service=service)

            # book.open: numbered per chapter (not the domain's 41/42), and the
            # generic alt is flagged so the shell can hide the word "Image".
            opened = replies[0]["result"]["book"]["chapters"][0]["figures"]
            self.assertEqual([f["number"] for f in opened], [1, 2])
            self.assertEqual([f["alt_is_generic"] for f in opened], [True, False])

            # What the voice was asked to say, in order.
            spoken = [text for text, _voice in engine.requests]
            self.assertEqual(spoken, [
                "Đoạn đầu.", "Xem hình 1.", "Xem hình 2.", "Đoạn hai.",
            ])

            # And the cue's position carries the figure, the prose's does not.
            positions = [r for r in replies if r.get("event") == "position"]
            self.assertEqual(
                [p.get("figure_id") for p in positions],
                [None, "fig-a", "fig-b", None],
            )
        # A second-chapter picture starts again at 1 - that is the promise.

    def test_book_open_lists_figures_and_book_figure_serves_bytes(self) -> None:
        """EPUB figures ride the same pipe: refs inline in book.open, bytes
        lazily per figure - a whole art book must not sit inside one reply."""
        from types import SimpleNamespace
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.storage.repository import LibraryRepository

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([("Một", [("Đoạn có hình.", "paragraph")])])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)
            segment = book.chapters[0].segments[0]
            figure = SimpleNamespace(
                id="fig-1", number=1, chapter_id=book.chapters[0].id,
                anchor_segment_id=segment.id, placement="after",
                media_type="image/png", alt_text="Sơ đồ", alt_is_generic=False,
                # Deliberately NOT the id: a fixture where the two are the
                # same string cannot tell a correct lookup from the wrong one.
                asset_path="OEBPS/images/one.png",
            )
            presentation = SimpleNamespace(
                chapters=[SimpleNamespace(
                    chapter_id=book.chapters[0].id, figures=(figure,),
                )],
            )
            service = SimpleNamespace(
                presentation_for=lambda book, path: presentation,
                # Keyed the way the real `load_epub_assets` keys it: by the
                # member name inside the archive. The old fake answered to the
                # figure id instead, which is what let a caller that asked by
                # id pass this test while no figure ever loaded (2026-09-02).
                assets_for=lambda book, path, figures: {
                    "OEBPS/images/one.png": b"\x89PNG-fake-bytes",
                },
            )

            replies = run_server(
                [{"id": 80, "method": "book.open",
                  "params": {"book_id": BOOK_ID}},
                 {"id": 81, "method": "book.figure",
                  "params": {"book_id": BOOK_ID, "figure_id": "fig-1"}},
                 {"id": 82, "method": "book.figure",
                  "params": {"book_id": BOOK_ID, "figure_id": "missing"}}],
                FakeEngine(), repository=repository, service=service,
            )

        listed = replies[0]["result"]["book"]["chapters"][0]["figures"]
        self.assertEqual(listed, [{
            "id": "fig-1", "anchor_segment_id": segment.id,
            "placement": "after", "alt": "Sơ đồ",
            "number": 1, "alt_is_generic": False,
        }])
        served = replies[1]["result"]
        self.assertEqual(served["media_type"], "image/png")
        self.assertEqual(
            base64.b64decode(served["data"]), b"\x89PNG-fake-bytes")
        self.assertFalse(replies[2]["ok"])

    def test_book_cover_serves_bytes_or_null_fields(self) -> None:
        """No cover is an ordinary answer for a shelf, not an error."""
        from types import SimpleNamespace
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.storage.repository import LibraryRepository

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([("Một", [("Đoạn.", "paragraph")])])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)
            covers = {book.id: (b"\xff\xd8-jpeg", "image/jpeg")}
            service = SimpleNamespace(
                cover_for=lambda stored, path: covers.get(stored.id),
            )
            replies = run_server(
                [{"id": 60, "method": "book.cover", "params": {"book_id": BOOK_ID}},
                 {"id": 61, "method": "book.cover", "params": {"book_id": "nope"}}],
                FakeEngine(), repository=repository, service=service,
            )
            self.assertEqual(replies[0]["result"]["media_type"], "image/jpeg")
            self.assertEqual(base64.b64decode(replies[0]["result"]["data"]), b"\xff\xd8-jpeg")
            self.assertFalse(replies[1]["ok"])

            covers.clear()
            replies = run_server(
                [{"id": 62, "method": "book.cover", "params": {"book_id": BOOK_ID}}],
                FakeEngine(), repository=repository, service=service,
            )
            self.assertTrue(replies[0]["ok"])
            self.assertEqual(replies[0]["result"], {"media_type": None, "data": None})

    def test_library_list_says_how_far_and_in_which_chapter(self) -> None:
        from vieneu_reader.storage.repository import LibraryRepository, Progress
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = LibraryRepository(root / "reader.sqlite3")
            book = build_book([
                ("Một", [("A.", "paragraph"), ("B.", "paragraph")]),
                ("Hai", [("C.", "paragraph"), ("D.", "paragraph")]),
            ])
            source = root / "book.epub"
            source.write_bytes(b"fixture")
            repository.add_book(book, source)
            third = book.chapters[1].segments[0]

            before = run_server([{"id": 70, "method": "library.list"}],
                                FakeEngine(), repository=repository)
            repository.save_progress(Progress(
                book_id=book.id, segment_id=third.id, playback_rate=1.0, voice_id="adam",
            ))
            after = run_server([{"id": 71, "method": "library.list"}],
                               FakeEngine(), repository=repository)

        row = before[0]["result"]["books"][0]
        self.assertIsNone(row["progress_ratio"])
        self.assertIsNone(row["progress_chapter"])
        row = after[0]["result"]["books"][0]
        self.assertEqual(row["progress_ratio"], 0.5)
        self.assertEqual(row["progress_chapter"], "Hai")

    def _apple_fixture(self, root, *, extra_highlight: bool = False):
        """A tiny unpacked EPUB on disk, an Apple Books reader stub, and a repository."""
        from types import SimpleNamespace
        from vieneu_reader.integrations.apple_books import Annotation
        from vieneu_reader.storage.repository import LibraryRepository
        from tests.importers.epub_fixture import make_epub
        from zipfile import ZipFile

        repository = LibraryRepository(root / "reader.sqlite3")
        packed = make_epub(root, name="seed.epub", title="Thiên Nga Đen")
        folder = root / "Thiên Nga Đen.epub"
        with ZipFile(packed) as archive:
            archive.extractall(folder)
        apple_book = SimpleNamespace(asset_id="A1", title="Thiên Nga Đen", edition_id="e", reading_progress=0.0, path=str(folder))
        notes = {"A1": (
            Annotation("A1", 2, "epubcfi(/6/4!/4/2)", selected_text="Nội dung chương hai", note="hay", style=3),
            Annotation("A1", 2, "epubcfi(/6/4!/4/2)", selected_text="không có trong sách"),
            Annotation("A1", 3, "epubcfi(/6/4!/4/2)"),
        ) + ((
            # A highlight with no note of its own - the kind a mode of
            # "notes" does not carry. Off by default so the counts every
            # other test asserts stay where they are.
            Annotation("A1", 2, "epubcfi(/6/2!/4/2)", selected_text="Nội dung chương một", style=1),
        ) if extra_highlight else ())}
        library = SimpleNamespace(
            books=lambda: (apple_book,),
            book=lambda asset_id: apple_book,
            annotations=lambda asset_id: notes.get(asset_id, ()),
            annotations_for=lambda *ids: {i: notes.get(i, ()) for i in ids},
        )
        return repository, library

    def test_the_shelf_says_which_books_are_paired_with_apple_books(self) -> None:
        # The badge on the shelf reports the LINK, so the flag has to follow
        # the link and nothing else: a book imported by hand is not paired,
        # and one imported from Apple Books is - without the shelf going and
        # reading Apple's own database to find out.
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository, library = self._apple_fixture(root)
            service = LibraryService(AppPaths.create(root / "app"), repository)
            deps = {"library": library}

            def flags():
                reply = run_server(
                    [{"id": 9, "method": "library.list"}],
                    FakeEngine(), repository=repository, service=service,
                    notes_deps=deps,
                )[0]
                return {
                    book["title"]: book["from_apple_books"]
                    for book in reply["result"]["books"]
                }

            # A book that arrived by hand: the flag has to be False for it,
            # or a hardcoded True would pass this test just as well.
            from tests.importers.epub_fixture import make_epub
            sources = root / "by-hand"
            sources.mkdir()
            run_server(
                [{"id": 1, "method": "library.import",
                  "params": {"path": str(make_epub(sources))}}],
                FakeEngine(), repository=repository, service=service, notes_deps=deps,
            )
            by_hand = flags()
            self.assertEqual(len(by_hand), 1, by_hand)
            self.assertFalse(any(by_hand.values()), by_hand)

            run_server(
                [{"id": 2, "method": "applebooks.import", "params": {"asset_id": "A1"}}],
                FakeEngine(), repository=repository, service=service, notes_deps=deps,
            )
            both = flags()
            self.assertEqual(len(both), 2, both)
            self.assertEqual(sorted(both.values()), [False, True], both)

    def test_apple_books_shelf_import_and_note_sync_round_trip(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository, library = self._apple_fixture(root)
            service = LibraryService(AppPaths.create(root / "app"), repository)
            deps = {"library": library}
            replies = run_server(
                [{"id": 1, "method": "applebooks.shelf"},
                 {"id": 2, "method": "applebooks.import", "params": {"asset_id": "A1"}},
                 {"id": 3, "method": "applebooks.shelf"},
                 {"id": 4, "method": "applebooks.import", "params": {"asset_id": "A1"}},
                 {"id": 5, "method": "applebooks.sync_notes", "params": {"asset_id": "A1"}},
                 {"id": 6, "method": "library.list"}],
                FakeEngine(), repository=repository, service=service, notes_deps=deps,
            )
            before = replies[0]["result"]["books"][0]
            self.assertEqual((before["status"], before["highlights"]), ("importable", 2))
            imported = replies[1]["result"]
            self.assertFalse(imported["was_existing"])
            after = replies[2]["result"]["books"][0]
            self.assertEqual((after["status"], after["book_id"]), ("linked", imported["book_id"]))
            # The same folder again is the same book, by bytes and by link.
            self.assertTrue(replies[3]["result"]["was_existing"])
            synced = replies[4]["result"]
            self.assertEqual((synced["matched"], synced["unmatched"], synced["skipped"]), (1, 1, 1))
            self.assertEqual(len(replies[5]["result"]["books"]), 1)

            opened = run_server(
                [{"id": 7, "method": "book.open", "params": {"book_id": imported["book_id"]}}],
                FakeEngine(), repository=repository, service=service, notes_deps=deps,
            )[0]["result"]
            self.assertEqual(len(opened["annotations"]), 1)
            self.assertEqual(opened["annotations"][0]["note"], "hay")
            segment_ids = {s["id"] for c in opened["book"]["chapters"] for s in c["segments"]}
            self.assertIn(opened["annotations"][0]["segment_id"], segment_ids)

    def test_a_plain_read_says_which_part_it_is_speaking(self) -> None:
        events = run_server(
            [{"id": 1, "method": "read", "params": {
                "text": "Câu một. Câu hai.\n\nĐoạn sau.", "voice_id": "v",
            }}],
            FakeEngine(),
        )
        parts = [e["segment_id"] for e in events if e.get("event") == "position"]
        self.assertEqual(parts, ["part-0", "part-1"])

    def test_a_plain_read_can_carry_on_from_the_part_it_reached(self) -> None:
        # What changing the voice mid-reading needs: the same text, resumed
        # where the ear was, not restarted from the top.
        engine = FakeEngine()
        events = run_server(
            [{"id": 1, "method": "read", "params": {
                "text": "Câu một.\n\nĐoạn hai.\n\nĐoạn ba.",
                "voice_id": "v", "segment_id": "part-2",
            }}],
            engine,
        )
        parts = [e["segment_id"] for e in events if e.get("event") == "position"]
        self.assertEqual(parts, ["part-2"])
        self.assertNotIn("Câu một.", " ".join(t for t, _ in engine.requests))

    def test_a_plain_read_refuses_a_part_it_does_not_have(self) -> None:
        reply = run_server(
            [{"id": 1, "method": "read", "params": {
                "text": "Một câu.", "voice_id": "v", "segment_id": "part-9",
            }}],
            FakeEngine(),
        )[0]
        self.assertFalse(reply["ok"])

    def test_apple_books_note_sync_modes_keep_what_was_asked_for(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository, library = self._apple_fixture(root)
            service = LibraryService(AppPaths.create(root / "app"), repository)
            deps = {"library": library}
            imported = run_server(
                [{"id": 1, "method": "applebooks.import", "params": {"asset_id": "A1"}}],
                FakeEngine(), repository=repository, service=service, notes_deps=deps,
            )[0]["result"]["book_id"]
            def synced(mode):
                run_server(
                    [{"id": 2, "method": "applebooks.sync_notes", "params": {"asset_id": "A1", "mode": mode}}],
                    FakeEngine(), repository=repository, service=service, notes_deps=deps,
                )
                return [(a.selected_text, a.note) for a in repository.annotations_for(imported)]
            self.assertEqual(synced("highlights"), [("Nội dung chương hai", None)])
            self.assertEqual(synced("notes"), [("Nội dung chương hai", "hay")])
            self.assertEqual(synced("both"), [("Nội dung chương hai", "hay")])
            bad = run_server(
                [{"id": 3, "method": "applebooks.sync_notes", "params": {"asset_id": "A1", "mode": "all"}}],
                FakeEngine(), repository=repository, service=service, notes_deps=deps,
            )[0]
            self.assertFalse(bad["ok"])

    def test_a_narrower_sync_mode_also_drops_what_it_no_longer_covers(self) -> None:
        # Pinning what HAPPENS, because until now nothing did, and what
        # happens is easy to be surprised by: `sync_notes` replaces every
        # `source=applebooks` row for the book, so a mode of "notes" does not
        # merely decline to bring plain highlights over - it removes the ones
        # an earlier "both" already brought.
        #
        # Nothing is lost: Apple Books is the source of truth, so syncing
        # "both" again puts it straight back, which the last assertion proves.
        # Whether the menu should read as "bring only notes" (a filter on the
        # transfer) or "hold only notes" (a filter on the mirror) is the
        # owner's call - this test says which one it is today, so a change
        # would have to be a decision rather than an accident.
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository, library = self._apple_fixture(root, extra_highlight=True)
            service = LibraryService(AppPaths.create(root / "app"), repository)
            deps = {"library": library}
            book_id = run_server(
                [{"id": 1, "method": "applebooks.import", "params": {"asset_id": "A1"}}],
                FakeEngine(), repository=repository, service=service, notes_deps=deps,
            )[0]["result"]["book_id"]

            def synced(mode):
                reply = run_server(
                    [{"id": 2, "method": "applebooks.sync_notes",
                      "params": {"asset_id": "A1", "mode": mode}}],
                    FakeEngine(), repository=repository, service=service, notes_deps=deps,
                )[0]["result"]
                held = [a.selected_text for a in repository.annotations_for(book_id)]
                return reply, sorted(held)

            reply, held = synced("both")
            self.assertEqual(held, ["Nội dung chương hai", "Nội dung chương một"])
            self.assertEqual(reply["matched"], 2)

            reply, held = synced("notes")
            self.assertEqual(held, ["Nội dung chương hai"])
            # And the reply counts it as skipped-on-the-way-in. It does not
            # say that one already here was removed, which is why the shell
            # cannot tell the person either.
            self.assertEqual((reply["matched"], reply["skipped"]), (1, 2))

            _reply, held = synced("both")
            self.assertEqual(held, ["Nội dung chương hai", "Nội dung chương một"])

    def test_a_deleted_highlight_does_not_come_back_on_the_next_sync(self) -> None:
        # The whole point of deleting: a sync is a mirror of Apple Books, so
        # without a tombstone the next one would put the highlight straight
        # back (owner, 03/09: "xoá hẳn luôn").
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository, library = self._apple_fixture(root)
            service = LibraryService(AppPaths.create(root / "app"), repository)
            deps = {"library": library}
            def call(n, method, params):
                return run_server(
                    [{"id": n, "method": method, "params": params}],
                    FakeEngine(), repository=repository, service=service,
                    notes_deps=deps,
                )[0]
            book_id = call(1, "applebooks.import", {"asset_id": "A1"})["result"]["book_id"]
            call(2, "applebooks.sync_notes", {"asset_id": "A1"})
            carried = repository.annotations_for(book_id)
            self.assertTrue(carried)

            gone = call(3, "annotations.delete", {
                "book_id": book_id, "annotation_id": carried[0].id,
            })
            self.assertTrue(gone["result"]["removed"])
            self.assertEqual(repository.annotations_for(book_id), ())

            call(4, "applebooks.sync_notes", {"asset_id": "A1"})
            self.assertEqual(repository.annotations_for(book_id), ())
            self.assertIn(carried[0].id, repository.forgotten_annotations(book_id))

    def test_deleting_a_highlight_that_is_not_there_says_so(self) -> None:
        # The real "not there" case is a stale id on a book that DOES exist -
        # a second window removed it first, say. It answers rather than
        # throwing, so the shell can tell "gone" from "never here".
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository, library = self._apple_fixture(root)
            service = LibraryService(AppPaths.create(root / "app"), repository)
            def call(n, params):
                return run_server(
                    [{"id": n, "method": "annotations.delete", "params": params}],
                    FakeEngine(), repository=repository, service=service,
                    notes_deps={"library": library},
                )[0]
            book_id = run_server(
                [{"id": 0, "method": "applebooks.import", "params": {"asset_id": "A1"}}],
                FakeEngine(), repository=repository, service=service,
                notes_deps={"library": library},
            )[0]["result"]["book_id"]

            reply = call(1, {"book_id": book_id, "annotation_id": "khong-co"})
            self.assertTrue(reply["ok"])
            self.assertFalse(reply["result"]["removed"])

            bad = call(2, {"book_id": book_id})
            self.assertFalse(bad["ok"])

    def test_apple_books_refuses_what_it_cannot_read(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from vieneu_reader.config import AppPaths
        from vieneu_reader.importers.service import LibraryService

        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository, library = self._apple_fixture(root)
            (root / "Thiên Nga Đen.epub" / "META-INF" / "encryption.xml").write_bytes(
                b"""<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                <EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#"><CipherData>
                <CipherReference URI="OEBPS/chapter-1.xhtml"/></CipherData></EncryptedData></encryption>"""
            )
            service = LibraryService(AppPaths.create(root / "app"), repository)
            replies = run_server(
                [{"id": 1, "method": "applebooks.shelf"},
                 {"id": 2, "method": "applebooks.import", "params": {"asset_id": "A1"}},
                 {"id": 3, "method": "applebooks.sync_notes", "params": {"asset_id": "A1"}}],
                FakeEngine(), repository=repository, service=service, notes_deps={"library": library},
            )
            self.assertEqual(replies[0]["result"]["books"][0]["status"], "encrypted")
            self.assertIn("encrypted", replies[1]["error"])
            self.assertIn("not_in_library", replies[2]["error"])

    def test_a_stop_then_read_supersedes_the_reading_in_flight(self) -> None:
        """The shell cancels before it starts, and this is why it must.

        A read arriving mid-stream is DEFERRED by design, not merged: without
        the stop in front of it the engine finishes the old text first, which
        is what made an impatient second click buy a second full reading
        instead of a new one (2026-09-02).
        """
        engine = FakeEngine(chunks_per_sentence=200, chunk_delay=0.01)
        request_read, request_write = os.pipe()
        reply_read, reply_write = os.pipe()
        reader = os.fdopen(request_read, "r")
        writer = os.fdopen(reply_write, "w")
        requests = os.fdopen(request_write, "w")
        replies = os.fdopen(reply_read, "r")

        server = threading.Thread(
            target=serve, args=(reader, writer, engine), daemon=True
        )
        server.start()
        try:
            requests.write(json.dumps({
                "id": 10,
                "method": "read",
                "params": {"text": "Câu thứ nhất.", "voice_id": "adam"},
            }) + "\n")
            requests.flush()
            self.assertEqual(_first_audio(replies)["event"], "chunk")

            # Exactly the pair the Rust client sends when a reading starts
            # while another one is running.
            requests.write(json.dumps({"id": 11, "method": "stop"}) + "\n")
            requests.write(json.dumps({
                "id": 12,
                "method": "read",
                "params": {"text": "Câu thứ hai.", "voice_id": "adam"},
            }) + "\n")
            requests.flush()

            first_done = None
            chunks_after_cut = 0
            second_chunks = 0
            second_done = None
            for line in replies:
                message = json.loads(line)
                if message.get("id") == 10 and "ok" in message:
                    first_done = message
                elif message.get("id") == 10 and message.get("event") == "chunk":
                    if first_done is None:
                        continue
                    chunks_after_cut += 1
                elif message.get("id") == 12 and message.get("event") == "chunk":
                    second_chunks += 1
                elif message.get("id") == 12 and "ok" in message:
                    second_done = message
                    break

            self.assertIsNotNone(first_done)
            self.assertTrue(first_done["result"]["stopped"])
            # The superseded reading emits nothing once it has closed out.
            self.assertEqual(chunks_after_cut, 0)
            # And the new one really runs, rather than being swallowed.
            self.assertGreater(second_chunks, 0)
            self.assertIsNotNone(second_done)
            self.assertFalse(second_done["result"]["stopped"])
        finally:
            requests.close()
            reader.close()

    def test_quick_requests_are_answered_while_a_reading_streams(self) -> None:
        """Listening is not a modal state. Switching to the library, saving a
        speed change, loading a picture that scrolled into view - all of that
        used to wait until the reading ended (6.56 s for six sentences, minutes
        for a chapter, past the shell's 30 s timeout), which the person saw as
        the app hanging (2026-09-02). Quick, harmless requests are answered
        between chunks now; the heavy ones still wait their turn.
        """
        engine = FakeEngine(chunks_per_sentence=200, chunk_delay=0.01)
        request_read, request_write = os.pipe()
        reply_read, reply_write = os.pipe()
        reader = os.fdopen(request_read, "r")
        writer = os.fdopen(reply_write, "w")
        requests = os.fdopen(request_write, "w")
        replies = os.fdopen(reply_read, "r")
        server = threading.Thread(
            target=serve, args=(reader, writer, engine), daemon=True
        )
        server.start()
        try:
            requests.write(json.dumps({
                "id": 20, "method": "read",
                "params": {"text": "Một câu rất dài.", "voice_id": "adam"},
            }) + "\n")
            requests.flush()
            self.assertEqual(_first_audio(replies)["event"], "chunk")
            requests.write(json.dumps({"id": 21, "method": "ping"}) + "\n")
            requests.write(json.dumps({"id": 22, "method": "stop"}) + "\n")
            requests.flush()

            order = []
            for line in replies:
                message = json.loads(line)
                if "ok" in message:
                    order.append(message["id"])
                if message.get("id") == 20 and "ok" in message:
                    break
            # The ping came back BEFORE the reading closed out - it did not
            # wait in the deferred queue behind the whole utterance.
            self.assertEqual(order.index(21) < order.index(20), True)
        finally:
            requests.close()
            reader.close()

    def test_stop_interrupts_a_reading_mid_stream(self) -> None:
        engine = FakeEngine(chunks_per_sentence=200, chunk_delay=0.01)
        request_read, request_write = os.pipe()
        reply_read, reply_write = os.pipe()
        reader = os.fdopen(request_read, "r")
        writer = os.fdopen(reply_write, "w")
        requests = os.fdopen(request_write, "w")
        replies = os.fdopen(reply_read, "r")

        server = threading.Thread(
            target=serve, args=(reader, writer, engine), daemon=True
        )
        server.start()
        try:
            requests.write(json.dumps({
                "id": 5,
                "method": "read",
                "params": {"text": "Một câu rất dài.", "voice_id": "adam"},
            }) + "\n")
            requests.flush()
            first = _first_audio(replies)
            self.assertEqual(first["event"], "chunk")
            requests.write(json.dumps({"id": 6, "method": "stop"}) + "\n")
            requests.flush()

            done = None
            for line in replies:
                message = json.loads(line)
                if message.get("id") == 5 and "ok" in message:
                    done = message
                    break
            self.assertIsNotNone(done)
            self.assertTrue(done["result"]["stopped"])
            self.assertLess(done["result"]["voiced_frames"], 200)
        finally:
            requests.close()
            server.join(timeout=5)
            self.assertFalse(server.is_alive(), "server did not exit at EOF")
            for stream in (reader, writer, replies):
                stream.close()


if __name__ == "__main__":
    unittest.main()
