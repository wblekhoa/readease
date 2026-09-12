"""Which language a book is written in, read off the book itself.

The voice has to know this before it opens its mouth: VieNeu is a Vietnamese
model and must never be handed another language (owner, 07/09/2026), and every
transform that turns writing into WORDS - numbers, Roman numerals, the word for
a dot in a web address - answers differently per language.

Asking the reader would be one more question at exactly the wrong moment, and
asking the FILE is unreliable: EPUB carries `dc:language`, PDF carries nothing
worth trusting, and both are wrong often enough that a book would end up read
in a language nobody chose. The text itself is the one witness that is always
present.

The signal is Vietnamese orthography, which English does not have: the letters
ăâđêôơư and the five tone marks. Measured on constructed samples (2026-09-07):

    Vietnamese prose                 28%
    Vietnamese with English terms    12%
    English with Vietnamese names     6% in one short sentence, far less
                                        across a whole book
    English                           0%

so the threshold sits at 5% - an order of magnitude below any Vietnamese text
and above what proper nouns can reach once a real book's worth of characters
is counted.
"""

from __future__ import annotations

import unicodedata
from typing import Iterable, Sequence

from .prosody import DEFAULT_SPEECH_LANGUAGE, SPEECH_LANGUAGES, speech_language


#: Letters only Vietnamese uses, before any tone mark is applied.
_VIETNAMESE_LETTERS = frozenset("ăâđêôơưĂÂĐÊÔƠƯ")
#: The five tone marks, as combining characters after NFD.
_TONE_MARKS = frozenset("̣̀́̃̉")
#: Above this share of marked letters, the text is Vietnamese.
VIETNAMESE_THRESHOLD = 0.05
#: How much text to look at. Enough that a title page, an English epigraph or a
#: bibliography cannot decide the whole book; small enough to cost nothing.
SAMPLE_LETTERS = 20_000
#: How many places in the book to look at. Spread from first segment to last,
#: so the sample is of the BOOK and not of its opening pages.
SAMPLE_PARTS = 200


def vietnamese_share(text: str) -> float:
    """Share of letters carrying Vietnamese orthography, 0.0 for none."""

    letters = marked = 0
    for character in text:
        if not character.isalpha():
            continue
        letters += 1
        if character in _VIETNAMESE_LETTERS:
            marked += 1
            continue
        decomposed = unicodedata.normalize("NFD", character)
        if len(decomposed) > 1 and any(part in _TONE_MARKS for part in decomposed):
            marked += 1
    return marked / letters if letters else 0.0


def language_of_text(
    text: str, fallback: str = DEFAULT_SPEECH_LANGUAGE
) -> str:
    """The language `text` is written in, or `fallback` when it says nothing.

    A short or letterless string - a page number, a caption of digits - is not
    evidence of anything, so it falls back rather than guessing.
    """

    if sum(1 for character in text if character.isalpha()) < 20:
        return speech_language(fallback)
    return "vi" if vietnamese_share(text) >= VIETNAMESE_THRESHOLD else "en"


def language_of_texts(
    texts: Iterable[str] | Sequence[str], fallback: str = DEFAULT_SPEECH_LANGUAGE
) -> str:
    """The language of a whole book, from a sample spread across it.

    Spread rather than the first chapter: books open with title pages,
    dedications and English epigraphs, and a Vietnamese book has been known to
    put its whole abstract in English before the first sentence of its own.
    """

    parts = [text for text in texts if text and text.strip()]
    if not parts:
        return speech_language(fallback)
    # Evenly spaced parts, each TRUNCATED to its share of the budget. Reading
    # whole parts until the budget ran out only ever sampled the front of the
    # book, which is the one place the docstring above says not to trust: a
    # book with an English first act and a Vietnamese body came back English.
    step = max(1, len(parts) // SAMPLE_PARTS)
    chosen = parts[::step][:SAMPLE_PARTS]
    per_part = max(40, SAMPLE_LETTERS // len(chosen))
    sample = " ".join(part[:per_part] for part in chosen)
    return language_of_text(sample, fallback)


def language_in_use(chosen: str | None, detected: str) -> str:
    """The language a book is read in, given a reader's word and the text's.

    The two are not equal witnesses. The detector can PROVE Vietnamese - the
    marks are on the page - but it can never prove English: the absence of
    marks is the absence of evidence, and a Vietnamese book scanned without
    its diacritics leaves exactly that absence behind. So a reader's word
    fills the gap the text leaves (that scanned book, set to Vietnamese, is
    read) and does not overrule what the text proves (a book 29% marked, set
    to English by a stray tap, stays Vietnamese instead of becoming a book no
    voice will read - the owner's shelf, 12/09/2026).

    One edge to know about: a book too short to judge falls back to the
    interface language, and with a Vietnamese interface that fallback looks
    like proof here. Nothing is lost by it - there was nothing to read.
    """

    if detected == DEFAULT_SPEECH_LANGUAGE:
        return DEFAULT_SPEECH_LANGUAGE
    return chosen if chosen in SPEECH_LANGUAGES else detected
