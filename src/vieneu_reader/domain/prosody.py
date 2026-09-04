"""Structure-aware pauses and speech-text shaping for natural reading.

Every duration here is the silence ReadEase itself injects at a boundary,
on top of the roughly 250-400 ms the voice already leaves at the seams of
two synthesized clips. Injected silence rides through the playback
time-stretcher, so at faster reading rates every pause shortens with the
speech.
"""

from __future__ import annotations

import re
import unicodedata

from collections.abc import Sequence

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
# A colon only introduces something when a gap follows it, which is what keeps
# "10:30" and "https://" whole without this needing to know about clocks or
# links. A dash sets an aside apart, attached or spaced - but between two
# digits it is a range like "1975—1980", so the range is matched FIRST, as its
# own thing, and skipped. The old guard refused any dash touching a digit on
# either side, which silently swallowed "kể—99 xu": a letter before, a number
# after, and the voice ran straight through it (owner, 2026-09-02). A hyphen
# only counts as a dash when spaced on both sides ("Anh - em"); "tháng 1-2"
# and "Anh-Mỹ" stay whole.
_CLAUSE_BOUNDARY = re.compile(
    r":\s+|(?P<range>\d\s*[—–-]\s*\d)|\s*[—–]\s*|\s-\s"
)
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


def _boundaries(text: str) -> list[int]:
    """Offsets where the voice should take a breath inside one paragraph."""

    cuts: set[int] = set()
    for match in _SENTENCE_BOUNDARY.finditer(text):
        following = match.end()
        if following >= len(text) or not _opens_a_sentence(text[following]):
            continue
        if _is_abbreviation(text, match.start()):
            continue
        cuts.add(following)
    for match in _CLAUSE_BOUNDARY.finditer(text):
        if match.group("range"):
            continue  # "1975—1980": one thing, not two
        if match.end() >= len(text):
            continue
        # A dash that OPENS a line of dialogue has nothing before it to end -
        # at the start of the text, or right after a finished sentence
        # ("Cô ấy gật đầu. - Vâng"). The sentence break already cut there;
        # cutting again would leave the dash standing alone.
        before = text[: match.start()].rstrip()
        if not before or ends_sentence(before):
            continue
        cuts.add(match.end())
    return sorted(cuts)


def split_sentences(text: str) -> tuple[str, ...]:
    """Split one paragraph into the parts the voice should read apart.

    A full stop is the obvious break, but a colon introducing something and a
    dash setting an aside apart are breaks the ear expects too, and the voice
    places none of them reliably on its own. Each cut is only taken where the
    punctuation really means it: not inside "TS. Nguyễn Văn A", "10:30",
    "https://readease.vn" or "1975—1980".
    """

    parts: list[str] = []
    start = 0
    for cut in _boundaries(text):
        piece = text[start:cut].strip()
        if piece:
            parts.append(piece)
            start = cut
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return tuple(parts)


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


def _core_letters(token: str) -> str:
    return "".join(character for character in token if character.isalpha())


def _has_vowel(word: str) -> bool:
    decomposed = unicodedata.normalize("NFD", word.lower())
    return any(character in "aeiouy" for character in decomposed)


def _is_shouted(token: str) -> bool:
    letters = _core_letters(token)
    # A word with no vowel is an abbreviation - BBC, TP, HCM - and lowercasing
    # it would ask the voice to pronounce letters that are meant to be spelled.
    return len(letters) >= 2 and letters.isupper() and _has_vowel(letters)


def unshout(text: str) -> str:
    """Lower the case of words written in capitals for emphasis.

    Set text and headings often arrive shouted - LOOK RIGHT, CHƯƠNG MỘT - and
    the voice reads capitals more slowly and less predictably than ordinary
    words. Only a run of at least two shouted words is touched, so a lone
    acronym in a normal sentence keeps its capitals.
    """

    tokens = text.split(" ")
    shouted = [_is_shouted(token) for token in tokens]
    result = list(tokens)
    start = 0
    while start < len(tokens):
        if not shouted[start]:
            start += 1
            continue
        end = start
        while end < len(tokens) and shouted[end]:
            end += 1
        if end - start >= 2:
            for index in range(start, end):
                result[index] = tokens[index].lower()
            if start == 0:
                # Ordinary prose still opens with a capital; a shouted heading
                # should end up looking like a sentence, not like a whisper.
                result[0] = _capitalise_first(result[0])
        start = end
    return " ".join(result)


def _capitalise_first(token: str) -> str:
    for index, character in enumerate(token):
        if character.isalpha():
            return token[:index] + character.upper() + token[index + 1 :]
    return token


# "#1" is an ordinal in print ("Sự thật #1", "#2. Thế giới đã thay đổi") but
# the voice has no way to know that; it was handed the raw "#1" and read it
# however the model felt like. Spoken Vietnamese says "thứ nhất", and the
# words are irregular at exactly the places a naive "thứ " + digits gets wrong:
# 1 → nhất, 4 → tư, and inside compounds 1 → mốt, 4 → tư, 5 → lăm.
_ORDINAL_MARK = re.compile(r"(?<![\w#])#(\d{1,3})(?!\w)")
_UNITS = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín")


def ordinal_words(number: int) -> str:
    """'thứ nhất' … 'thứ chín mươi chín'; digits past that (the model reads them)."""
    if number < 1 or number > 99:
        return f"thứ {number}"
    if number == 1:
        return "thứ nhất"
    if number == 4:
        return "thứ tư"
    if number < 10:
        return f"thứ {_UNITS[number]}"
    tens, unit = divmod(number, 10)
    head = "mười" if tens == 1 else f"{_UNITS[tens]} mươi"
    if unit == 0:
        return f"thứ {head}"
    if unit == 1:
        tail = "một" if tens == 1 else "mốt"
    elif unit == 4:
        tail = "bốn" if tens == 1 else "tư"
    elif unit == 5:
        tail = "lăm"
    else:
        tail = _UNITS[unit]
    return f"thứ {head} {tail}"


def spell_ordinal_marks(text: str) -> str:
    """'#1' → 'thứ nhất' for the voice; the page keeps its '#1'."""
    return _ORDINAL_MARK.sub(lambda m: ordinal_words(int(m.group(1))), text)


# Footnote numbers set as superscripts. Six in the owner's library, every one a
# note mark ("Tang.³", "người³"); none arithmetic. A superscript right after a
# digit IS arithmetic ("10³") and is left alone.
_NOTE_MARK = re.compile(r"(?<!\d)[\u00b2\u00b3\u00b9\u2070\u2074-\u2079]+")


_LEADING_ZERO = re.compile(r"^\s*0+(?=\d)")


# Inline enumerators "(a) … (b) …". The owner's library has 31, all of them
# opening a phrase in a list, none a reference. The ear chose (02/09, four
# renders of the same sentence) the letter kept and a pause after it: "a,
# nhiệm vụ hiện tại, hoặc b, sở thích" - not deleted, not "một là / hai là".
# "book(s)" has no space before the bracket and is not an enumerator.
_ENUMERATOR = re.compile(r"(?<!\S)\(([a-z])\)")
_ENUMERATOR_AFTER_CONJUNCTION = re.compile(
    r"\s*(?:,\s*)?\b(hoặc|hay|và|rồi|cũng như)\s+\(([a-z])\)"
)
# "mục (b)", "điểm (c)": a reference to an item, spoken as its name, no pause.
_ENUMERATOR_REFERENCE = re.compile(
    r"\b(mục|điểm|phần|khoản|ý|câu|trường hợp|phương án|lựa chọn)\s+\(([a-z])\)"
)


def speak_enumerators(text: str) -> str:
    """Turn "(a)" markers into something the voice can phrase.

    An enumerator becomes the letter plus a pause ("a, "); when a conjunction
    leads into it the pause moves in front of the conjunction, which is how
    the sentence was read in the render the owner picked. A reference
    ("mục (b)") keeps its letter and takes no pause.
    """

    spoken = _ENUMERATOR_REFERENCE.sub(lambda m: f"{m.group(1)} {m.group(2)}", text)
    spoken = _ENUMERATOR_AFTER_CONJUNCTION.sub(lambda m: f", {m.group(1)} {m.group(2)},", spoken)
    return _ENUMERATOR.sub(lambda m: f"{m.group(1)},", spoken)


def drop_note_marks(text: str) -> str:
    """Take the footnote superscripts out of what the voice says.

    They are for the eye - the page keeps them - and spoken they land as a
    stray "ba" in the middle of a sentence, glued to the word before it.

    Only the SUPERSCRIPT glyphs, and that is not the whole problem: a book
    whose references are ordinary digits inside a link ("tiếp theo 6 - dù")
    reads them as numbers, and no character here can tell that "6" from any
    other. Those are removed by position instead - see `speak_with_notes`,
    which knows where each reference is because the note it points at was
    found with it.
    """

    return _NOTE_MARK.sub("", text)


#: Punctuation that should not be left stranded behind a removed reference
#: number: "(tương lai) 2 ." has to close as "(tương lai)." and not "…) .".
_CLINGING = ".,;:!?…)]}»”’"


def _text_without_labels(
    text: str, marks: Sequence[tuple[int, int]]
) -> tuple[str, tuple[int, ...]]:
    """The sentence without its reference numbers, and where they had been.

    The number is for the eye. Left in, the voice reads "sáu" in the middle
    of a clause, glued to the word before it - and now that the note itself
    is spoken, the number is not even the pointer it was on paper.
    """

    kept: list[str] = []
    positions: list[int] = []
    cursor = 0
    for offset, length in marks:
        kept.append(text[cursor:offset])
        positions.append(sum(len(piece) for piece in kept))
        cursor = offset + length
    kept.append(text[cursor:])
    joined = "".join(kept)

    # Close the gap the number left - a doubled space, or a space now
    # standing in front of the punctuation that used to follow the number -
    # and carry the positions across the same edit.
    out: list[str] = []
    moved: list[int] = []
    at = 0
    for index, character in enumerate(joined):
        while at < len(positions) and positions[at] == index:
            moved.append(len(out))
            at += 1
        if character == " ":
            if not out or out[-1] == " ":
                continue
            ahead = index + 1
            while ahead < len(joined) and joined[ahead] == " ":
                ahead += 1
            # Looks PAST the gap the number left, so "lai) 2 ." closes as
            # "lai)." and not "lai) .".
            if ahead < len(joined) and joined[ahead] in _CLINGING:
                continue
        out.append(character)
    while at < len(positions):
        moved.append(len(out))
        at += 1

    clean = "".join(out)
    lead = len(clean) - len(clean.lstrip())
    trimmed = clean.strip()
    return trimmed, tuple(
        min(max(position - lead, 0), len(trimmed)) for position in moved
    )


def sentence_end_at_or_after(text: str, position: int) -> int:
    """Where the sentence holding ``position`` finishes.

    A note belongs to a sentence, not to a word: read at the number itself
    it cuts the clause in half, and the listener loses both halves. So the
    sentence is finished first and the note follows it whole.
    """

    for index in range(min(position, len(text)), len(text)):
        if text[index] in SENTENCE_ENDINGS:
            end = index + 1
            while end < len(text) and text[end] in _TRAILING_CLOSERS:
                end += 1
            return end
    return len(text)


def speak_with_notes(
    text: str, notes: Sequence[tuple[int, int, str]]
) -> tuple[tuple[str, bool], ...]:
    """One segment's text broken into what the voice says, in order.

    Each piece is ``(text, is_note)``. Notes attached to the same sentence
    come out after it in the order the page prints them; a segment with no
    notes comes back as itself, so the caller has one path, not two.
    """

    if not notes:
        # Untouched, not stripped: `speakable_text` decides what a segment
        # says, and the estimate re-derives its number from that same
        # function. Trimming here would make the price and the reading
        # disagree by however much whitespace the book happened to carry.
        return ((text, False),) if text.strip() else ()
    clean, positions = _text_without_labels(text, [(at, size) for at, size, _ in notes])
    cuts = [sentence_end_at_or_after(clean, position) for position in positions]
    pieces: list[tuple[str, bool]] = []
    cursor = 0
    index = 0
    while index < len(cuts):
        here = cuts[index]
        same = index
        while same < len(cuts) and cuts[same] == here:
            same += 1
        chunk = clean[cursor:here].strip()
        if chunk:
            pieces.append((chunk, False))
        for order in range(index, same):
            body = notes[order][2].strip()
            if body:
                pieces.append((body, True))
        cursor = here
        index = same
    tail = clean[cursor:].strip()
    if tail:
        pieces.append((tail, False))
    return tuple(pieces)


def speakable_text(text: str, kind: str = "paragraph") -> str:
    """Shape one segment's text for the voice without touching the display.

    Bullet glyphs derail the voice (one probe read two words for four
    seconds), so they are dropped; a heading left without any terminal
    punctuation tends to end mid-air, so it is spoken with a final period.
    """

    spoken = spell_ordinal_marks(unshout(speak_enumerators(drop_note_marks(text))))
    stripped = spoken.lstrip()
    while stripped and stripped[0] in _BULLET_GLYPHS:
        stripped = stripped[1:].lstrip()
    if stripped:
        spoken = stripped
    if kind == "heading":
        # "01", "07": the numbered-principle headings the owner's library has
        # 203 of. Spoken with the zero ("không một") they are wrong; the page
        # keeps the zero-padded label, the voice says the number.
        spoken = _LEADING_ZERO.sub("", spoken)
        if not final_punctuation(spoken):
            spoken = f"{spoken}."
    return spoken
