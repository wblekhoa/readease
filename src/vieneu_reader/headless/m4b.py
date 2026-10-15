"""An audiobook file (.m4b) with chapter marks, from a WAV, with nothing added.

macOS encodes the audio (`afconvert`, part of every Mac); this module only
rearranges the MPEG-4 boxes around it and adds a QuickTime chapter track -
the kind Apple Books, QuickTime and Music read. Spike of 15/10 (RE-PLAY-020):
AVFoundation wrote such a track and read it back; the layout below is
the one it wrote (a disabled 'text' track, one sample per chapter, the audio
track pointing at it with tref/chap), so no AVFoundation binding and no new
dependency is needed.

The file is laid out as ftyp, mdat (the encoded audio as it was, then the
chapter samples), moov - so every audio chunk moves by one known distance and
nothing has to be guessed about where the encoder put its boxes.
"""

from __future__ import annotations

import os
import struct
import subprocess
import tempfile
from dataclasses import dataclass


@dataclass(frozen=True)
class Chapter:
    title: str
    start: float  # seconds from the start of the file


# --- box reading ------------------------------------------------------------

def _boxes(data: bytes, start: int, end: int):
    """(kind, box_start, body_start, box_end) for each box in data[start:end]."""
    at = start
    while at + 8 <= end:
        size, kind = struct.unpack(">I4s", data[at:at + 8])
        body = at + 8
        if size == 1:
            size = struct.unpack(">Q", data[at + 8:at + 16])[0]
            body = at + 16
        elif size == 0:
            size = end - at
        if size < 8 or at + size > end:
            raise ValueError(f"damaged box {kind!r} at {at}")
        yield kind, at, body, at + size
        at += size


def _child(data: bytes, start: int, end: int, kind: bytes):
    for found, box_start, body, box_end in _boxes(data, start, end):
        if found == kind:
            return box_start, body, box_end
    return None


def _box(kind: bytes, *parts: bytes) -> bytes:
    body = b"".join(parts)
    return struct.pack(">I4s", 8 + len(body), kind) + body


def _full(kind: bytes, version_flags: int, *parts: bytes) -> bytes:
    return _box(kind, struct.pack(">I", version_flags), *parts)


# --- the chapter track ------------------------------------------------------

_TEXT_SAMPLE_DESCRIPTION = (
    struct.pack(">I4s6xH", 59, b"text", 1)  # size, format, reserved, data ref 1
    + bytes(4 + 4 + 6 + 8 + 8 + 2 + 2 + 1 + 2 + 6)
    # display flags, justification, background colour, text box, reserved,
    # font number, face, reserved, reserved, foreground colour (59 bytes in
    # all, as AVFoundation wrote it)
)
# The 'encd' atom QuickTime puts after each sample's text: UTF-8.
_ENCD_UTF8 = struct.pack(">I4sI", 12, b"encd", 0x00000100)
_TIMESCALE = 1000  # chapter times in milliseconds


def _chapter_sample(title: str) -> bytes:
    text = title.encode("utf-8")[:0xFFFF]
    return struct.pack(">H", len(text)) + text + _ENCD_UTF8


def _language_code(language: str) -> int:
    """ISO 639-2/T in the 15 bits mdhd keeps; 'und' when not known."""
    code = {"vi": "vie", "en": "eng"}.get(language, "und")
    return ((ord(code[0]) - 0x60) << 10) | ((ord(code[1]) - 0x60) << 5) | (ord(code[2]) - 0x60)


def _chapter_trak(track_id: int, durations_ms: list[int], sizes: list[int], offsets: list[int], movie_timescale: int, language: str = "") -> bytes:
    total_ms = sum(durations_ms)
    movie_duration = total_ms * movie_timescale // _TIMESCALE
    identity = struct.pack(">9I", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)
    # flags 0: a chapter track is never played, only listed.
    tkhd = _full(b"tkhd", 0, struct.pack(">IIIII", 0, 0, track_id, 0, movie_duration),
                 bytes(8), struct.pack(">hhhH", 0, 0, 0, 0), identity, struct.pack(">II", 0, 0))
    mdhd = _full(b"mdhd", 0, struct.pack(">IIII", 0, 0, _TIMESCALE, total_ms), struct.pack(">HH", _language_code(language), 0))
    hdlr = _full(b"hdlr", 0, struct.pack(">I4s12x", 0, b"text"), b"Chapters\x00")
    dinf = _box(b"dinf", _full(b"dref", 0, struct.pack(">I", 1), _full(b"url ", 1)))
    stts = _full(b"stts", 0, struct.pack(">I", len(durations_ms)),
                 b"".join(struct.pack(">II", 1, d) for d in durations_ms))
    stsc = _full(b"stsc", 0, struct.pack(">IIII", 1, 1, 1, 1))
    stsz = _full(b"stsz", 0, struct.pack(">II", 0, len(sizes)), b"".join(struct.pack(">I", s) for s in sizes))
    stco = _full(b"stco", 0, struct.pack(">I", len(offsets)), b"".join(struct.pack(">I", o) for o in offsets))
    stsd = _full(b"stsd", 0, struct.pack(">I", 1), _TEXT_SAMPLE_DESCRIPTION)
    stbl = _box(b"stbl", stsd, stts, stsc, stsz, stco)
    minf = _box(b"minf", _full(b"nmhd", 0), dinf, stbl)
    return _box(b"trak", tkhd, _box(b"mdia", mdhd, hdlr, minf))


# --- tags -------------------------------------------------------------------

def _ilst_text(kind: bytes, value: str) -> bytes:
    return _box(kind, _full(b"data", 1, struct.pack(">I", 0), value.encode("utf-8")))


def _udta(tags: dict[str, str], cover: bytes | None) -> bytes:
    items = [_ilst_text(kind, tags[key]) for key, kind in (
        ("title", b"\xa9nam"), ("artist", b"\xa9ART"), ("album", b"\xa9alb"),
        ("comment", b"\xa9cmt"), ("software", b"\xa9too"), ("year", b"\xa9day"),
    ) if tags.get(key)]
    # Audiobook, so the Music app files it there (stik 2).
    items.append(_box(b"stik", _full(b"data", 21, struct.pack(">I", 0), b"\x02")))
    if cover:
        kind = 14 if cover[:8] == b"\x89PNG\r\n\x1a\n" else 13
        items.append(_box(b"covr", _full(b"data", kind, struct.pack(">I", 0), cover)))
    hdlr = _full(b"hdlr", 0, struct.pack(">I4s12x", 0, b"mdir"), b"\x00")
    return _box(b"udta", _full(b"meta", 0, hdlr, _box(b"ilst", *items)))


# --- the rewrite ------------------------------------------------------------

def _rewrite_stco(stbl: bytes, shift: int) -> bytes:
    """stbl's body with every audio chunk offset moved by `shift`."""
    out = bytearray()
    for kind, box_start, body, box_end in _boxes(stbl, 0, len(stbl)):
        box = stbl[box_start:box_end]
        if kind == b"stco":
            count = struct.unpack(">I", stbl[body + 4:body + 8])[0]
            offsets = struct.unpack(f">{count}I", stbl[body + 8:body + 8 + 4 * count])
            moved = [o + shift for o in offsets]
            if moved and max(moved) > 0xFFFFFFFF:
                raise ValueError("audio too long for 32-bit chunk offsets")
            box = _full(b"stco", 0, struct.pack(">I", count), struct.pack(f">{count}I", *moved))
        elif kind == b"co64":
            count = struct.unpack(">I", stbl[body + 4:body + 8])[0]
            offsets = struct.unpack(f">{count}Q", stbl[body + 8:body + 8 + 8 * count])
            box = _full(b"co64", 0, struct.pack(">I", count), struct.pack(f">{count}Q", *(o + shift for o in offsets)))
        out += box
    return bytes(out)


def _rebuild(data: bytes, start: int, end: int, path: tuple[bytes, ...], edit) -> bytes:
    """The boxes in data[start:end] with `edit(kind, body_bytes)` applied to
    each container along `path` (outermost first)."""
    out = bytearray()
    for kind, box_start, body, box_end in _boxes(data, start, end):
        if path and kind == path[0]:
            inner = _rebuild(data, body, box_end, path[1:], edit) if len(path) > 1 else data[body:box_end]
            out += _box(kind, edit(kind, inner))
        else:
            out += data[box_start:box_end]
    return bytes(out)


def _plan(moov: bytes, audio_start: int, audio_length: int, chapters: list[Chapter],
          tags: dict[str, str], cover: bytes | None) -> tuple[bytes, bytes, bytes]:
    """What goes around the audio: (ftyp + mdat header, chapter samples, moov).

    `moov` is the encoder's moov box; the audio is the `audio_length` bytes
    that sat at `audio_start` in its file. Only these small parts are held in
    memory - the audio itself is copied by the caller.
    """
    _, _, moov_body, moov_end = next(_boxes(moov, 0, len(moov)))
    traks = [box for box in _boxes(moov, moov_body, moov_end) if box[0] == b"trak"]
    if len(traks) != 1:
        raise ValueError(f"expected one audio track, found {len(traks)}")
    mvhd = _child(moov, moov_body, moov_end, b"mvhd")
    if mvhd is None or moov[mvhd[1]] != 0:
        raise ValueError("missing or 64-bit movie header")
    timescale, duration = struct.unpack(">II", moov[mvhd[1] + 12:mvhd[1] + 20])
    total = duration / timescale

    marks = sorted((c for c in chapters if 0 <= c.start < total), key=lambda c: c.start)
    if not marks:
        marks = [Chapter(tags.get("title", ""), 0.0)]
    elif marks[0].start > 0:
        # A gap before the first mark would show as an untitled chapter.
        marks[0] = Chapter(marks[0].title, 0.0)
    starts_ms = [round(c.start * 1000) for c in marks]
    total_ms = round(total * 1000)
    durations = [max(1, b - a) for a, b in zip(starts_ms, starts_ms[1:] + [total_ms])]
    samples = [_chapter_sample(c.title) for c in marks]
    sample_bytes = b"".join(samples)

    ftyp = _box(b"ftyp", b"M4B ", struct.pack(">I", 0), b"M4B ", b"M4A ", b"mp42", b"isom")
    body_length = audio_length + len(sample_bytes)
    if body_length + 8 > 0xFFFFFFFF:
        mdat_header = struct.pack(">I4sQ", 1, b"mdat", body_length + 16)
    else:
        mdat_header = struct.pack(">I4s", body_length + 8, b"mdat")
    new_audio_start = len(ftyp) + len(mdat_header)
    shift = new_audio_start - audio_start
    text_offsets = []
    at = new_audio_start + audio_length
    for sample in samples:
        text_offsets.append(at)
        at += len(sample)

    next_id = struct.unpack(">I", moov[mvhd[1] + 96:mvhd[1] + 100])[0]
    chapter_id = max(next_id, 2)

    def edit(kind: bytes, body: bytes) -> bytes:
        if kind == b"stbl":
            return _rewrite_stco(body, shift)
        if kind == b"trak":
            # The audio track lists the chapter track (tref/chap), after tkhd.
            out = bytearray()
            for k, s, b, e in _boxes(body, 0, len(body)):
                if k == b"tref":
                    continue
                out += body[s:e]
                if k == b"tkhd":
                    out += _box(b"tref", _box(b"chap", struct.pack(">I", chapter_id)))
            return bytes(out)
        return body

    moov_inner = _rebuild(moov, moov_body, moov_end, (b"trak", b"mdia", b"minf", b"stbl"), edit)
    # Drop the encoder's own tags; ours replace them. Next track id moves on.
    kept = bytearray()
    for kind, s, b, e in _boxes(moov_inner, 0, len(moov_inner)):
        if kind == b"udta":
            continue
        box = moov_inner[s:e]
        if kind == b"mvhd":
            box = box[:8 + 96] + struct.pack(">I", chapter_id + 1) + box[8 + 100:]
        kept += box
    kept += _chapter_trak(chapter_id, durations, [len(s) for s in samples], text_offsets, timescale, tags.get("language", ""))
    kept += _udta(tags, cover)
    return ftyp + mdat_header, sample_bytes, _box(b"moov", bytes(kept))


def _top_level(read_at, size: int) -> dict[bytes, tuple[int, int, int]]:
    """{kind: (box start, body start, box end)} of a file's top-level boxes,
    reading only their headers."""
    found: dict[bytes, tuple[int, int, int]] = {}
    at = 0
    while at + 8 <= size:
        head = read_at(at, 16)
        length, kind = struct.unpack(">I4s", head[:8])
        body = at + 8
        if length == 1:
            length = struct.unpack(">Q", head[8:16])[0]
            body = at + 16
        elif length == 0:
            length = size - at
        if length < 8 or at + length > size:
            raise ValueError(f"damaged box {kind!r} at {at}")
        found.setdefault(kind, (at, body, at + length))
        at += length
    if not all(kind in found for kind in (b"ftyp", b"moov", b"mdat")):
        raise ValueError("not an MPEG-4 audio file")
    return found


def add_chapters(m4a: bytes, chapters: list[Chapter], tags: dict[str, str], cover: bytes | None = None) -> bytes:
    """An AAC .m4a (one audio track) as an .m4b with chapters and tags."""
    boxes = _top_level(lambda at, n: m4a[at:at + n], len(m4a))
    moov_start, _, moov_end = boxes[b"moov"]
    _, audio_start, audio_end = boxes[b"mdat"]
    head, samples, moov = _plan(m4a[moov_start:moov_end], audio_start, audio_end - audio_start, chapters, tags, cover)
    return head + m4a[audio_start:audio_end] + samples + moov


def _add_chapters_file(source: str, target: str, chapters: list[Chapter], tags: dict[str, str], cover: bytes | None) -> None:
    """`add_chapters` from file to file, the audio copied a megabyte at a
    time: a ten-hour book is about 300 MB of AAC, never held in memory."""
    with open(source, "rb") as src:
        size = os.fstat(src.fileno()).st_size
        boxes = _top_level(lambda at, n: os.pread(src.fileno(), n, at), size)
        moov_start, _, moov_end = boxes[b"moov"]
        _, audio_start, audio_end = boxes[b"mdat"]
        moov = os.pread(src.fileno(), moov_end - moov_start, moov_start)
        head, samples, new_moov = _plan(moov, audio_start, audio_end - audio_start, chapters, tags, cover)
        with open(target, "wb") as out:
            out.write(head)
            at = audio_start
            while at < audio_end:
                piece = os.pread(src.fileno(), min(1 << 20, audio_end - at), at)
                if not piece:
                    raise ValueError("audio ended early")
                out.write(piece)
                at += len(piece)
            out.write(samples)
            out.write(new_moov)


def read_chapters(m4b: bytes) -> list[Chapter]:
    """The chapter titles and starts as written by `add_chapters` - for tests
    and for a check after writing."""
    moov = _child(m4b, 0, len(m4b), b"moov")
    if not moov:
        return []
    for kind, s, body, end in _boxes(m4b, moov[1], moov[2]):
        if kind != b"trak":
            continue
        mdia = _child(m4b, body, end, b"mdia")
        hdlr = _child(m4b, mdia[1], mdia[2], b"hdlr")
        if m4b[hdlr[1] + 8:hdlr[1] + 12] != b"text":
            continue
        mdhd = _child(m4b, mdia[1], mdia[2], b"mdhd")
        scale = struct.unpack(">I", m4b[mdhd[1] + 12:mdhd[1] + 16])[0]
        minf = _child(m4b, mdia[1], mdia[2], b"minf")
        stbl = _child(m4b, minf[1], minf[2], b"stbl")
        table = {k: m4b[b:e] for k, _, b, e in _boxes(m4b, stbl[1], stbl[2])}
        n = struct.unpack(">I", table[b"stts"][4:8])[0]
        deltas = []
        for i in range(n):
            count, delta = struct.unpack(">II", table[b"stts"][8 + 8 * i:16 + 8 * i])
            deltas += [delta] * count
        offsets = struct.unpack(f">{len(deltas)}I", table[b"stco"][8:8 + 4 * len(deltas)])
        out, clock = [], 0
        for offset, delta in zip(offsets, deltas):
            length = struct.unpack(">H", m4b[offset:offset + 2])[0]
            out.append(Chapter(m4b[offset + 2:offset + 2 + length].decode("utf-8"), clock / scale))
            clock += delta
        return out
    return []


def write_m4b(wav_path: str, path: str, chapters: list[Chapter], tags: dict[str, str],
              cover: bytes | None = None, bitrate: int = 64000) -> None:
    """Encode `wav_path` to AAC with macOS's own encoder and write the .m4b
    at `path`, atomically: a stopped or failed export leaves no file."""
    folder = os.path.dirname(path)
    fd, encoded = tempfile.mkstemp(suffix=".m4a", dir=folder)
    os.close(fd)
    fd, staged = tempfile.mkstemp(suffix=".m4b", dir=folder)
    os.close(fd)
    try:
        subprocess.run(
            ["/usr/bin/afconvert", "-f", "m4af", "-d", "aac", "-b", str(bitrate), wav_path, encoded],
            check=True, capture_output=True, timeout=3600,
        )
        _add_chapters_file(encoded, staged, chapters, tags, cover)
        os.replace(staged, path)
    finally:
        for leftover in (encoded, staged):
            if os.path.exists(leftover):
                os.remove(leftover)
