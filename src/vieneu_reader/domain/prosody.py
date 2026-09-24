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
# sentence on its own, which leaves about 250 ms at the seam by itself; this
# tops it up to something the ear reads as a full stop without turning it into
# a paragraph break. It was 100, and a full stop then came out no longer than
# a comma - 0.35 s against the model's own 0.50-0.65 when it reads a stop
# inside one run (audit 23/09, three voices); the owner chose 250 by ear
# (24/09). The English voice's seam is trimmed to the same ~250 ms
# (`kokoro.trim_edges`), so one number sets both.
SENTENCE_PAUSE_MS = 250
BLOCK_PAUSE_MS = 450

# Pauses inside a segment are baked into the audio that gets cached, so the
# cache has to know which reading produced it. Deriving this from the pause
# itself means tuning the pause re-renders exactly what it invalidates.
READING_REVISION = f"sentences-{SENTENCE_PAUSE_MS}"

# A terminal mark, any closing quotes or brackets, then the gap before whatever
# comes next. Only a sentence's end is a cut: a colon and a dash used to be
# cuts too, and each piece then reached the Vietnamese SDK without a closing
# mark - which it FORCES to a full stop, so "Anh ấy nói:" was read as
# "anh ấy nói." with a falling voice and a sentence's pause (audit 23/09).
# Left in the sentence they are read as the commas the SDK turns them into;
# the one dash it drops, the attached one, is `speak_attached_dashes`' job.
_SENTENCE_BOUNDARY = re.compile(r"[.!?…]+[\"\'”’»›)\]}]*\s+")
_SENTENCE_OPENERS = frozenset("(\"'“‘«[-—–")
# Titles and initials end in a period and are followed by a capitalised name,
# which is exactly what a sentence boundary looks like.
_ABBREVIATIONS = frozenset(
    {
        "tp", "ts", "gs", "pgs", "ths", "th", "bs", "ks", "cn", "đh", "cđ",
        "vs", "vd", "tr", "st", "mr", "mrs", "ms", "dr", "prof", "no",
        # English references and months (audit 23/09): "on Jan. 5, 2024"
        # was cut in two in the middle of a date, "see pp. 12" after "pp.".
        # One list for both languages - none of these is a Vietnamese word.
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
        "oct", "nov", "dec", "pp", "vol", "vols", "ch", "chap", "fig", "figs",
        "eq", "eqs", "ed", "eds", "al", "cf", "eg", "ie", "jr", "sr",
    }
)

# A heading is READ differently, not only paused around (owner, 16/09:
# "đổi giọng điệu hoặc đọc to hơn một xíu các tiêu đề"). Neither local
# model takes a pitch or a tone, so the heading is set apart with what the
# pipe does control: a touch slower, a touch louder, and more air on both
# sides. Both are applied after the sentence cache, so the cached voice is
# the same audio either way.
HEADING_RATE = 0.92
HEADING_GAIN = 1.26  # +2 dB

_AFTER_KIND_MS = {
    "heading": 850,
    "paragraph": BLOCK_PAUSE_MS,
    "list_item": 300,
    "quote": 550,
    "caption": BLOCK_PAUSE_MS,
    "preformatted": BLOCK_PAUSE_MS,
}
_BEFORE_KIND_MS = {
    "heading": 1000,
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
    return sorted(cuts)


def split_sentences(text: str) -> tuple[str, ...]:
    """Split one paragraph into the sentences the voice reads one at a time.

    Only a real full stop cuts: not "TS. Nguyễn Văn A", not "3.5", not "Jan.
    5". A colon or a dash stays inside its sentence, where the voice reads it
    as a comma - a pause with the voice still going on - instead of a falling
    full stop (HIG 5.1, 24/09).
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

# The language the VOICE is reading in, which is not the same question as the
# language of the interface. Everything below that turns writing into speech -
# a number, a Roman numeral, a web address - has to answer in the language
# being read, or an English book gets "Part hai" in the middle of a sentence.
# Vietnamese stays the default: it is what every existing caller means.
SPEECH_LANGUAGES = ("vi", "en")
DEFAULT_SPEECH_LANGUAGE = "vi"
_EN_UNITS = (
    "zero", "one", "two", "three", "four",
    "five", "six", "seven", "eight", "nine",
)
_EN_TEENS = (
    "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
)
_EN_TENS = (
    "", "", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety",
)


def speech_language(value: object) -> str:
    """The reading language named by `value`, or Vietnamese."""
    text = str(value or "").strip().lower()
    return text if text in SPEECH_LANGUAGES else DEFAULT_SPEECH_LANGUAGE


def _english_cardinal(number: int) -> str:
    if number < 1 or number > 99:
        return str(number)
    if number < 10:
        return _EN_UNITS[number]
    if number < 20:
        return _EN_TEENS[number - 10]
    tens, unit = divmod(number, 10)
    # Hyphenated the way English writes it; the voice reads the hyphen as the
    # single word it is.
    return _EN_TENS[tens] if unit == 0 else f"{_EN_TENS[tens]}-{_EN_UNITS[unit]}"


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


def spell_ordinal_marks(
    text: str, language: str = DEFAULT_SPEECH_LANGUAGE
) -> str:
    """'#1' → 'thứ nhất' for the voice; the page keeps its '#1'.

    English print says the same thing with a different word: "#1" is read
    "number one", not an ordinal, so the English side is not a translation of
    the Vietnamese one.
    """
    if speech_language(language) == "en":
        return _ORDINAL_MARK.sub(
            lambda m: f"number {_english_cardinal(int(m.group(1)))}", text
        )
    return _ORDINAL_MARK.sub(lambda m: ordinal_words(int(m.group(1))), text)


# An em or en dash with a word on each side ("kể—99 xu", "mép đường—rất khó").
# The Vietnamese SDK turns a SPACED dash into a comma, and a pause, but drops
# an attached one outright: "kể chín mươi chín xu", straight through - the
# owner's own complaint on 02/09. A dash between two DIGITS is a range the SDK
# reads as "đến" and is left alone.
_ATTACHED_DASH = re.compile(r"(?<=\S)[—–](?=\S)")


def speak_attached_dashes(text: str) -> str:
    """'kể—99 xu' → 'kể, 99 xu' for the Vietnamese voice; '1975—1980' stays."""

    def comma(match: re.Match[str]) -> str:
        before, after = text[match.start() - 1], text[match.end()]
        return match.group(0) if before.isdigit() and after.isdigit() else ", "

    return _ATTACHED_DASH.sub(comma, text)


# English clock times, ranges and references, written out before the G2P sees
# them (HIG 5.1, audit 23/09). The English G2P has no normaliser of its own:
# measured on it, every "digit:digit" and every dash-joined pair of numbers
# came out as a nonsense word - "10:30" as ˈæksˌæk, "1990–2000" as
# ˌæɡəɡɡˌIkˈɑɡ - and "pp." as "pip". The Vietnamese voice needs none of this:
# its SDK already says "mười giờ ba mươi phút" and "đến". Every rewrite below
# was tried on the G2P and read right.
_EN_MONTHS = {
    "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
    "Jun": "June", "Jul": "July", "Aug": "August", "Sep": "September",
    "Sept": "September", "Oct": "October", "Nov": "November", "Dec": "December",
}
_EN_MONTH_BEFORE_DAY = re.compile(r"\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.\s+(?=\d)")
_EN_REFERENCE_WORDS = {
    "pp": "pages", "p": "page", "vol": "volume", "vols": "volumes",
    "ch": "chapter", "chap": "chapter", "fig": "figure", "figs": "figures",
}
_EN_REFERENCE = re.compile(r"\b(pp|p|vols|vol|chap|ch|figs|fig)\.\s*(?=\d)", re.IGNORECASE)
# "pp. 12-15": a hyphen after "pages" is a page range, whatever else a
# hyphen between two numbers may be.
_EN_PAGE_RANGE = re.compile(r"\b(pages)\s+(\d+)\s*-\s*(?=\d)", re.IGNORECASE)
_EN_CLOCK_SECONDS = re.compile(r"(?<![\d:])(\d{1,2}):(\d{2}):(\d{2})(?![\d:])")
_EN_CLOCK = re.compile(r"(?<![\d:])(\d{1,2}):(\d{2})(?![\d:])(\s*[ap]\.?m\.?(?![a-z]))?", re.IGNORECASE)
_EN_COLON_PAIR = re.compile(r"(?<![\d:])(\d+):(\d+)(?![\d:])")
_EN_DASH_RANGE = re.compile(r"(\d)\s*[–—]\s*(?=\d)")
# A hyphen joins too much to be read as "to" in general - "2024-05-01",
# "COVID-19", "555-1234", a 2-1 score - so only a span of YEARS is a range.
_EN_YEAR_RANGE = re.compile(r"(?<![\d-])(1[5-9]\d\d|20\d\d)-(\d{4}|\d{2})(?![\d-])")


def _same_case(word: str, written: str) -> str:
    return word[:1].upper() + word[1:] if written[:1].isupper() else word


def _clock(match: re.Match[str]) -> str:
    hour, minute, meridiem = match.group(1), match.group(2), match.group(3) or ""
    if int(hour) > 24 or int(minute) > 59:
        return f"{hour} {minute}{meridiem}"
    if minute == "00":
        # "5:00" is "five o'clock", but "10:00 a.m." is "ten a.m.".
        return f"{hour}{meridiem}" if meridiem else f"{hour} o'clock"
    if minute.startswith("0"):
        return f"{hour} oh {minute[1]}{meridiem}"
    return f"{hour} {minute}{meridiem}"


def speak_english_forms(text: str) -> str:
    """Clock times, number ranges and page references as the English voice
    says them: "10:30" → "10 30", "12–15" → "12 to 15", "pp. 7" → "pages 7".

    A colon pair that is not a clock reads as two numbers when its second
    side has two digits or more ("John 3:16" → "3 16", a verse) and as a
    ratio otherwise ("1:3" → "1 to 3").
    """

    spoken = _EN_MONTH_BEFORE_DAY.sub(lambda m: f"{_EN_MONTHS[m.group(1)]} ", text)
    spoken = _EN_REFERENCE.sub(
        lambda m: f"{_same_case(_EN_REFERENCE_WORDS[m.group(1).lower()], m.group(1))} ", spoken
    )
    spoken = _EN_PAGE_RANGE.sub(lambda m: f"{m.group(1)} {m.group(2)} to ", spoken)
    spoken = _EN_CLOCK_SECONDS.sub(
        lambda m: f"{m.group(1)} {m.group(2)}" + ("" if m.group(3) == "00" else f" {m.group(3)}"),
        spoken,
    )
    spoken = _EN_CLOCK.sub(_clock, spoken)
    spoken = _EN_COLON_PAIR.sub(
        lambda m: f"{m.group(1)} {m.group(2)}" if len(m.group(2)) > 1 else f"{m.group(1)} to {m.group(2)}",
        spoken,
    )
    spoken = _EN_DASH_RANGE.sub(lambda m: f"{m.group(1)} to ", spoken)
    return _EN_YEAR_RANGE.sub(lambda m: f"{m.group(1)} to {m.group(2)}", spoken)


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


# Web addresses. A URL is written for a reader who can copy it; spoken
# whole it is unusable - "w w w chấm flickr chấm com gạch chéo photos gạch
# chéo…" - and the owner asked for the site to be named instead (05/09).
#
# So: the scheme goes, "www" goes, the PATH goes, and what is left is said
# with "chấm" for the dots, behind the words "địa chỉ" so the listener knows
# a link is being named rather than a word being spelled. The page keeps the
# address in full; only the voice shortens it.
#
# 165 addresses in the owner's library. The final label has to be a real
# top-level domain or nothing is a link: the same sweep matched "1.000/năm"
# as a domain the moment that rule was missing.
_LINK_TLDS = frozenset({
    "com", "org", "net", "edu", "gov", "info", "io", "co", "me", "app",
    "dev", "ai", "tv", "blog", "news", "xyz",
    "vn", "uk", "us", "is", "ly", "ch", "de", "fr", "jp", "cn", "au", "ca",
})
_LINK = re.compile(
    r"(?<![\w@/.])(?:https?://)?"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}"
    r"(?:/[^\s<>]*)?"
)
_LINK_TAIL = ".,;:!?…)]}»”’\"'"
#: Words that already announce a link. "tại địa chỉ www.x.com" must not
#: become "tại địa chỉ địa chỉ x chấm com".
_LINK_ANNOUNCED = ("địa chỉ", "đường dẫn", "trang", "website", "url", "link")
#: Same three parts in English: what the dots are called, what announces a
#: link, and the words that already did the announcing.
_LINK_WORDS = {
    "vi": (" chấm ", "địa chỉ ", _LINK_ANNOUNCED),
    "en": (
        " dot ",
        "the address ",
        ("address", "link", "url", "website", "site", "at", "page"),
    ),
}


def speak_links(text: str, language: str = DEFAULT_SPEECH_LANGUAGE) -> str:
    """Say the site a link points at, not the link."""

    separator, prefix, announced = _LINK_WORDS[speech_language(language)]

    def spoken(match: "re.Match[str]") -> str:
        hit = match.group(0)
        tail = ""
        while hit and hit[-1] in _LINK_TAIL:
            tail = hit[-1] + tail
            hit = hit[:-1]
        host = re.sub(r"^https?://", "", hit).split("/", 1)[0]
        host = re.sub(r"^www\d*\.", "", host, flags=re.IGNORECASE)
        labels = [label for label in host.split(".") if label]
        if len(labels) < 2 or labels[-1].lower() not in _LINK_TLDS:
            return match.group(0)
        said = separator.join(labels)
        before = match.string[:match.start()].rstrip().lower()
        if any(before.endswith(word) for word in announced):
            return f"{said}{tail}"
        return f"{prefix}{said}{tail}"

    return _LINK.sub(spoken, text)


# Roman numerals after a division word: "Phần II" is a number the author
# WROTE as a number, and the voice read it as the letter - "phần y" (owner,
# 05/09). Sixty-one of them in the library, every single one behind "Phần".
#
# The cue word is the whole safety of this. A bare uppercase [IVXLC] run is
# not a numeral in any useful sense: the same sweep found "OS X" six times,
# and initials like "Catherine V" - both would become numbers under a rule
# that only looked at the letters. So a numeral is only a numeral when a
# word that names a division of a book stands in front of it.
_ROMAN_CUES = (
    "phần", "chương", "quyển", "tập", "mục", "hồi", "kỳ", "phụ lục",
    "chapter", "part", "book", "volume", "section", "appendix",
)
_ROMAN_NUMERAL = re.compile(
    r"\b(" + "|".join(_ROMAN_CUES) + r")(\s+)([IVXLC]+)\b",
    re.IGNORECASE,
)
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def cardinal_words(number: int, language: str = DEFAULT_SPEECH_LANGUAGE) -> str:
    """'một' … 'chín mươi chín'; anything else stays a digit for the model."""
    if speech_language(language) == "en":
        return _english_cardinal(number)
    if number < 1 or number > 99:
        return str(number)
    if number < 10:
        return _UNITS[number]
    tens, unit = divmod(number, 10)
    head = "mười" if tens == 1 else f"{_UNITS[tens]} mươi"
    if unit == 0:
        return head
    if unit == 1:
        tail = "một" if tens == 1 else "mốt"
    elif unit == 5:
        tail = "lăm"
    else:
        tail = _UNITS[unit]
    return f"{head} {tail}"


def roman_value(token: str) -> int | None:
    """The number a Roman numeral spells, or None if it does not spell one.

    Checked by writing the answer back out: "IIII" and "VV" parse to 4 and
    10 under a naive sum, and neither is a numeral anybody wrote. Only a
    token that round-trips is treated as one.
    """

    total = 0
    previous = 0
    for character in reversed(token):
        value = _ROMAN_VALUES.get(character)
        if value is None:
            return None
        total = total - value if value < previous else total + value
        previous = max(previous, value)
    if total < 1 or total > 399:
        return None
    return total if _roman_form(total) == token else None


def _roman_form(number: int) -> str:
    out = []
    for value, glyph in (
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ):
        while number >= value:
            out.append(glyph)
            number -= value
    return "".join(out)


def speak_roman_numerals(
    text: str, language: str = DEFAULT_SPEECH_LANGUAGE
) -> str:
    """"Phần II" → "Phần hai" for the voice; the page keeps its "II"."""

    def spoken(match: "re.Match[str]") -> str:
        number = roman_value(match.group(3))
        if number is None:
            return match.group(0)
        said = cardinal_words(number, language)
        return f"{match.group(1)}{match.group(2)}{said}"

    return _ROMAN_NUMERAL.sub(spoken, text)


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

# ── References, read for the ear (owner, 16/09: "tối ưu nội dung khi đọc
# các ref để tránh dài dòng") ─────────────────────────────────────────────
#
# A footnote is one of two things. A BIBLIOGRAPHIC one names where a claim
# came from - author, title, publisher, year, page, an address - and read
# aloud it is a list nobody can use with their ears. A COMMENTARY one says
# something more, and that is worth hearing, though a long one hijacks the
# paragraph it hangs from. So a note is classified by its shape, and the
# reader chooses between hearing every note whole (`full`), the commentary
# ones cut short (`short`, the default), or none (`off`). The page shows
# every note either way.
NOTE_READINGS = ("full", "short", "off")
DEFAULT_NOTE_READING = "short"
SHORT_NOTE_SENTENCES = 2
SHORT_NOTE_WORDS = 40

_CITATION_OPENERS = re.compile(
    r"^\s*(?:sđd|s\.đ\.d|nt\b|ntr\b|ibid|id\.|op\.\s*cit|loc\.\s*cit|xem thêm|see also|cf\.|xem\b)",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:1[5-9]\d\d|20\d\d)[a-z]?\b")
_PAGE = re.compile(r"(?:^|[\s,(])(?:tr\.|trang\s+\d|p\.|pp\.|§)\s*\d", re.IGNORECASE)
_PUBLISHER = re.compile(
    r"\b(?:nxb|nhà xuất bản|press|publishing|publishers|university|éditions|editions|verlag|"
    r"books|journal|tạp chí|vol\.|no\.|số\s+\d|tập\s+\d)\b",
    re.IGNORECASE,
)
_ADDRESS = re.compile(r"https?://|www\.|\bdoi[:\s]|\bisbn\b", re.IGNORECASE)


def note_is_citation(body: str) -> bool:
    """Whether a footnote is a bibliographic reference rather than words."""

    text = body.strip()
    if not text:
        return False
    if _CITATION_OPENERS.match(text):
        return True
    if _ADDRESS.search(text) and len(text.split()) <= 30:
        return True
    has_year = bool(_YEAR.search(text))
    if has_year and (_PAGE.search(text) or _PUBLISHER.search(text)):
        return True
    words = text.split()
    if len(words) <= 25:
        # A short note that is mostly names, numbers and punctuation is a
        # reference; prose has small words in it.
        shaped = sum(
            1 for word in words
            if word[:1].isupper() or word[:1].isdigit() or not word[:1].isalnum()
        )
        if shaped / len(words) >= 0.6 and (has_year or _PAGE.search(text)):
            return True
    return False


def shorten_note(body: str) -> str:
    """The first sentences of a commentary note, within a word budget."""

    sentences = split_sentences(body.strip()) or (body.strip(),)
    kept: list[str] = []
    words = 0
    for sentence in sentences[:SHORT_NOTE_SENTENCES]:
        count = len(sentence.split())
        if kept and words + count > SHORT_NOTE_WORDS:
            break
        if not kept and count > SHORT_NOTE_WORDS:
            # One long sentence: cut at the budget, on a word, with an
            # ellipsis the voice renders as a trailing-off pause.
            kept.append(" ".join(sentence.split()[:SHORT_NOTE_WORDS]).rstrip(",;:") + "…")
            words = SHORT_NOTE_WORDS
            break
        kept.append(sentence)
        words += count
    return " ".join(kept)


def spoken_note(body: str, reading: str) -> str | None:
    """What the voice says for a footnote under a reading mode, or None
    for nothing at all."""

    if reading == "off":
        return None
    if reading == "full":
        return body.strip() or None
    if note_is_citation(body):
        return None
    return shorten_note(body) or None


# In-text citations are for the eye too: "(Trần, 2019)", "(Nguyễn & Trần,
# 2019, tr. 12)", "[12]", "[3–5]". Spoken they are a stumble in the middle
# of the sentence that cites. A parenthesis with a year in it and no verb's
# worth of words is a citation; a longer aside is left alone.
_BRACKET_CITATION = re.compile(r"\s?\[\d+(?:\s*[,;–-]\s*\d+)*\](?:,?\s?\[\d+(?:\s*[,;–-]\s*\d+)*\])*")
# The word before a citation, captured so a citation that is the OBJECT of
# the sentence keeps its author: "Theo (Nguyễn, 2019), …" is "Theo Nguyễn",
# not "Theo," - the citation was the only thing the word had to govern.
_PAREN_CITATION = re.compile(
    r"(?P<governor>\b(?:theo|như|xem|according to|see|cf\.)\s+)?\s?\((?P<inside>[^()]{1,80})\)",
    re.IGNORECASE,
)
_CITATION_AUTHOR = re.compile(r"^\s*(?P<author>[^,\d]{1,60}?)\s*,?\s*(?:1[5-9]\d\d|20\d\d)[a-z]?\b")


def drop_citations(text: str) -> str:
    """Take in-text citations out of what the voice says."""

    def parenthesis(match: re.Match[str]) -> str:
        inside = match.group("inside")
        if not (_YEAR.search(inside) and len(inside.split()) <= 8):
            return match.group(0)
        governor = match.group("governor")
        if governor:
            author = _CITATION_AUTHOR.match(inside)
            if author:
                return governor + author.group("author").replace("&", "và" if _looks_vietnamese(governor) else "and")
            return governor.rstrip()
        return ""

    spoken = _BRACKET_CITATION.sub("", text)
    spoken = _PAREN_CITATION.sub(parenthesis, spoken)
    # A comma or a stop that stood after the citation now follows a space.
    return re.sub(r"\s+([.,;:!?…])", r"\1", spoken)


def _looks_vietnamese(word: str) -> bool:
    return word.strip().lower() in {"theo", "như", "xem"}


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


def speakable_text(
    text: str,
    kind: str = "paragraph",
    language: str = DEFAULT_SPEECH_LANGUAGE,
    *,
    citations: bool = False,
) -> str:
    """Shape one segment's text for the voice without touching the display.

    Bullet glyphs derail the voice (one probe read two words for four
    seconds), so they are dropped; a heading left without any terminal
    punctuation tends to end mid-air, so it is spoken with a final period.

    Two more things the eye reads and the ear cannot: a Roman numeral after
    a division word ("Phần II"), which came out as a letter, and a web
    address, which came out spelled character by character.

    `language` is the language being READ. It only reaches the transforms that
    have to produce words - numbers, Roman numerals, the word for a dot in an
    address. Dropping note marks, de-shouting, bullets and the heading's final
    period are the same job in either language.
    """

    # Roman numerals BEFORE unshout: "II" is all-caps and vowel-less, and a
    # de-shouted "ii" is no longer a numeral anything can recognise.
    spoken = drop_note_marks(text)
    if citations:
        # `citations` says the in-text ones may go too - the reader's
        # `note_reading` is anything but "full" (16/09).
        spoken = drop_citations(spoken)
    if speech_language(language) == "en":
        spoken = speak_english_forms(spoken)
    else:
        # The English G2P keeps an attached dash as a mark Kokoro pauses at;
        # the Vietnamese SDK would drop it (HIG 5.1).
        spoken = speak_attached_dashes(spoken)
    spoken = speak_roman_numerals(speak_enumerators(spoken), language)
    spoken = spell_ordinal_marks(unshout(speak_links(spoken, language)), language)
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
