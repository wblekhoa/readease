from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory
import unittest

from vieneu_reader.config import AppPaths
from vieneu_reader.domain.models import AudioChunk, Voice
from vieneu_reader.storage.repository import LibraryRepository

from tests.importers.epub_fixture import make_epub, make_png
from tests.ui.real_book_smoke import run_book_smoke


class _ReadySpeechEngine:
    is_model_ready = True

    def __init__(self, _models_path: Path):
        self.spoken_texts: list[str] = []

    def voices(self) -> tuple[Voice, ...]:
        return (Voice(id="Adam", label="Adam"),)

    def stream(self, text: str, voice_id: str):
        if voice_id != "Adam":
            raise AssertionError("unexpected voice")
        self.spoken_texts.append(text)
        yield AudioChunk(pcm=struct.pack("<4800f", *([0.5] * 4800)))


class _MissingSpeechEngine(_ReadySpeechEngine):
    is_model_ready = False


class RealBookSmokeTests(unittest.TestCase):
    def test_shell_entrypoint_runs_a_caller_supplied_book(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            source = make_epub(sources)
            script = Path(__file__).resolve().parents[2] / "scripts" / "smoke-real-book.sh"

            completed = subprocess.run(
                [script, source],
                cwd=script.parent.parent,
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("REAL_BOOK_SMOKE PASS", completed.stdout)
        self.assertIn("duplicate=1", completed.stdout)
        self.assertIn("restore=1", completed.stdout)

    def test_import_duplicate_and_restart_progress_without_touching_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            source = make_epub(sources)
            source_before = sha256(source.read_bytes()).hexdigest()
            app_root = root / "isolated-app-data"

            receipt = run_book_smoke(source, app_root)

            self.assertEqual(receipt.source_format, "epub")
            self.assertEqual(receipt.chapters, 2)
            self.assertGreaterEqual(receipt.segments, 4)
            self.assertGreater(receipt.characters, 0)
            self.assertTrue(receipt.duplicate_detected)
            self.assertTrue(receipt.restored_progress)
            self.assertEqual(receipt.figures, 0)
            self.assertEqual(receipt.loaded_figure_assets, 0)
            self.assertEqual(receipt.rendered_figures, 0)
            self.assertEqual(receipt.accessible_figure_descriptions, 0)
            self.assertEqual(receipt.max_figure_overflow, 0)
            self.assertEqual(receipt.figure_cues, 0)
            self.assertTrue(receipt.document_payload_unchanged)
            self.assertEqual(receipt.audio_samples, 0)
            self.assertEqual(sha256(source.read_bytes()).hexdigest(), source_before)

            paths = AppPaths.create(app_root)
            repository = LibraryRepository(paths.database)
            try:
                self.assertEqual(repository.count_books(), 1)
                stored = repository.list_books()[0]
                self.assertEqual(stored.managed_path.parent, paths.books.resolve())
                self.assertEqual(
                    sha256(stored.managed_path.read_bytes()).hexdigest(),
                    source_before,
                )
            finally:
                repository.close()

    def test_image_aware_smoke_loads_a_real_managed_figure_without_db_rewrite(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
            <h1>Một</h1><p>Nội dung.</p>
            <img src="images/diagram.png" alt="Sơ đồ"/>
            </body></html>"""
            source = make_epub(
                sources,
                spine=("chapter-1",),
                chapter_overrides={"chapter-1": chapter},
                image_entries={
                    "images/diagram.png": (make_png(320, 200), "image/png"),
                },
            )

            receipt = run_book_smoke(source, root / "isolated-app-data")

        self.assertEqual(receipt.figures, 1)
        self.assertEqual(receipt.loaded_figure_assets, 1)
        self.assertEqual(receipt.rendered_figures, 1)
        self.assertEqual(receipt.accessible_figure_descriptions, 1)
        self.assertEqual(receipt.max_figure_overflow, 0)
        self.assertEqual(receipt.figure_cues, 1)
        self.assertTrue(receipt.document_payload_unchanged)

    def test_optional_ready_engine_receives_the_numbered_figure_cue(self):
        created: list[_ReadySpeechEngine] = []

        def factory(models_path: Path) -> _ReadySpeechEngine:
            engine = _ReadySpeechEngine(models_path)
            created.append(engine)
            return engine

        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
            <h1>Một</h1><p>Nội dung.</p>
            <img src="images/diagram.png" alt="Sơ đồ"/>
            </body></html>"""
            source = make_epub(
                sources,
                spine=("chapter-1",),
                chapter_overrides={"chapter-1": chapter},
                image_entries={
                    "images/diagram.png": (make_png(320, 200), "image/png"),
                },
            )

            receipt = run_book_smoke(
                source,
                root / "isolated-app-data",
                speech_engine_factory=factory,
                models_path=root / "prepared-models",
            )

        self.assertEqual(receipt.figure_cues, 1)
        self.assertEqual(len(created), 1)
        self.assertIn("Mời bạn xem Hình 1.", created[0].spoken_texts[0])

    def test_optional_ready_engine_proves_non_silent_book_audio(self):
        created: list[_ReadySpeechEngine] = []

        def factory(models_path: Path) -> _ReadySpeechEngine:
            engine = _ReadySpeechEngine(models_path)
            created.append(engine)
            return engine

        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            source = make_epub(sources)

            receipt = run_book_smoke(
                source,
                root / "isolated-app-data",
                speech_engine_factory=factory,
                models_path=root / "prepared-models",
            )

        self.assertEqual(receipt.audio_samples, 4800)
        self.assertAlmostEqual(receipt.audio_peak, 0.5)
        self.assertEqual(len(created), 1)
        self.assertTrue(created[0].spoken_texts)
        self.assertIn("Một", created[0].spoken_texts[0])

    def test_optional_engine_fails_closed_when_model_is_not_ready(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            source = make_epub(sources)

            with self.assertRaisesRegex(RuntimeError, "chưa sẵn sàng"):
                run_book_smoke(
                    source,
                    root / "isolated-app-data",
                    speech_engine_factory=_MissingSpeechEngine,
                    models_path=root / "missing-models",
                )


if __name__ == "__main__":
    unittest.main()
