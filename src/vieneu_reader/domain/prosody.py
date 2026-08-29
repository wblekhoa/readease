"""Structure-aware pauses and speech-text shaping for natural reading.

Every duration here is the silence ReadEase itself injects at a boundary,
on top of the roughly 250-400 ms the voice already leaves at the seams of
two synthesized clips. Injected silence rides through the playback
time-stretcher, so at faster reading rates every pause shortens with the
speech.
"""

from __future__ import annotations

import re

from vieneu_reader.domain.models import Segment, SegmentJoint

SENTENCE_ENDINGS = frozenset(".!?…")
_TRAILING_CLOSERS = frozenset("\"'”’»›)]}")
_BULLET_GLYPHS = frozenset("•◦▪●‣·*")

CHAPTER_PAUSE_MS = 1200
LINE_PAUSE_MS = 250
# One sentence to the next inside a paragraph. The voice is asked to read each
# sentence on its own, which leaves about 260 ms at the seam by itself; this
# tops it up to something the ear reads as a full stop without turning it into
# a paragraph break.
SENTENCE_PAUSE_MS = 100
BLOCK_PAUSE_MS = 450

# Pauses inside a segment are baked into the audio that gets cached, so the
# cache has to know which reading produced it. Deriving this from the pause
# itself means tuning the pause re-renders exactly what it invalidates.
READING_REVISION = f"sentences-{SENTENCE_PAUSE_MS}"

# A terminal mark, any closing quotes or brackets, then the gap before whatever
# comes next.
_SENTENCE_BOUNDARY = re.compile(r"[.!?…]+[\"\'”’»›)\]}]*\s+")
_SENTENCE_OPENERS = frozenset("(\"'“‘«[-—–")
# Titles and initials end in a period and are followed by a capitalised name,
# which is exactly what a sentence boundary looks like.
_ABBREVIATIONS = frozenset(
    {
        "tp", "ts", "gs", "pgs", "ths", "th", "bs", "ks", "cn", "đh", "cđ",
        "vs", "vd", "tr", "st", "mr", "mrs", "ms", "dr", "prof", "no",
    }
)

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
    return SENTENCE_PAUSE_MS if ends_sentence(previous_text) else 0


def _opens_a_sentence(character: str) -> bool:
    return (
        character.isupper()
        or character.isdigit()
        or character in _SENTENCE_OPENERS
    )


def _is_abbreviation(text: str, mark_index: int) -> bool:
    cursor = mark_index
    while cursor > 0 and (text[cursor - 1].isalnum() or text[cursor - 1] == "."):
        cursor -= 1
    token = text[cursor:mark_index]
    letters = token.replace(".", "")
    if not letters:
        return False
    if len(letters) == 1 and letters.isalpha():
        # An initial, as in "T. P. Hồ Chí Minh".
        return True
    return letters.lower() in _ABBREVIATIONS


def split_sentences(text: str) -> tuple[str, ...]:
    """Split one paragraph into the sentences the voice should read apart.

    A period is only a boundary when what follows could start a sentence and
    what precedes it is not a title or an initial; anything less careful puts
    a silence in the middle of "TS. Nguyễn Văn A".
    """

    sentences: list[str] = []
    start = 0
    for match in _SENTENCE_BOUNDARY.finditer(text):
        following = match.end()
        if following >= len(text):
            break
        if not _opens_a_sentence(text[following]):
            continue
        if _is_abbreviation(text, match.start()):
            continue
        piece = text[start:following].strip()
        if piece:
            sentences.append(piece)
            start = following
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return tuple(sentences)


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
