"""Content patterns a book's markup leaves behind, found once, used twice.

Translated EPUBs (BookStudio and friends) carry structure the eye skips and
the ear cannot: a picture and its translated copy one after the other, an
"image annotation" paragraph under each, a caption that repeats the alt, a
diagram whose labels fell out as one-word paragraphs. Read aloud naively,
each becomes a repeated announcement or a stray word.

This module names those patterns as typed findings. Two callers read them:
the audit script (`scripts/audit-book-content.py`), which counts them over
a library so a pattern earns a rule with numbers rather than one screenshot;
and the reading engine, which acts on the kinds marked as RULES. Kinds
marked REPORT are counted only - the data decides whether they graduate
(owner, 05/09: "phân tích … tự động detect những pattern nội dung có vấn đề
để từ đó xây dựng luật").

Measured over the owner's nine books before any rule was written:
- Translated copies are class-marked (`bs-localized-image`,
  `bs-image-companion`); alt-equality is NOT a safe signal - 154 of Krug's
  195 alts are "Image", and two DIFFERENT figures often sit side by side
  with only a caption between them. So the duplicate rule is by class.
- "Chú giải ảnh:" runs 8-110 per book and is the only description a
  listener gets of the picture. It stays spoken, once. Report only.
- One-word blocks before a figure are mostly author names; the one real
  diagram-label case does not justify a rule. Report only.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Literal

from vieneu_reader.domain.models import BookDocument, Chapter, Segment
from vieneu_reader.domain.presentation import figure_label

#: A translator's description of a picture. Matcher data for book text;
#: nothing here is shown to anyone.
_IMAGE_ANNOTATION = re.compile(
    r"^\s*(chú giải ảnh|mô tả ảnh|image description)\s*:", re.IGNORECASE
)
#: "(xem Hình 1.3)" - prose pointing at a figure by the book's own number.
_FIGURE_REFERENCE = re.compile(
    r"\(\s*(?:xem\s+)?(?:hình|ảnh|minh họa|figure|fig\.?)\s*"
    r"(\d+(?:[.\-–]\d+)*[a-z]?)\s*\)",
    re.IGNORECASE,
)

Kind = Literal[
    # RULES - the engine acts on these.
    "figure_duplicate",
    # REPORTS - counted, not acted on, until the numbers say otherwise.
    "short_block_before_figure",
    "image_annotation",
    "alt_equals_caption",
    "generic_alt",
    "uncaptioned_figure",
    "dangling_figure_reference",
]

RULES: frozenset[str] = frozenset({"figure_duplicate"})


@dataclass(frozen=True, slots=True)
class Finding:
    kind: Kind
    chapter_id: str
    #: The figure this is about, when it is about one.
    figure_id: str | None
    #: The segments involved, in order.
    segment_ids: tuple[str, ...]
    #: A short, human-readable specimen - the text or label in question.
    detail: str

    @property
    def is_rule(self) -> bool:
        return self.kind in RULES


def is_image_annotation(text: str) -> bool:
    return _IMAGE_ANNOTATION.match(text) is not None


def is_short_block(segment: Segment, max_words: int = 3) -> bool:
    """A block too short to be prose and not closed like a sentence."""
    text = segment.text.strip()
    return (
        0 < len(text.split()) <= max_words
        and not text.endswith((".", "!", "?", ":", ";"))
        and segment.kind in ("paragraph", "quote")
    )


def figure_references(text: str) -> list[str]:
    return [match.group(1) for match in _FIGURE_REFERENCE.finditer(text)]


def audit_chapter(chapter: Chapter, figures: Iterable[Any]) -> list[Finding]:
    """Every finding in one chapter. `figures` are its FigureRefs."""
    findings: list[Finding] = []
    segments = chapter.segments
    index = {segment.id: position for position, segment in enumerate(segments)}
    by_id = {segment.id: segment for segment in segments}
    for figure in figures:
        anchor = index.get(figure.anchor_segment_id)
        if anchor is None:
            continue
        caption = by_id.get(figure.caption_segment_id) if figure.caption_segment_id else None
        if figure.duplicate_of is not None:
            # Everything else about a copy is the original's (caption, alt,
            # what sits above and below it); counting it twice would be
            # counting the same picture twice.
            findings.append(Finding(
                "figure_duplicate", chapter.id, figure.id, (),
                f"repeats {figure.duplicate_of}",
            ))
            continue
        if caption is None:
            findings.append(Finding(
                "uncaptioned_figure", chapter.id, figure.id, (), figure.alt_text or "",
            ))
        elif figure.alt_text and figure.alt_text.strip() == caption.text.strip():
            findings.append(Finding(
                "alt_equals_caption", chapter.id, figure.id, (caption.id,),
                caption.text[:80],
            ))
        if figure.alt_is_generic:
            findings.append(Finding(
                "generic_alt", chapter.id, figure.id, (), figure.alt_text or "",
            ))
        # A run of short blocks right above the picture (walking up from the
        # anchor; the caption is not part of it).
        run: list[Segment] = []
        position = anchor
        while position >= 0:
            candidate = segments[position]
            if candidate is caption or not is_short_block(candidate):
                break
            run.insert(0, candidate)
            position -= 1
        if run:
            findings.append(Finding(
                "short_block_before_figure", chapter.id, figure.id,
                tuple(segment.id for segment in run),
                " | ".join(segment.text for segment in run),
            ))
        # The translator's description right after the caption (or picture).
        after = (index[caption.id] if caption is not None else anchor) + 1
        if after < len(segments) and is_image_annotation(segments[after].text):
            findings.append(Finding(
                "image_annotation", chapter.id, figure.id, (segments[after].id,),
                segments[after].text[:80],
            ))
    return findings


def audit_book(book: BookDocument, presentation: Any) -> list[Finding]:
    """Every finding in a book, chapter findings first, then book-wide ones."""
    findings: list[Finding] = []
    labels: set[str] = set()
    for chapter in book.chapters:
        shown = presentation.chapter(chapter.id)
        figures = tuple(shown.figures) if shown is not None else ()
        findings.extend(audit_chapter(chapter, figures))
        for figure in figures:
            labelled = figure_label(figure.label)
            if labelled is not None:
                labels.add(labelled[1])
    if labels:
        # Only a book that numbers its figures can have a reference to one
        # that is missing; in an unnumbered book "(xem hình 3)" is prose.
        for chapter in book.chapters:
            for segment in chapter.segments:
                for number in figure_references(segment.text):
                    if number not in labels:
                        findings.append(Finding(
                            "dangling_figure_reference", chapter.id, None,
                            (segment.id,), number,
                        ))
    return findings
