"""Conservative normalization and speech-sized paragraph splitting."""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE = re.compile(r"\s+")
_PARAGRAPH_BREAK = re.compile(r"\n[\t ]*\n+")
_SENTENCE_ENDINGS = frozenset(".!?…")
_CLAUSE_ENDINGS = frozenset(",;:")
MAX_PASTED_TEXT_CHARS = 100_000


def normalize_paragraph(text: str) -> str:
    """Compose Unicode and collapse whitespace inside one paragraph."""

    composed = unicodedata.normalize("NFC", text)
    return _WHITESPACE.sub(" ", composed).strip()


def prepare_pasted_text(
    text: str,
    max_total_chars: int = MAX_PASTED_TEXT_CHARS,
) -> str:
    """Normalize one-off text after enforcing a bounded raw input size."""

    if max_total_chars <= 0:
        raise ValueError("max_total_chars must be positive")
    if len(text) > max_total_chars:
        raise ValueError("pasted text is too long")
    composed = unicodedata.normalize("NFC", text).replace("\r\n", "\n")
    composed = composed.replace("\r", "\n").replace("\u2029", "\n\n")
    paragraphs = tuple(
        paragraph
        for raw in _PARAGRAPH_BREAK.split(composed)
        if (paragraph := normalize_paragraph(raw))
    )
    return "\n\n".join(paragraphs)


def _last_boundary(
    text: str,
    start: int,
    end: int,
    endings: frozenset[str],
) -> int | None:
    for index in range(end, start, -1):
        if text[index].isspace() and text[index - 1] in endings:
            return index
    return None


def _last_whitespace(text: str, start: int, end: int) -> int | None:
    for index in range(end, start, -1):
        if text[index].isspace():
            return index
    return None


def split_paragraph(text: str, max_chars: int = 240) -> tuple[str, ...]:
    """Split normalized text without exceeding ``max_chars``."""

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    normalized = normalize_paragraph(text)
    if not normalized:
        return ()

    parts: list[str] = []
    cursor = 0
    length = len(normalized)
    while length - cursor > max_chars:
        end = cursor + max_chars
        cut = (
            _last_boundary(normalized, cursor, end, _SENTENCE_ENDINGS)
            or _last_boundary(normalized, cursor, end, _CLAUSE_ENDINGS)
            or _last_whitespace(normalized, cursor, end)
            or end
        )
        part = normalized[cursor:cut].strip()
        if part:
            parts.append(part)
        cursor = cut
        while cursor < length and normalized[cursor].isspace():
            cursor += 1

    if cursor < length:
        parts.append(normalized[cursor:])
    return tuple(parts)


def split_transient_text(text: str, max_chars: int = 240) -> tuple[str, ...]:
    """Preserve authored paragraphs before applying the bounded speech splitter."""

    prepared = prepare_pasted_text(text)
    if not prepared:
        return ()
    parts: list[str] = []
    for paragraph in prepared.split("\n\n"):
        parts.extend(split_paragraph(paragraph, max_chars=max_chars))
    return tuple(parts)
