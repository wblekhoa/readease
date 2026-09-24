"""What a reading is made of: the utterances, the cues and the rests.

Lifted out of `server.py` (22/09) unchanged. These are pure functions over a
document - they take text, segments, figures and notes, and return the exact
sequence the voice will speak. They belong together because two callers need
the SAME answer: the reading itself, and the estimate that prices it and says
how long it will take. A second builder would be a second truth, and the day
they disagreed the bill would be wrong.

Nothing here talks to the engine, the protocol or the shell. The names keep
their leading underscore: they are this package's own, not an API, and
`server.py` re-exports them so the tests that reach for them still find them
where they were.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from vieneu_reader.domain.presentation import figure_label
from vieneu_reader.domain.prosody import (
    DEFAULT_NOTE_READING,
    DEFAULT_SPEECH_LANGUAGE,
    pause_after_ms,
    selection_pause_ms,
    speak_with_notes,
    speakable_text,
    spoken_note,
)
from vieneu_reader.domain.segmenter import split_transient_parts
from vieneu_reader.playback.time_stretch import SAMPLE_RATE
from vieneu_reader.speech.contracts import SynthesisSettings

def _text_utterances(
    text: str,
    settings: SynthesisSettings,
    language: str = DEFAULT_SPEECH_LANGUAGE,
    note_reading: str = DEFAULT_NOTE_READING,
) -> list[_Utterance]:
    """Pasted or captured text, shaped exactly as the reading will send it.

    ONE builder, two callers - the reading and the estimate that prices it,
    the same rule a book's utterances follow. Counting `text` itself would
    quote a number the bill then disagrees with: `speakable_text` lowers
    shouted runs and rewrites ordinals on the way past.

    Each part is addressable, exactly as a book's segments are. Nothing is
    stored for a plain read (no book_id reaches `_speak`, so no progress
    row) - the id exists so a reading can be RESUMED at the part it had
    reached, which is what changing the voice mid-way does.
    """

    parts = split_transient_parts(text, settings.max_chars)
    if not parts:
        return []
    spoken = tuple(
        speakable_text(part.text, language=language, citations=note_reading != "full")
        for part in parts
    )
    return [
        _Utterance(
            text=spoken[index],
            pause_after_ms=(
                selection_pause_ms(spoken[index], parts[index + 1].joint)
                if index + 1 < len(parts)
                else 0
            ),
            segment_id=f"part-{index}",
            source=parts[index].text,
        )
        for index in range(len(parts))
    ]


def _start_at(
    utterances: "list[_Utterance]",
    wanted: object,
    order: "list[str] | None" = None,
) -> int:
    """Where a resume lands: the first thing said ABOUT that segment.

    Which may be the cue for a picture placed before it, not the paragraph.

    Some segments say nothing of their own - a footnote whose words were
    already read at the sentence that referenced it. Pointing at one has to
    carry on from the next thing that DOES speak: falling back to 0, as this
    did for anything it could not find, would silently restart the book from
    the beginning under a finger that meant "read from here".
    """

    if not wanted:
        return 0
    for index, utterance in enumerate(utterances):
        if utterance.segment_id == wanted:
            return index
    if not order or str(wanted) not in order:
        return 0
    speaks = {utterance.segment_id for utterance in utterances}
    for later in order[order.index(str(wanted)) + 1:]:
        if later in speaks:
            return next(
                index
                for index, utterance in enumerate(utterances)
                if utterance.segment_id == later
            )
    # Nothing after it has anything to say: the reading is over, which is
    # the truth, and not the top of the book.
    return len(utterances)


def _reading_order(book: Any) -> list[str]:
    """Every segment id, in the order the book reads."""

    return [
        segment.id for chapter in book.chapters for segment in chapter.segments
    ]


def _silence(milliseconds: int) -> bytes:
    samples = SAMPLE_RATE * milliseconds // 1000
    return np.zeros(samples, dtype=np.float32).tobytes()


@dataclass(frozen=True)
class _Utterance:
    """One thing to speak, the rest that follows it, and where it lives."""

    text: str
    pause_after_ms: int
    segment_id: str | None = None
    # The same words as WRITTEN. `text` is what the voice says, and
    # `speakable_text` has already been past it - shouted runs lowered,
    # ordinals rewritten - so it is the wrong thing to show a reader who
    # wants to see what was captured. A book hands its own text to the
    # shell through `book.open`; a plain read had no such door until
    # `text.parts` (09/09), and this field is what that door returns.
    source: str = ""
    # What kind of block the words came from - a heading is read set apart
    # (slower, louder, HEADING_RATE/HEADING_GAIN); everything else reads as
    # a paragraph. Cues and notes are paragraphs.
    kind: str = "paragraph"
    # What this utterance opens, on the first utterance of the passage the
    # book's division plan names (`domain.divisions`, HIG 5.1): "part" or
    # "chapter" - the chime, if one is chosen, sounds before it - or
    # "part-chapter", the chapter right after its part's title, which gets a
    # rest and no second sound. None for everything else, a new FILE
    # included: a file is not a chapter.
    opens: str | None = None
    # Set on the spoken cue for a picture ("Xem hình 3."): rides the position
    # event so the shell can bring the picture into view exactly when the ear
    # hears the cue, not when the model synthesised it.
    figure_id: str | None = None


# What the voice says when the reading reaches a picture, and the rest that
# follows so the listener has a beat to look. In the language being READ: this
# sentence is spoken aloud between two sentences of the book, so a Vietnamese
# one in the middle of an English chapter is a stumble, not a label.
FIGURE_CUE = {
    "vi": "Xem hình {number}.",
    "en": "See figure {number}.",
}
FIGURE_CUE_PAUSE_MS = 600

# What the voice says before a footnote, and the beat after it. On paper a
# small number sends the eye down the page and back; an ear has no such move,
# so the note is read where it belongs - after the sentence that carries the
# number - and it has to be ANNOUNCED, or it arrives as a non-sequitur in the
# middle of a paragraph. Two words, because a longer preamble said before
# eighty notes becomes the thing you hear instead of the notes (owner,
# 04/09: "nói thêm").
NOTE_CUE = {
    "vi": "Nói thêm, {text}",
    "en": "Also, {text}",
}
NOTE_CUE_PAUSE_MS = 450

# Around the chime that opens a chapter (owner, 16/09): the previous
# chapter's last words settle, the chime, then a breath before the title.
# Together with a 0.9-2.0 s chime this replaces the 1.2 s of plain silence
# a chapter boundary used to get; with the chime off, the silence stays.
CHIME_LEAD_MS = 300
CHIME_TAIL_MS = 500


@dataclass(frozen=True)
class _FigureCue:
    placement: str
    figure_id: str
    #: What the voice says: the book's own number ("1.3") when the caption
    #: or alt carries one, else the figure's count within its chapter.
    number: str
    #: The segment that captions this figure, if the book gave it one. The
    #: caption is then the announcement - no "Xem hình" on top of it.
    caption_segment_id: str | None


def _figure_cues(presentation: Any) -> dict[str, list[_FigureCue]]:
    """Per anchor segment, the figures announced there.

    Numbered per CHAPTER, not per book: the domain's running count is right
    for a print index, but "Xem hình 187" is not something a listener can
    hold in their head, and "Xem hình 3" is (owner's call, 2026-09-02). A
    book that numbers its own figures wins over both: "Xem hình 1.3" is
    what the text beside it says (owner, 05/09).
    """
    cues: dict[str, list[_FigureCue]] = {}
    for chapter in presentation.chapters:
        for figure, number in _figure_numbers(chapter.figures):
            if figure.duplicate_of is not None:
                # A translated copy of the picture just announced. The page
                # shows it; the voice has nothing new to say about it.
                continue
            labelled = figure_label(figure.label)
            cues.setdefault(figure.anchor_segment_id, []).append(_FigureCue(
                placement=figure.placement,
                figure_id=figure.id,
                number=labelled[1] if labelled else str(number),
                caption_segment_id=figure.caption_segment_id,
            ))
    return cues


def _figure_numbers(figures: Any) -> list[tuple[Any, int]]:
    """Each figure with its number within the chapter; a copy shares the
    number of the picture it repeats, so the page and the voice agree."""
    numbered: list[tuple[Any, int]] = []
    by_id: dict[str, int] = {}
    count = 0
    for figure in figures:
        if figure.duplicate_of is not None and figure.duplicate_of in by_id:
            number = by_id[figure.duplicate_of]
        else:
            count += 1
            number = count
        by_id[figure.id] = number
        numbered.append((figure, number))
    return numbered


def _note_marks(presentation: Any) -> dict[str, list[tuple[int, int, str]]]:
    """Per anchor segment: (offset, label length, the note's own words).

    Ordered by where the number falls, because that is the order the page
    prints them in and the order a listener has to hear them.
    """

    marks: dict[str, list[tuple[int, int, str]]] = {}
    for chapter in presentation.chapters:
        for note in getattr(chapter, "notes", ()):
            marks.setdefault(note.anchor_segment_id, []).append(
                (note.offset, note.length, note.text)
            )
    for found in marks.values():
        found.sort()
    return marks
