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
    metadata_extra: str = "",
    manifest_extra: str = "",
    extra_members: dict[str, bytes] | None = None,
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
      <metadata><dc:title>{title}</dc:title>{metadata_extra}</metadata>
      <manifest>{''.join(manifest_lines)}{manifest_extra}</manifest>
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
        for member, payload in (extra_members or {}).items():
            archive.writestr(member, payload, compress_type=ZIP_DEFLATED)
        if unsafe_entry:
            archive.writestr(unsafe_entry, "malicious", compress_type=ZIP_DEFLATED)
    return path


# A book with a publisher's contents tree (HIG 3.25): a part page, a chapter
# with sections found by id - on the heading, on a wrapper, and on an empty
# `<a>` inside a paragraph - a second chapter, and a cover with no words.
# Invented titles, like every fixture here.
CONTENTS_PAGES = {
    "part": (
        "part.xhtml",
        """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <p>Phần sách</p><h1>Những con đường</h1><p>Lời dẫn của phần một.</p>
        </body></html>""",
    ),
    "chapter-1": (
        "chapter-1.xhtml",
        """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <p>Chương 1</p><h1>Bến sông</h1><p>Đoạn mở đầu của chương.</p>
        <h2 id="s-1">Con thuyền</h2><p>Đoạn nói về con thuyền.</p>
        <section id="s-2"><h3>Mái chèo</h3><p>Đoạn nói về mái chèo.</p></section>
        <p><a id="s-3"/>Câu có một mốc đứng trước chữ đầu.</p>
        </body></html>""",
    ),
    "chapter-2": (
        "chapter-2.xhtml",
        """<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <h1>Bờ bên kia</h1><p>Đoạn cuối của sách thử.</p>
        </body></html>""",
    ),
    "cover": (
        "cover.xhtml",
        """<html xmlns="http://www.w3.org/1999/xhtml"><body><div/></body></html>""",
    ),
}

CONTENTS_NAV = """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>
<nav epub:type="toc"><ol>
  <li><a href="cover.xhtml">Bìa</a><ol><li><a href="chapter-2.xhtml#none">Lời tựa lạc chỗ</a></li></ol></li>
  <li><a href="part.xhtml">Phần Một: Những con đường</a><ol>
    <li><a href="chapter-1.xhtml">Chương 1 Bến sông</a><ol>
      <li><a href="chapter-1.xhtml#s-1">Con thuyền</a><ol>
        <li><a href="chapter-1.xhtml#s-2">Mái chèo</a></li>
      </ol></li>
      <li><a href="chapter-1.xhtml#s-3">Mốc giữa đoạn</a></li>
      <li><a href="chapter-1.xhtml#khong-co">Mốc không có trên trang</a></li>
    </ol></li>
    <li><a href="chapter-2.xhtml">Chương 2 Bờ bên kia</a></li>
  </ol></li>
</ol></nav>
<nav epub:type="landmarks"><ol><li><a href="chapter-1.xhtml">Không phải mục lục</a></li></ol></nav>
</body></html>"""

CONTENTS_NCX = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap>
  <navPoint id="n0"><navLabel><text>Bìa</text></navLabel><content src="cover.xhtml"/>
    <navPoint id="n0a"><navLabel><text>Lời tựa lạc chỗ</text></navLabel><content src="chapter-2.xhtml#none"/></navPoint>
  </navPoint>
  <navPoint id="n1"><navLabel><text>Phần Một: Những con đường</text></navLabel><content src="part.xhtml"/>
    <navPoint id="n2"><navLabel><text>Chương 1 Bến sông</text></navLabel><content src="chapter-1.xhtml"/>
      <navPoint id="n3"><navLabel><text>Con thuyền</text></navLabel><content src="chapter-1.xhtml#s-1"/>
        <navPoint id="n4"><navLabel><text>Mái chèo</text></navLabel><content src="chapter-1.xhtml#s-2"/></navPoint>
      </navPoint>
      <navPoint id="n5"><navLabel><text>Mốc giữa đoạn</text></navLabel><content src="chapter-1.xhtml#s-3"/></navPoint>
      <navPoint id="n6"><navLabel><text>Mốc không có trên trang</text></navLabel><content src="chapter-1.xhtml#khong-co"/></navPoint>
    </navPoint>
    <navPoint id="n7"><navLabel><text>Chương 2 Bờ bên kia</text></navLabel><content src="chapter-2.xhtml"/></navPoint>
  </navPoint>
</navMap></ncx>"""


def make_epub_with_contents(
    root: Path,
    *,
    name: str = "contents.epub",
    navigation: str = "nav",
    nav_override: str | None = None,
) -> Path:
    """The contents fixture, its tree as an EPUB 3 nav (`navigation="nav"`),
    an EPUB 2 NCX (`"ncx"`) or none at all (`"none"`)."""

    pages = {key: CONTENTS_PAGES[key] for key in ("chapter-1", "chapter-2")}
    extra = {f"OEBPS/{href}": content.encode() for key, (href, content) in CONTENTS_PAGES.items() if key not in pages}
    manifest = "".join(
        f'<item id="{key}" href="{href}" media-type="application/xhtml+xml"/>'
        for key, (href, _content) in CONTENTS_PAGES.items() if key not in pages
    )
    if navigation == "nav":
        extra["OEBPS/nav.xhtml"] = (nav_override or CONTENTS_NAV).encode()
        manifest += '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    elif navigation == "ncx":
        extra["OEBPS/toc.ncx"] = (nav_override or CONTENTS_NCX).encode()
        manifest += '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
    return make_epub(
        root,
        name=name,
        spine=("cover", "part", "chapter-1", "chapter-2"),
        chapter_overrides={key: content for key, (_href, content) in pages.items()},
        manifest_extra=manifest,
        extra_members=extra,
    )
