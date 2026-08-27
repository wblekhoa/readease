from __future__ import annotations

from pathlib import Path
import struct
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile
import zlib


CONTAINER_XML = """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def make_png(width: int, height: int) -> bytes:
    """Build a tiny valid RGBA fixture without adding an image dependency."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    row = b"\x00" + (b"\xd4\x25\x25\xff" * width)
    pixels = row * height
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            chunk("IHDR".encode(), struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)),
            chunk("IDAT".encode(), zlib.compress(pixels)),
            chunk("IEND".encode(), b""),
        )
    )


def make_epub(
    root: Path,
    *,
    name: str = "fixture.epub",
    title: str = "Sách thử nghiệm",
    spine: tuple[str, ...] = ("chapter-1", "chapter-2"),
    unsafe_entry: str | None = None,
    unsafe_href: str | None = None,
    empty_chapters: bool = False,
    chapter_overrides: dict[str, str | bytes] | None = None,
    image_entries: dict[str, tuple[bytes, str]] | None = None,
) -> Path:
    path = root / name
    chapters = {
        "chapter-1": (
            "chapter-1.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body>
            <h1>Một</h1><p>Nội dung chương một.</p>
            </body></html>""",
        ),
        "chapter-2": (
            "chapter-2.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body>
            <h1>Hai</h1><p>Nội dung chương hai.</p>
            <script>window.alert('không được đọc')</script>
            <style>.secret { display: block }</style>
            <p hidden="hidden">Nội dung ẩn.</p>
            <p aria-hidden="true">Cũng bị ẩn.</p>
            </body></html>""",
        ),
    }
    if empty_chapters:
        chapters = {
            key: (href, "<html xmlns=\"http://www.w3.org/1999/xhtml\"><body/></html>")
            for key, (href, _content) in chapters.items()
        }
    if chapter_overrides:
        chapters = {
            key: (href, chapter_overrides.get(key, content))
            for key, (href, content) in chapters.items()
        }

    manifest_lines = []
    for item_id, (href, _content) in chapters.items():
        if unsafe_href and item_id == spine[0]:
            href = unsafe_href
        manifest_lines.append(
            f'<item id="{item_id}" href="{href}" media-type="application/xhtml+xml"/>'
        )
    for index, (href, (_payload, media_type)) in enumerate(
        (image_entries or {}).items()
    ):
        manifest_lines.append(
            f'<item id="image-{index}" href="{href}" media-type="{media_type}"/>'
        )
    spine_lines = [f'<itemref idref="{item_id}"/>' for item_id in spine]
    opf = f"""<?xml version="1.0"?>
    <package xmlns="http://www.idpf.org/2007/opf"
             xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0">
      <metadata><dc:title>{title}</dc:title></metadata>
      <manifest>{''.join(manifest_lines)}</manifest>
      <spine>{''.join(spine_lines)}</spine>
    </package>
    """

    with ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER_XML, compress_type=ZIP_DEFLATED)
        archive.writestr("OEBPS/content.opf", opf, compress_type=ZIP_DEFLATED)
        for _item_id, (href, content) in chapters.items():
            archive.writestr(f"OEBPS/{href}", content, compress_type=ZIP_DEFLATED)
        for href, (payload, _media_type) in (image_entries or {}).items():
            archive.writestr(f"OEBPS/{href}", payload, compress_type=ZIP_DEFLATED)
        if unsafe_entry:
            archive.writestr(unsafe_entry, "malicious", compress_type=ZIP_DEFLATED)
    return path
