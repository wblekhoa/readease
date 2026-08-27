"""Portable real-book proof for import, restore, and optional VieNeu audio."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
import math
import os
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vieneu_reader.config import AppPaths, default_app_root
from vieneu_reader.importers.service import LibraryService
from vieneu_reader.storage.repository import LibraryRepository, Progress


@dataclass(frozen=True, slots=True)
class BookSmokeReceipt:
    source_format: str
    chapters: int
    segments: int
    characters: int
    duplicate_detected: bool
    restored_progress: bool
    figures: int
    loaded_figure_assets: int
    rendered_figures: int
    accessible_figure_descriptions: int
    max_figure_overflow: int
    figure_cues: int
    document_payload_unchanged: bool
    audio_samples: int
    audio_peak: float


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _prove_audio(engine: Any, text: str) -> tuple[int, float]:
    if not engine.is_model_ready:
        raise RuntimeError("Mô hình VieNeu-TTS chưa sẵn sàng; smoke test không tải model.")
    voices = engine.voices()
    if not voices:
        raise RuntimeError("VieNeu-TTS không cung cấp giọng đọc nào.")
    voice = next((candidate for candidate in voices if candidate.id == "Adam"), voices[0])

    sample_count = 0
    peak = 0.0
    for chunk in engine.stream(text, voice.id):
        if (
            chunk.sample_rate != 48_000
            or chunk.channels != 1
            or chunk.sample_format != "float32"
            or len(chunk.pcm) % 4
        ):
            raise RuntimeError("VieNeu-TTS trả về định dạng âm thanh không hợp lệ.")
        for (sample,) in struct.iter_unpack("<f", chunk.pcm):
            if not math.isfinite(sample):
                raise RuntimeError("VieNeu-TTS trả về mẫu âm thanh không hữu hạn.")
            sample_count += 1
            peak = max(peak, abs(sample))

    if sample_count < 4_800 or peak <= 0.0001:
        raise RuntimeError("VieNeu-TTS không tạo đủ âm thanh nghe được từ nội dung sách.")
    return sample_count, peak


def _prove_figure_rendering(
    chapter: Any,
    chapter_presentation: Any,
    assets: dict[str, bytes],
) -> tuple[int, int, int]:
    """Render one real EPUB chapter at the supported minimum window size."""

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QAccessible, QTextFormat
    from PySide6.QtWidgets import QApplication

    from vieneu_reader.ui.book_reader_view import BookReaderView
    from vieneu_reader.ui.controller import ChapterItem, FigureItem, SegmentItem

    application = QApplication.instance() or QApplication([])
    view = BookReaderView()
    view.resize(900, 600)
    view.show()
    application.processEvents()
    view.render_chapters(
        (ChapterItem(chapter.id, chapter.title, chapter.ordinal),),
        chapter.id,
    )
    view.render_segments(
        tuple(
            SegmentItem(segment.id, segment.chapter_id, segment.ordinal, segment.text)
            for segment in chapter.segments
        ),
        chapter.segments[0].id,
        tuple(
            FigureItem(
                id=figure.id,
                number=figure.number,
                anchor_segment_id=figure.anchor_segment_id,
                placement=figure.placement,
                alt_text=figure.alt_text,
                alt_is_generic=figure.alt_is_generic,
                media_type=figure.media_type,
                width=figure.width,
                height=figure.height,
                image_bytes=assets.get(figure.asset_path),
            )
            for figure in chapter_presentation.figures
        ),
    )
    application.processEvents()
    application.processEvents()

    document = view.reader_text.document()
    image_widths: list[int] = []
    image_alts: list[str] = []
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid() and fragment.charFormat().isImageFormat():
                image_format = fragment.charFormat().toImageFormat()
                image_widths.append(round(image_format.width()))
                image_alts.append(
                    str(image_format.property(QTextFormat.Property.ImageAltText))
                )
            iterator += 1
        block = block.next()

    available_width = max(
        0,
        view.reader_text.viewport().width()
        - (2 * round(document.documentMargin()))
        - 4,
    )
    max_overflow = max(
        (max(0, width - available_width) for width in image_widths),
        default=0,
    )
    accessibility = QAccessible.queryAccessibleInterface(view.reader_text)
    accessible_description = (
        accessibility.text(QAccessible.Text.Description)
        if accessibility is not None
        else ""
    )
    useful_descriptions = tuple(
        figure.alt_text
        for figure in chapter_presentation.figures
        if figure.alt_text
        and not figure.alt_is_generic
        and figure.asset_path in assets
    )
    accessible_descriptions = sum(
        description in image_alts and description in accessible_description
        for description in useful_descriptions
    )
    view.close()
    application.processEvents()

    if assets and not image_widths:
        raise AssertionError("Chương có asset ảnh nhưng Qt không render được ảnh nào.")
    if max_overflow:
        raise AssertionError(
            f"Ảnh EPUB vượt vùng đọc ở cửa sổ 900×600: {max_overflow}px."
        )
    if accessible_descriptions != len(useful_descriptions):
        raise AssertionError("Mô tả ảnh EPUB chưa được expose đầy đủ cho trợ năng.")
    return len(image_widths), accessible_descriptions, max_overflow


def run_book_smoke(
    source: Path,
    app_root: Path,
    *,
    speech_engine_factory: Callable[[Path], Any] | None = None,
    models_path: Path | None = None,
) -> BookSmokeReceipt:
    """Exercise a caller-owned book in isolated app data without downloading."""

    source = Path(source).expanduser().resolve(strict=True)
    app_root = Path(app_root).expanduser().resolve()
    if app_root == default_app_root().resolve():
        raise ValueError("Smoke test phải dùng thư mục app-data cô lập.")
    if not source.is_file():
        raise ValueError("Đường dẫn sách phải là một tệp.")
    source_before = _file_sha256(source)

    paths = AppPaths.create(app_root)
    repository = LibraryRepository(paths.database)
    try:
        service = LibraryService(paths, repository)
        first = service.import_book(source)
        second = service.import_book(source)
        if first.was_existing or not second.was_existing:
            raise AssertionError("Import mới/trùng không trả đúng trạng thái.")
        if second.book != first.book or second.managed_path != first.managed_path:
            raise AssertionError("Import trùng không trỏ về cùng cuốn sách.")
        if repository.count_books() != 1:
            raise AssertionError("Import trùng tạo nhiều hơn một bản ghi sách.")
        if first.managed_path.parent != paths.books:
            raise AssertionError("Bản sao sách không nằm trong thư viện được quản lý.")
        if _file_sha256(first.managed_path) != source_before:
            raise AssertionError("Bản sao thư viện không còn giống tệp nguồn.")

        book = first.book
        payload_before = repository._connection.execute(
            "SELECT document_json FROM books WHERE id = ?",
            (book.id,),
        ).fetchone()["document_json"]
        presentation = service.presentation_for(book, first.managed_path)
        figures = tuple(
            figure
            for chapter in presentation.chapters
            for figure in chapter.figures
        )
        figure_chapter = next(
            (
                chapter
                for chapter in presentation.chapters
                if any(
                    figure.alt_text and not figure.alt_is_generic
                    for figure in chapter.figures
                )
            ),
            None,
        ) or next(
            (chapter for chapter in presentation.chapters if chapter.figures),
            None,
        )
        loaded_assets = (
            service.assets_for(
                book,
                first.managed_path,
                figure_chapter.figures,
            )
            if figure_chapter is not None
            else {}
        )
        rendered_figures = 0
        accessible_figure_descriptions = 0
        max_figure_overflow = 0
        if figure_chapter is not None:
            source_chapter = next(
                chapter
                for chapter in book.chapters
                if chapter.id == figure_chapter.chapter_id
            )
            (
                rendered_figures,
                accessible_figure_descriptions,
                max_figure_overflow,
            ) = _prove_figure_rendering(
                source_chapter,
                figure_chapter,
                loaded_assets,
            )
        from vieneu_reader.ui.controller import ReaderController

        speech_projection = ReaderController._speech_projection(book, presentation)
        figure_cues = sum(
            spoken.count("Mời bạn xem Hình")
            for spoken in speech_projection.values()
        )
        if figure_cues != len(figures):
            raise AssertionError("Số cue đọc hình không khớp thứ tự hình trong EPUB.")
        payload_after = repository._connection.execute(
            "SELECT document_json FROM books WHERE id = ?",
            (book.id,),
        ).fetchone()["document_json"]
        document_payload_unchanged = payload_before == payload_after
        if not document_payload_unchanged:
            raise AssertionError("Trình bày hình ảnh đã ghi đè dữ liệu sách.")
        target = book.chapters[-1].segments[-1]
        progress = Progress(
            book_id=book.id,
            segment_id=target.id,
            playback_rate=1.0,
            voice_id="Adam",
        )
        repository.save_active_book_id(book.id)
        repository.save_progress(progress)
    finally:
        repository.close()

    restarted = LibraryRepository(paths.database)
    try:
        restored_progress = (
            restarted.load_active_book_id() == book.id
            and restarted.load_progress(book.id) == progress
            and restarted.count_books() == 1
        )
        if not restored_progress:
            raise AssertionError("Tiến độ đọc không khôi phục sau khi mở lại kho dữ liệu.")
    finally:
        restarted.close()

    if _file_sha256(source) != source_before:
        raise AssertionError("Smoke test đã làm thay đổi tệp sách của người dùng.")

    audio_samples = 0
    audio_peak = 0.0
    if speech_engine_factory is not None:
        if models_path is None:
            raise ValueError("Cần models_path khi bật kiểm tra VieNeu-TTS.")
        text = next(
            (
                spoken
                for spoken in speech_projection.values()
                if "Mời bạn xem Hình" in spoken
            ),
            next(
                segment.text
                for chapter in book.chapters
                for segment in chapter.segments
                if segment.text.strip()
            ),
        )
        engine = speech_engine_factory(Path(models_path))
        audio_samples, audio_peak = _prove_audio(engine, text)

    return BookSmokeReceipt(
        source_format=book.source_format,
        chapters=len(book.chapters),
        segments=sum(len(chapter.segments) for chapter in book.chapters),
        characters=sum(
            len(segment.text)
            for chapter in book.chapters
            for segment in chapter.segments
        ),
        duplicate_detected=second.was_existing,
        restored_progress=restored_progress,
        figures=len(figures),
        loaded_figure_assets=len(loaded_assets),
        rendered_figures=rendered_figures,
        accessible_figure_descriptions=accessible_figure_descriptions,
        max_figure_overflow=max_figure_overflow,
        figure_cues=figure_cues,
        document_payload_unchanged=document_payload_unchanged,
        audio_samples=audio_samples,
        audio_peak=audio_peak,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Kiểm tra một sách thật bằng dữ liệu app cô lập."
    )
    parser.add_argument("book", type=Path, help="Đường dẫn tệp EPUB hoặc PDF")
    parser.add_argument(
        "--real-tts",
        action="store_true",
        help="Tạo âm thanh thật bằng model VieNeu-TTS đã chuẩn bị sẵn",
    )
    arguments = parser.parse_args(argv)

    speech_engine_factory = None
    models_path = None
    if arguments.real_tts:
        from vieneu_reader.speech.vieneu import VieNeuSpeechEngine

        speech_engine_factory = VieNeuSpeechEngine
        models_path = default_app_root() / "Models"

    with TemporaryDirectory(prefix="vieneu-real-book-smoke-") as directory:
        receipt = run_book_smoke(
            arguments.book,
            Path(directory) / "app-data",
            speech_engine_factory=speech_engine_factory,
            models_path=models_path,
        )
    print(
        "REAL_BOOK_SMOKE PASS "
        f"format={receipt.source_format} "
        f"chapters={receipt.chapters} "
        f"segments={receipt.segments} "
        f"characters={receipt.characters} "
        f"duplicate={int(receipt.duplicate_detected)} "
        f"restore={int(receipt.restored_progress)} "
        f"figures={receipt.figures} "
        f"loaded_figure_assets={receipt.loaded_figure_assets} "
        f"rendered_figures={receipt.rendered_figures} "
        f"accessible_figure_descriptions={receipt.accessible_figure_descriptions} "
        f"max_figure_overflow={receipt.max_figure_overflow} "
        f"figure_cues={receipt.figure_cues} "
        f"document_payload_unchanged={int(receipt.document_payload_unchanged)} "
        f"audio_samples={receipt.audio_samples} "
        f"audio_peak={receipt.audio_peak:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
