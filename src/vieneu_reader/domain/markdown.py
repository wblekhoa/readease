"""Conservative Markdown strong-emphasis removal for speech, with source offsets."""

from collections.abc import Sequence
import re


# Consume escapes and code before looking for emphasis. Only paired ** / __
# around prose qualify; literal powers, identifiers and incomplete marks stay.
# Neither delimiter may touch a letter or digit on its outer side: two powers
# in one selection ("2**10 rồi 3**4") otherwise pair up and read "210 rồi 34".
_TOKENS = re.compile(
    r"\\.|(?P<ticks>`+)[\s\S]*?(?P=ticks)(?!`)|"
    r"(?<![\w\\*])\*\*(?![\s*])(?P<stars>[^*`\\]+?)(?<!\s)\*\*(?![\w*])|"
    r"(?<![\w\\_])__(?![\s_])(?P<underscores>[^_`\\]+?)(?<!\s)__(?![\w_])"
)


def strip_strong_parts(parts: Sequence[str]) -> tuple[str, ...]:
    """Remove paired bold markers even when the speech splitter divides a span.

    Keep one result per original part so display text and resume ids still
    address the original selection. Separators are only for matching, never
    returned or counted as spoken characters.
    """
    joined = " ".join(parts)
    removed: set[int] = set()
    for match in _TOKENS.finditer(joined):
        body = match.group("stars") or match.group("underscores")
        if body and any(character.isalnum() for character in body):
            removed.update((match.start(), match.start() + 1,
                            match.end() - 2, match.end() - 1))
    result: list[str] = []
    offset = 0
    for part in parts:
        result.append("".join(character for index, character in enumerate(part)
                              if offset + index not in removed))
        offset += len(part) + 1
    return tuple(result)


def strip_strong(text: str) -> str:
    """The single-segment form of the same speech rule."""
    return strip_strong_parts((text,))[0]


# ── Pasted and captured text: the whole of everyday Markdown (06/10) ─────────
#
# Books keep `strip_strong` alone: their audio is cached by its spoken text,
# so a wider rule would re-synthesise (and, on a paid voice, re-bill) every
# changed paragraph, and fiction opens dialogue with "- " where a list rule
# would fire. Transient text has no cache, and Markdown is what people paste.
#
# Every rule below only DELETES characters of the source, except that a
# table's inner pipe becomes a comma and a heading gains its full stop, so
# each part's speech stays a cleaned copy of exactly that part.

_SENTINEL = "\x00"  # a protected character as the matchers see it
_PROTECT = re.compile(
    r"\\(?P<escaped>[!-/:-@\[-`{-~])|(?P<hard>\\)(?=\s|$)"
    r"|(?<![`\\])(?P<ticks>`+)(?!`)(?P<code>[\s\S]*?)(?<!`)(?P=ticks)(?!`)"
    r"|(?P<tildes>~{3,})(?P<tilde_code>[\s\S]*?)(?P=tildes)"
    r"|(?P<auto><(?:https?://|mailto:)[^\s<>]+>|<[\w.+-]+@[\w-]+(?:\.[\w-]+)+>)"
    r"|(?P<url>(?<![\w@/.])(?:https?://|www\.)[^\s<>]*[^\s<>.,;:!?…)\]}»”’\"'])"
)
_INFO_WORD = re.compile(r"[\w+#.-]+(?=\s)")
_HEADING = re.compile(r"\s{0,3}#{1,6}(?:\s+|$)")
_HEADING_CLOSE = re.compile(r"\s+#+\s*$")
_SETEXT = re.compile(r"\s{0,3}(?:=+|-+)\s*")
_RULE = re.compile(r"\s{0,3}([-*_])(?:\s*\1){2,}\s*")
_TABLE_RULE = re.compile(r"\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*")
_DEFINITION = re.compile(r"\s{0,3}\[(?!\^)[^\]]+\]:\s*\S+(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*")
_FOOTNOTE_DEFINITION = re.compile(r"\s{0,3}\[\^[^\]\s]+\]:\s*")
_QUOTE = re.compile(r"\s{0,3}(?:>\s?)+")
_LIST = re.compile(r"[-+*]\s+")
_TASK = re.compile(r"\[[ xX]\]\s+")
_SENTENCE_CLOSE = ".!?…:;"
_INLINE = (
    # (pattern, which groups SURVIVE; everything else in the match goes).
    # Bracket bodies exclude "[": with "[^\]]" a run of 90,000 "[" took 27 s,
    # each one scanning to the end before failing.
    (re.compile(r"!\[(?P<keep>[^\[\]]*)\]\([^()\s]*(?:\([^()\s]*\)[^()\s]*)*"
                r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"), "keep"),
    (re.compile(r"(?<!!)\[(?P<keep>[^\[\]]+)\]\([^()\s]*(?:\([^()\s]*\)[^()\s]*)*"
                r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"), "keep"),
    (re.compile(r"\[\^[^\[\]\s]+\]"), None),
    (re.compile(r"(?<!!)\[(?P<keep>[^\[\]]+)\]\[[^\[\]]*\]"), "keep"),
    (re.compile(r"~~(?![\s~])(?P<keep>[^~]+?)(?<![\s~])~~"), "keep"),
    (re.compile(r"(?<!\*)(?<![^\W_])(?P<d>\*{1,3})(?![\s*])(?P<keep>[^*]+?)(?<![\s*])"
                r"(?P=d)(?!\*)(?![^\W_])"), "keep"),
    (re.compile(r"(?<!_)(?<![^\W_])(?P<d>_{1,3})(?![\s_])(?P<keep>[^_]+?)(?<![\s_])"
                r"(?P=d)(?!_)(?![^\W_])"), "keep"),
)
_HTML = re.compile(
    r"</?(?P<tag>b|i|em|strong|u|s|del|ins|mark|small|sub|sup|span|code|kbd|"
    r"br|p|div|a|font)\b[^<>]*?/?>",
    re.IGNORECASE,
)
_BREAKING_TAGS = frozenset(("br", "p", "div"))


def markdown_speech_parts(texts: Sequence[str], joints: Sequence[str]) -> tuple[str, ...]:
    """What each transient part says once its Markdown is read as meant.

    `joints` are the splitter's: "block" opens a paragraph, "line" an
    authored line inside one, "split" continues a long line. Line-level
    marks (headings, quotes, lists, tables, rules, definitions) are only
    looked for where a line opens; inline marks are matched across the
    whole selection, so a pair cut by the splitter still closes.
    """
    joined = " ".join(texts)
    edits: dict[int, str] = {}
    protected: set[int] = set()

    def delete(start: int, end: int) -> None:
        for index in range(start, end):
            edits[index] = ""

    for match in _PROTECT.finditer(joined):
        if match.group("hard") is not None:
            edits[match.start()] = ""
        elif match.group("escaped") is not None:
            edits[match.start()] = ""
            protected.add(match.start() + 1)
        elif match.group("ticks") is not None:
            ticks, (body_start, body_end) = match.group("ticks"), match.span("code")
            delete(match.start(), body_start)
            delete(body_end, match.end())
            if len(ticks) >= 3 and (info := _INFO_WORD.match(joined, body_start, body_end)):
                delete(info.start(), info.end())
                body_start = info.end()
            elif (body_end - body_start > 1 and joined[body_start] == " "
                  and joined[body_end - 1] == " "):
                delete(body_start, body_start + 1)
                delete(body_end - 1, body_end)
            protected.update(range(body_start, body_end))
        elif match.group("tildes") is not None:
            body_start, body_end = match.span("tilde_code")
            delete(match.start(), body_start)
            delete(body_end, match.end())
            if info := _INFO_WORD.match(joined, body_start, body_end):
                delete(info.start(), info.end())
                body_start = info.end()
            protected.update(range(body_start, body_end))
        elif match.group("auto") is not None:
            edits[match.start()] = edits[match.end() - 1] = ""
            protected.update(range(match.start() + 1, match.end() - 1))
        else:
            protected.update(range(*match.span()))

    # Lines: [start, end) in `joined`, and whether the line above shares
    # its paragraph (a setext underline needs a line to underline).
    lines: list[list[int]] = []
    continues: list[bool] = []
    offset = 0
    for index, text in enumerate(texts):
        joint = joints[index] if index < len(joints) else "block"
        if not lines or joint != "split":
            lines.append([offset, offset + len(text)])
            continues.append(bool(lines[:-1]) and joint == "line")
        else:
            lines[-1][1] = offset + len(text)
        offset += len(text) + 1

    headings: list[int] = []
    plain: set[int] = set()  # lines no line rule touched: underline-able
    for number, (start, end) in enumerate(lines):
        line = joined[start:end]
        if start in protected or not line.strip():
            continue
        if continues[number] and number - 1 in plain and _SETEXT.fullmatch(line):
            delete(start, end)
            headings.append(number - 1)
            continue
        if _RULE.fullmatch(line) or (_TABLE_RULE.fullmatch(line) and "|" in line):
            delete(start, end)
            continue
        if _DEFINITION.fullmatch(line):
            delete(start, end)
            continue
        if heading := _HEADING.match(line):
            delete(start, start + heading.end())
            if close := _HEADING_CLOSE.search(line, heading.end()):
                delete(start + close.start(), end)
            headings.append(number)
            continue
        cursor = start
        if footnote := _FOOTNOTE_DEFINITION.match(line):
            delete(start, start + footnote.end())
            cursor = start + footnote.end()
        if quote := _QUOTE.match(joined, cursor, end):
            delete(quote.start(), quote.end())
            cursor = quote.end()
        if bullet := _LIST.match(joined, cursor, end):
            delete(bullet.start(), bullet.end())
            cursor = bullet.end()
            if task := _TASK.match(joined, cursor, end):
                delete(task.start(), task.end())
                cursor = task.end()
        rest = joined[cursor:end]
        if rest.lstrip().startswith("|") and rest.count("|") >= 2:
            _table_row(joined, cursor, end, protected, edits)
        elif cursor == start:
            plain.add(number)

    # Inline marks, innermost first: every matcher sees a view rebuilt from
    # what survives, so "**a *b* c**" closes its inner pair, then its outer
    # one, and a link's words are emphasis-checked after the link is gone.
    def view() -> tuple[list[int], str]:
        alive = [index for index in range(len(joined)) if edits.get(index) != ""]
        return alive, "".join(
            _SENTINEL if index in protected else (edits.get(index) or joined[index])[0]
            for index in alive
        )

    alive, seen = view()
    for match in _HTML.finditer(seen):
        span = [alive[position] for position in range(*match.span())]
        for index in span:
            edits[index] = ""
        if match.group("tag").lower() in _BREAKING_TAGS:
            edits[span[0]] = " "
    for _ in range(32):
        changed = False
        for pattern, keep in _INLINE:
            alive, seen = view()
            for match in pattern.finditer(seen):
                if keep is not None:
                    body = match.group(keep)
                    if pattern.groupindex.get("d") and not any(
                        character.isalnum() or character == _SENTINEL for character in body
                    ):
                        continue
                    kept = range(*match.span(keep))
                else:
                    kept = range(0)
                for position in range(*match.span()):
                    if position not in kept:
                        edits[alive[position]] = ""
                changed = True
        if not changed:
            break

    for number in headings:
        if number < 0:
            continue
        start, end = lines[number]
        last = next((index for index in range(end - 1, start - 1, -1)
                     if (edits.get(index, joined[index]) or " ").strip()), None)
        if last is not None:
            said = edits.get(last, joined[last])
            if said[-1] not in _SENTENCE_CLOSE:
                edits[last] = said + "."

    result: list[str] = []
    offset = 0
    for text in texts:
        result.append("".join(edits.get(index, joined[index])
                              for index in range(offset, offset + len(text))))
        offset += len(text) + 1
    return tuple(result)


def _table_row(joined: str, start: int, end: int, protected: set[int],
               edits: dict[int, str]) -> None:
    """"| An | 7 |" reads "An, 7": outer pipes go, inner ones pause."""
    pipes = [index for index in range(start, end)
             if joined[index] == "|" and index not in protected]
    for number, pipe in enumerate(pipes):
        edits[pipe] = "" if number in (0, len(pipes) - 1) and (
            not joined[start:pipe].strip() if number == 0 else not joined[pipe + 1:end].strip()
        ) else ","
        if edits[pipe] == ",":
            back = pipe - 1
            while back >= start and joined[back] == " ":
                edits[back] = ""
                back -= 1
        elif number == 0:
            forward = pipe + 1
            while forward < end and joined[forward] == " ":
                edits[forward] = ""
                forward += 1
        else:
            back = pipe - 1
            while back >= start and joined[back] == " ":
                edits[back] = ""
                back -= 1
