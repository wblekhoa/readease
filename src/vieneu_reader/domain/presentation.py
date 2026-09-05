"""Transient EPUB presentation metadata derived from an immutable book source."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

#: A caption (or alt) that opens with the book's own figure label: "Hình
#: 1.1.", "Ảnh 3 -", "Minh họa 11", "Figure 2-4", "Fig. 7". The number is
#: mandatory, or "Hình ảnh này…" would pass. Separators inside the number
#: are what print uses: 1.3, 2-4, 2–4.
_FIGURE_LABEL = re.compile(
    r"^\s*(hình|ảnh|minh họa|figure|fig\.?)\s*(\d+(?:[.\-–]\d+)*[a-z]?)(?!\w)",
    re.IGNORECASE,
)


def figure_label(text: str | None) -> tuple[str, str] | None:
    """The book's own label at the start of `text`, as (label, number).

    "Hình 1.1. Trải nghiệm…" → ("Hình 1.1", "1.1"). None when the text does
    not open with one. A book that numbers its figures is telling the reader
    what to call them; the shell and the voice should not invent a second
    numbering beside it.
    """
    match = _FIGURE_LABEL.match(text or "")
    if match is None:
        return None
    word, number = match.group(1), match.group(2)
    # Keep the book's word as written, minus a trailing period on "Fig.".
    return f"{word.rstrip('.')} {number}", number


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
    #: The book's own label for this figure ("Hình 1.1"), read off its
    #: caption or alt. None when the book does not number it, and the
    #: shell counts per chapter instead.
    label: str | None = None
    #: The segment that IS this figure's caption - the figcaption beside
    #: it, or a paragraph opening with its label. The voice reads that
    #: caption as the figure's announcement instead of saying "Xem hình".
    caption_segment_id: str | None = None
    #: The figure this one repeats: a translated copy of the picture right
    #: before it (BookStudio's `bs-localized-image`), separated only by the
    #: caption or an annotation. The page shows both, so a reader can
    #: compare; the voice announces the picture once and numbers it once.
    duplicate_of: str | None = None


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
