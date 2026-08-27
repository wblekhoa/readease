"""Transient EPUB presentation metadata derived from an immutable book source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class FigureRef:
    id: str
    number: int
    chapter_id: str
    source_occurrence: int
    anchor_segment_id: str
    placement: Literal["before", "after"]
    asset_path: str
    media_type: str
    alt_text: str | None
    alt_is_generic: bool
    width: int | None
    height: int | None


@dataclass(frozen=True, slots=True)
class ChapterPresentation:
    chapter_id: str
    figures: tuple[FigureRef, ...] = ()


@dataclass(frozen=True, slots=True)
class BookPresentation:
    book_id: str
    source_hash: str
    chapters: tuple[ChapterPresentation, ...] = ()

    def chapter(self, chapter_id: str) -> ChapterPresentation | None:
        return next(
            (chapter for chapter in self.chapters if chapter.chapter_id == chapter_id),
            None,
        )

    @classmethod
    def empty(cls, book_id: str, source_hash: str) -> "BookPresentation":
        return cls(book_id=book_id, source_hash=source_hash)
