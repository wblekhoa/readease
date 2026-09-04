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
class NoteRef:
    """A footnote, and the exact place in the reading it belongs to.

    A note is written for the eye: the page prints a small number, and the
    reader's eye goes down or across when it wants to. An ear has no such
    move - read as a chapter of its own at the back of the book, eighty
    notes arrive detached from every sentence that needed them, and read as
    a bare "sáu" in the middle of a paragraph the number is worse than
    nothing. So the note is carried WITH its anchor: which segment holds the
    reference, and where in that segment's text the number sits.

    `offset` is into the stored segment text, so the reading can finish the
    sentence the number belongs to before saying the note out loud.
    """

    id: str
    #: What the page prints - "6". Kept so the voice can leave it out.
    label: str
    chapter_id: str
    anchor_segment_id: str
    #: Where the label starts in that segment's text.
    offset: int
    #: How many characters the label takes there.
    length: int
    #: The note itself, with its own number and its way-back link removed.
    text: str


@dataclass(frozen=True, slots=True)
class ChapterPresentation:
    chapter_id: str
    figures: tuple[FigureRef, ...] = ()
    notes: tuple[NoteRef, ...] = ()
    #: Segments whose words the voice has already said, as a footnote, at
    #: the sentence that referenced them - the endnotes at the back, or the
    #: small print at the foot of the chapter. They stay on the page and
    #: keep their place in the book; the reading just does not say them
    #: twice.
    spoken_elsewhere: tuple[str, ...] = ()


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
