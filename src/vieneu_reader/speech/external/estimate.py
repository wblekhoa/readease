"""How much of the book is about to be sent, and what that costs.

The read button carries the figure and stays disabled until it has one
(owner, 04/09), so this has to be exact rather than indicative - and it can
be: a paid voice bills by the character, and the whole text is already on
this machine. No sampling, no guessing, no request.

Exactness has one condition, which is the reason this module takes the
utterances rather than the book: the count must be over the SAME strings the
engine will send. That is `speakable_text()` applied to each segment plus the
spoken picture cues ("Xem hình 3."), not the segment text as displayed. The
server builds that list once, for both this and the reading itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .pricing import PRICES_FETCHED, VoicePrice


@dataclass(frozen=True, slots=True)
class ScopeEstimate:
    """What one press of the button would buy."""

    chars: int
    utterances: int
    chapters: int
    usd: float
    units: int
    unit: str
    price_dated: str = PRICES_FETCHED


def scope_end(chapter_of: Sequence[int], start: int, chapters: int | None) -> int:
    """One past the last utterance inside the chosen scope.

    `chapters=None` reads to the end of the book. `chapters=1` reads to the
    end of the chapter the start sits in - not "one chapter's worth from
    here", because a reader who resumes three paragraphs from the end of
    chapter two and asks for "chương này" means those three paragraphs.
    """

    total = len(chapter_of)
    if start >= total:
        return total
    if chapters is None:
        return total
    if chapters < 1:
        return start
    last_wanted = chapter_of[start] + chapters - 1
    end = start
    while end < total and chapter_of[end] <= last_wanted:
        end += 1
    return end


def scope_start(chapter_of: Sequence[int], start: int, chapters: int | None) -> int:
    """The earliest utterance a reading inside this scope could begin at.

    The price on the button is a CEILING, not the cost of one particular
    press (owner, 04/09). A person does not only press the button - they
    click a paragraph, and a click carries the same scope, so clicking back
    at the top of the chapter they are halfway through costs several times
    what resuming would. Measured on a ten-paragraph chapter: $0.018 from the
    last paragraph, $0.180 from the first - the same scope, ten times the
    money, and only one of those numbers was ever shown.

    Quoting from the scope's own start makes the figure true for every way
    of starting a reading inside it. It overstates a resume near the end,
    which is the safe direction to be wrong in.
    """

    if chapters is None:
        return 0
    if not chapter_of or start >= len(chapter_of):
        return start
    here = chapter_of[start]
    first = start
    while first > 0 and chapter_of[first - 1] == here:
        first -= 1
    return first


def estimate_scope(
    texts: Sequence[str],
    chapter_of: Sequence[int],
    start: int,
    chapters: int | None,
    price: VoicePrice,
) -> ScopeEstimate:
    if len(texts) != len(chapter_of):
        raise ValueError("one chapter index per utterance")
    end = scope_end(chapter_of, start, chapters)
    window = texts[start:end]
    chars = sum(len(text) for text in window)
    return ScopeEstimate(
        chars=chars,
        utterances=len(window),
        chapters=len(set(chapter_of[start:end])),
        usd=round(price.usd_for(chars), 4),
        units=price.units_for(chars),
        unit=price.unit,
    )
