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
                media_type="image/png", alt_text="Sơ đồ",
            )
            presentation = SimpleNamespace(
                chapters=[SimpleNamespace(
                    chapter_id=book.chapters[0].id, figures=(figure,),
                )],
            )
            service = SimpleNamespace(
                presentation_for=lambda book, path: presentation,
                assets_for=lambda book, path, figures: {
                    "fig-1": b"\x89PNG-fake-bytes",
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
        }])
        served = replies[1]["result"]
        self.assertEqual(served["media_type"], "image/png")
        self.assertEqual(
            base64.b64decode(served["data"]), b"\x89PNG-fake-bytes")
        self.assertFalse(replies[2]["ok"])

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
            first = json.loads(replies.readline())
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
