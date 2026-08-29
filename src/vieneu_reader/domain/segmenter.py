"""Conservative normalization and speech-sized paragraph splitting."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from vieneu_reader.domain.models import SegmentJoint
from vieneu_reader.domain.prosody import ends_sentence


_WHITESPACE = re.compile(r"\s+")
_PARAGRAPH_BREAK = re.compile(r"\n[\t ]*\n+")
_SENTENCE_ENDINGS = frozenset(".!?…")
_CLAUSE_ENDINGS = frozenset(",;:")
MAX_PASTED_TEXT_CHARS = 100_000


def normalize_paragraph(text: str) -> str:
    """Compose Unicode and collapse whitespace inside one paragraph."""

    composed = unicodedata.normalize("NFC", text)
    return _WHITESPACE.sub(" ", composed).strip()


def _composed_transient_text(text: str, max_total_chars: int) -> str:
    if max_total_chars <= 0:
        raise ValueError("max_total_chars must be positive")
    if len(text) > max_total_chars:
        raise ValueError("pasted text is too long")
    composed = unicodedata.normalize("NFC", text).replace("\r\n", "\n")
    return composed.replace("\r", "\n").replace("\u2029", "\n\n")


def prepare_pasted_text(
    text: str,
    max_total_chars: int = MAX_PASTED_TEXT_CHARS,
) -> str:
    """Normalize one-off text after enforcing a bounded raw input size."""

    composed = _composed_transient_text(text, max_total_chars)
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


@dataclass(frozen=True, slots=True)
class TransientPart:
    text: str
    joint: SegmentJoint


def _merged_paragraph_lines(raw_paragraph: str) -> tuple[str, ...]:
    """Keep authored line breaks, folding hard-wrapped continuations back in.

    A line that opens in lowercase while the line above never closed its
    sentence is a wrapping artifact (mail, code paste), not an authored
    break; verse, lists and addresses open their lines with capitals,
    digits or markers, so those keep their line boundary.
    """

    kept: list[str] = []
    for raw_line in raw_paragraph.split("\n"):
        line = normalize_paragraph(raw_line)
        if not line:
            continue
        if kept and line[0].islower() and not ends_sentence(kept[-1]):
            kept[-1] = f"{kept[-1]} {line}"
        else:
            kept.append(line)
    return tuple(kept)


def split_transient_parts(
    text: str,
    max_chars: int = 240,
) -> tuple[TransientPart, ...]:
    """Split one-off text while remembering how each part attaches."""

    composed = _composed_transient_text(text, MAX_PASTED_TEXT_CHARS)
    parts: list[TransientPart] = []
    for raw_paragraph in _PARAGRAPH_BREAK.split(composed):
        for line_index, line in enumerate(_merged_paragraph_lines(raw_paragraph)):
            for piece_index, piece in enumerate(
                split_paragraph(line, max_chars=max_chars)
            ):
                if piece_index:
                    joint: SegmentJoint = "split"
                elif line_index:
                    joint = "line"
                else:
                    joint = "block"
                parts.append(TransientPart(piece, joint))
    return tuple(parts)


def split_transient_text(text: str, max_chars: int = 240) -> tuple[str, ...]:
    """Preserve authored paragraphs before applying the bounded speech splitter."""

    return tuple(part.text for part in split_transient_parts(text, max_chars))
