"""Structure-aware pauses and speech-text shaping for natural reading.

Every duration here is the silence ReadEase itself injects at a boundary,
on top of the roughly 250-400 ms the voice already leaves at the seams of
two synthesized clips. Injected silence rides through the playback
time-stretcher, so at faster reading rates every pause shortens with the
speech.
"""

from __future__ import annotations

from vieneu_reader.domain.models import Segment, SegmentJoint

SENTENCE_ENDINGS = frozenset(".!?…")
_TRAILING_CLOSERS = frozenset("\"'”’»›)]}")
_BULLET_GLYPHS = frozenset("•◦▪●‣·*")

CHAPTER_PAUSE_MS = 1200
LINE_PAUSE_MS = 250
SENTENCE_SPLIT_PAUSE_MS = 150
BLOCK_PAUSE_MS = 450

_AFTER_KIND_MS = {
    "heading": 700,
    "paragraph": BLOCK_PAUSE_MS,
    "list_item": 300,
    "quote": 550,
    "caption": BLOCK_PAUSE_MS,
    "preformatted": BLOCK_PAUSE_MS,
}
_BEFORE_KIND_MS = {
    "heading": 800,
    "paragraph": 0,
    "list_item": 300,
    "quote": 550,
    "caption": 0,
    "preformatted": 0,
}


def final_punctuation(text: str) -> str:
    """Return the closing punctuation mark, looking through quote closers."""

    for character in reversed(text):
        if character in _TRAILING_CLOSERS or character.isspace():
            continue
        if character in SENTENCE_ENDINGS or character in ",;:":
            return character
        return ""
    return ""


def ends_sentence(text: str) -> bool:
    return final_punctuation(text) in SENTENCE_ENDINGS


def _split_pause_ms(previous_text: str) -> int:
    return SENTENCE_SPLIT_PAUSE_MS if ends_sentence(previous_text) else 0


def _block_pause_ms(current_kind: str, next_kind: str) -> int:
    after = _AFTER_KIND_MS[current_kind]
    if current_kind == "list_item" and next_kind != "list_item":
        # Leaving a list closes a block, not just one more item.
        after = _AFTER_KIND_MS["paragraph"]
    return max(after, _BEFORE_KIND_MS[next_kind])


def pause_after_ms(current: Segment, next_segment: Segment | None) -> int:
    """Silence to add between one segment's audio and the next one's."""

    if next_segment is None:
        return 0
    if next_segment.chapter_id != current.chapter_id:
        return CHAPTER_PAUSE_MS
    if next_segment.joint == "split":
        return _split_pause_ms(current.text)
    if next_segment.joint == "line":
        return LINE_PAUSE_MS
    return _block_pause_ms(current.kind, next_segment.kind)


def selection_pause_ms(previous_text: str, next_joint: SegmentJoint) -> int:
    """Silence between two parts of transient text (paste, selection)."""

    if next_joint == "split":
        return _split_pause_ms(previous_text)
    if next_joint == "line":
        return LINE_PAUSE_MS
    return BLOCK_PAUSE_MS


def speakable_text(text: str, kind: str = "paragraph") -> str:
    """Shape one segment's text for the voice without touching the display.

    Bullet glyphs derail the voice (one probe read two words for four
    seconds), so they are dropped; a heading left without any terminal
    punctuation tends to end mid-air, so it is spoken with a final period.
    """

    spoken = text
    stripped = spoken.lstrip()
    while stripped and stripped[0] in _BULLET_GLYPHS:
        stripped = stripped[1:].lstrip()
    if stripped:
        spoken = stripped
    if kind == "heading" and not final_punctuation(spoken):
        spoken = f"{spoken}."
    return spoken
