"""Where a reading marks a new part, chapter or section (HIG 5.1, 24/09).

A book's FILES are not its chapters. Converters split a long chapter into
two files, the front matter is a string of small ones, a whole book may sit
in one, and a PDF without bookmarks is imported a page at a time - so a
chime at every new file rang between the title and copyright pages, in the
middle of a chapter, never in a one-file book, and mid-sentence at every
page of a PDF. The publisher's contents say where the chapters are, and the
contents column already reads them (`app/src/ui/contents.ts`, HIG 3.25);
the voice reads them the same way, so the chime falls exactly where the eye
sees a chapter or part line.

The plan is derived on open, like the rest of the presentation overlay: the
stored segments, their ids and everything keyed by them stay as they were.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from vieneu_reader.domain.models import BookDocument
from vieneu_reader.domain.presentation import ContentsEntry
from vieneu_reader.domain.prosody import ends_sentence

# What a seam can open. A "part-chapter" is the chapter standing right after
# its part's title: the part's sound already said "something new begins".
PART = "part"
CHAPTER = "chapter"
PART_CHAPTER = "part-chapter"
# A first-level section - the contents line right under the chapter level,
# "1.1", "1.2" ... - which opens with a short sound (owner, 25/09: "Chương
# dài, mục ngắn"). Deeper sections are not divisions.
SECTION = "section"
SCENE = "scene"
# The next page of a PDF imported page by page, when the page before ended
# in the middle of a sentence: the sentence reads on, with no rest.
CONTINUE = "continue"

# How much a part may say between its title and its first chapter - the
# title, a subtitle, an epigraph - before that chapter counts as its own
# arrival again and gets its own sound.
PART_OPENING_WORDS = 80

_UNITS = {
    "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5,
    "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}
_ENGLISH = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
_MARKER = re.compile(r"^(chương|chapter|phần|part|quyển)\s+(.+)$", re.IGNORECASE)
_TRAILING = re.compile(r"[:.\-–—]+$")
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
_PDF_PAGE = re.compile(r"^Trang \d+$")


def _vietnamese_number(words: Sequence[str]) -> int | None:
    """"hai mươi mốt" = 21, "mười lăm" = 15, "tư" = 4 - or None."""

    value = 0
    seen = False
    index = 0
    while index < len(words):
        word = words[index]
        if word == "mười":
            value += 10
            seen = True
        elif word in _UNITS:
            if index + 1 < len(words) and words[index + 1] == "mươi":
                value += _UNITS[word] * 10
                index += 1
            else:
                value += _UNITS[word]
            seen = True
        else:
            return None
        index += 1
    return value if seen else None


def _roman_number(word: str) -> int | None:
    if not word or any(character not in _ROMAN for character in word):
        return None
    total = 0
    for index, character in enumerate(word):
        here = _ROMAN[character]
        following = _ROMAN.get(word[index + 1], 0) if index + 1 < len(word) else 0
        total += -here if here < following else here
    return total if total > 0 else None


def contents_marker(title: str) -> tuple[str, int] | None:
    """("chapter", 1) for "Chương 1 …", ("part", 2) for "Phần Hai: …" - the
    same reading as `marker()` in `app/src/ui/contents.ts`."""

    found = _MARKER.match(title.strip())
    if not found:
        return None
    kind = CHAPTER if found.group(1).lower() in ("chương", "chapter") else PART
    words = found.group(2).split()
    first = _TRAILING.sub("", words[0])
    number: int | None = None
    if first.isdigit() and first.isascii():
        number = int(first)
    elif _roman_number(first) is not None:
        number = _roman_number(first)
    elif first.lower() in _ENGLISH:
        number = _ENGLISH[first.lower()]
    else:
        # Vietnamese numbers run over several words: the longest run that
        # still reads as one ("hai mươi mốt"), stopping at the title.
        for take in range(min(4, len(words)), 0, -1):
            run = [_TRAILING.sub("", word).lower() for word in words[:take]]
            value = _vietnamese_number(run)
            if value is not None:
                number = value
                break
    if number is None or number <= 0:
        return None
    return kind, number


def _chapter_level(
    entries: Sequence[ContentsEntry], markers: Sequence[tuple[str, int] | None]
) -> int:
    """The level the chapters sit at: where "Chương N" lines are most often,
    else the top."""

    tally: dict[int, int] = {}
    for entry, found in zip(entries, markers):
        if found is not None and found[0] == CHAPTER:
            tally[entry.level] = tally.get(entry.level, 0) + 1
    if tally:
        return sorted(tally.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return min(entry.level for entry in entries)


def contents_roles(entries: Sequence[ContentsEntry]) -> list[str]:
    """"part", "chapter" or "section" for each line, by the contents column's
    rule (HIG 3.25): the chapter level is where "Chương N" lines sit most
    often, else the top; above it, a line with lines under it - or one that
    says "Phần N" - opens a part; below it are sections."""

    if not entries:
        return []
    markers = [contents_marker(entry.title) for entry in entries]
    stops = _chapter_level(entries, markers)
    roles: list[str] = []
    for index, entry in enumerate(entries):
        found = markers[index]
        following = entries[index + 1].level if index + 1 < len(entries) else 0
        opens_group = (found is not None and found[0] == PART) or following > entry.level
        if entry.level < stops:
            roles.append(PART if opens_group else CHAPTER)
        elif entry.level == stops:
            roles.append(CHAPTER)
        else:
            roles.append("section")
    return roles


def _words(text: str) -> int:
    return len(text.split())


def division_plan(
    book: BookDocument,
    contents: Sequence[ContentsEntry] = (),
    breaks: Iterable[str] = (),
) -> dict[str, str]:
    """What each seam of a reading opens, keyed by the id of the segment it
    opens: PART, CHAPTER, PART_CHAPTER, SECTION, SCENE, or CONTINUE for a
    PDF page that carries on a sentence. A segment not in the map rests the
    way any block does, even when it starts a new file."""

    segments = [segment for chapter in book.chapters for segment in chapter.segments]
    plan: dict[str, str] = {}
    known = {segment.id for segment in segments}
    # A part whose own line also names its first chapter has already had that
    # chapter's arrival; the NEXT chapter is not "right after the part".
    absorbed: set[str] = set()
    if contents:
        # "1.1", "1.2" ...: the level right under the chapters. Deeper ones
        # keep the heading's rest - a document can hold hundreds of sections.
        first_sections = _chapter_level(
            contents, [contents_marker(entry.title) for entry in contents]
        ) + 1
        for entry, role in zip(contents, contents_roles(contents)):
            if entry.segment_id not in known:
                continue
            if role == SECTION:
                # The lowest of the three: never over a chapter or part line
                # on the same passage, and never mistaken for one colliding.
                if entry.level == first_sections and entry.segment_id not in plan:
                    plan[entry.segment_id] = SECTION
                continue
            already = plan.get(entry.segment_id)
            if already is None or already == SECTION:
                plan[entry.segment_id] = role
            elif already != role:
                # A part line and a chapter line on one passage: it opens the
                # part, and that part has had its first chapter already.
                plan[entry.segment_id] = PART
                absorbed.add(entry.segment_id)
    elif book.source_format == "pdf":
        # Without bookmarks the importer made a chapter of every page; a page
        # is not a chapter, and a sentence that runs over its foot reads on.
        # With bookmarks, each bookmark is a chapter.
        if all(_PDF_PAGE.match(chapter.title) for chapter in book.chapters):
            pages = [chapter for chapter in book.chapters if chapter.segments]
            for before, page in zip(pages, pages[1:]):
                if not ends_sentence(before.segments[-1].text):
                    plan[page.segments[0].id] = CONTINUE
        else:
            for chapter in book.chapters:
                if chapter.segments:
                    plan[chapter.segments[0].id] = CHAPTER
    else:
        # No contents: a new file opens a chapter only when it opens with a
        # heading - a converter's split carries on with a paragraph.
        for chapter in book.chapters:
            if not chapter.segments or chapter.segments[0].kind != "heading":
                continue
            found = contents_marker(chapter.segments[0].text)
            plan[chapter.segments[0].id] = PART if found and found[0] == PART else CHAPTER

    # One sound for a part and the chapter that follows its title.
    part_at: str | None = None
    spoken_since = 0
    for segment in segments:
        opens = plan.get(segment.id)
        if opens == PART:
            part_at = None if segment.id in absorbed else segment.id
            spoken_since = 0
        elif opens == CHAPTER:
            if part_at is not None and spoken_since <= PART_OPENING_WORDS:
                plan[segment.id] = PART_CHAPTER
            part_at = None
        if part_at is not None:
            spoken_since += _words(segment.text)

    # One arrival, one sound (25/09): a division whose passage follows the
    # previous one with nothing but titles between them - "Chương 1" and its
    # name as two lines of the contents, a part inside a part, a section
    # whose title stands right under its chapter's - is the same arrival,
    # and rests like two headings in a row. A short chapter with words of
    # its own is still a chapter: on the owner's library 19 of 23 close
    # pairs were, and only 2 were headings in a row. A section is not an
    # arrival for this rule: a chapter after an empty section still rings.
    arrived = False
    since_titles_only = True
    for segment in segments:
        opens = plan.get(segment.id)
        if opens in (PART, CHAPTER, SECTION) and arrived and since_titles_only:
            del plan[segment.id]
            # Still a passage: when a line pointed at words, not a title,
            # those words are the chapter's own.
            opens = None
        if opens in (PART, CHAPTER, PART_CHAPTER):
            arrived = True
            # A division that opens on words - a PDF bookmark, a line of
            # the contents pointing at a paragraph - has said something.
            since_titles_only = segment.kind == "heading"
        elif segment.kind != "heading":
            since_titles_only = False

    for segment_id in breaks:
        if segment_id in known and segment_id not in plan:
            plan[segment_id] = SCENE
    return plan
