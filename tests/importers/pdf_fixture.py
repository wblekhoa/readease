"""Small dependency-free PDF fixtures for importer and UI tests."""

from __future__ import annotations

from base64 import b64decode
from pathlib import Path


_ENCRYPTED_PDF = b64decode(
    "JVBERi0xLjcKJcK1wrYKJSBXcml0dGVuIGJ5IE11UERGIDEuMjguMgoKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFIvSW5mbzw8L1Byb2R1Y2VyPENEMTkyRThERkIxRDdBMDcxRjRFNTY5NDZGRUQwOTNFMEQ4NjYzNDgyQTc1QjVDRDNEMEI2MjQ2MkVFNUJENUI+Pj4+PgplbmRvYmoKCjIgMCBvYmoKPDwvVHlwZS9QYWdlcy9Db3VudCAxL0tpZHNbNCAwIFJdPj4KZW5kb2JqCgozIDAgb2JqCjw8L0ZvbnQ8PC9oZWx2IDUgMCBSPj4+PgplbmRvYmoKCjQgMCBvYmoKPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCA1OTUgODQyXS9Sb3RhdGUgMC9SZXNvdXJjZXMgMyAwIFIvUGFyZW50IDIgMCBSL0NvbnRlbnRzWzYgMCBSXT4+CmVuZG9iagoKNSAwIG9iago8PC9UeXBlL0ZvbnQvU3VidHlwZS9UeXBlMS9CYXNlRm9udC9IZWx2ZXRpY2EvRW5jb2RpbmcvV2luQW5zaUVuY29kaW5nPj4KZW5kb2JqCgo2IDAgb2JqCjw8L0xlbmd0aCAxNDQvRmlsdGVyL0ZsYXRlRGVjb2RlPj4Kc3RyZWFtCgLqmI3zygE4LqQR+NpF4ncabC3S1moquo3xX51Y3FJL3wmra20EmE5oZb5tUXil9U4cflQKim+7536DTXtim1G9rKe9c0Jir4n5meG61cgA3elx4Wnw2soC98WbqS/qySDOvW0oBj8u4iqNxsejC+Vow+VvkUQMgxGjHYKSUm6Qpo/m0r8qfLekPYMQG91A8QplbmRzdHJlYW0KZW5kb2JqCgp4cmVmCjAgNwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwNDIgMDAwMDAgbiAKMDAwMDAwMDE3MiAwMDAwMCBuIAowMDAwMDAwMjI0IDAwMDAwIG4gCjAwMDAwMDAyNjUgMDAwMDAgbiAKMDAwMDAwMDM3MiAwMDAwMCBuIAowMDAwMDAwNDYxIDAwMDAwIG4gCgp0cmFpbGVyCjw8L1NpemUgNy9Sb290IDEgMCBSL0lEWzw0RTIwQzNBQUMzQjFDMkIwNTI0OTBFQzI5QTE0MjhDMj48NjNFMUE4NzUzMjE5MDlERDFBREQzQTM0NDM4OTZCN0U+XS9FbmNyeXB0PDwvRmlsdGVyL1N0YW5kYXJkL1IgNi9WIDUvTGVuZ3RoIDI1Ni9QIC00L0VuY3J5cHRNZXRhZGF0YSB0cnVlL1N0bUYvU3RkQ0YvU3RyRi9TdGRDRi9DRjw8L1N0ZENGPDwvQXV0aEV2ZW50L0RvY09wZW4vQ0ZNL0FFU1YzL0xlbmd0aCAzMj4+Pj4vTzw2ODQzQzQxNEI2QTAzRDVDRTU3ODJGRTdFRDk1NjYwQzYwQTM4RTlCREI5MjZFNDZCMTQ4OThDQTc4NEM5NDU4NkRFNkU4OTBCNEQ0QzQyNUM1RDVCOTU1MjA5N0UwQzc+L1U8RTNCMkYxN0YxQTFCRTA4MzUwQkMyMEExMTVGREZERDBGRTJFRUQ4Q0YyNEQyQzRCRjlDQkM3RjE3OTI4N0ZBNDJBOEVBQkM5NEEwRTA3Mzc3QTlCQzM3OTcyNjE4RERFPi9PRTw2N0EzNDY2N0VEQTY3MTUxMzVFQzdERDk4MTEzOTNDMUMwNjc0QUExRTUyQzY2QTUwOTZBMDI2MDdFODcxMDc0Pi9VRTw5NjQ5OTQ1NjVDNThCMzdCRTZERTI5RkUzRDExMDg1NzA4RjhEQjNFRTUwNzhFRjE1NTBBRkE2RjYwQjg5Q0ZEPi9QZXJtczxDMUE4Njg5NEE1QjgwQjI0OThBNkY1ODIzQTBDQTdCQT4+Pj4+CnN0YXJ0eHJlZgo2NzQKJSVFT0YK"
)


def _pdf_text(value: str) -> str:
    return f"<FEFF{value.encode('utf-16-be').hex().upper()}>"


def _pdf_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(commands: str) -> str:
    payload = commands.encode("ascii")
    return f"<< /Length {len(payload)} >>\nstream\n{commands}\nendstream"


def _serialize_pdf(objects: list[str], *, root: int, info: int) -> bytes:
    payload = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{object_number} 0 obj\n{body}\nendobj\n".encode("ascii"))
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {root} 0 R "
            f"/Info {info} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(payload)


def make_pdf(
    path: Path,
    *,
    pages: tuple[tuple[tuple[float, float, str], ...], ...],
    title: str = "",
    outline_titles: tuple[str, ...] = (),
) -> Path:
    """Write a tiny text PDF with optional top-level bookmarks."""

    if outline_titles and len(outline_titles) != len(pages):
        raise ValueError("outline_titles must match pages")

    page_ids = tuple(3 + index * 2 for index in range(len(pages)))
    content_ids = tuple(page_id + 1 for page_id in page_ids)
    font_id = 3 + len(pages) * 2
    outline_root_id = font_id + 1 if outline_titles else 0
    outline_ids = tuple(
        outline_root_id + 1 + index for index in range(len(outline_titles))
    )
    info_id = (outline_ids[-1] if outline_ids else font_id) + 1

    catalog_outline = f" /Outlines {outline_root_id} 0 R /PageMode /UseOutlines" if outline_titles else ""
    objects = [
        f"<< /Type /Catalog /Pages 2 0 R{catalog_outline} >>",
        f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] >>",
    ]
    for page_id, content_id, lines in zip(page_ids, content_ids, pages, strict=True):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        commands = "\n".join(
            f"BT /F1 12 Tf {x:g} {y:g} Td ({_pdf_literal(text)}) Tj ET"
            for x, y, text in lines
        )
        objects.append(_stream(commands))
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    if outline_titles:
        objects.append(
            f"<< /Type /Outlines /Count {len(outline_ids)} "
            f"/First {outline_ids[0]} 0 R /Last {outline_ids[-1]} 0 R >>"
        )
        for index, (outline_id, outline_title, page_id) in enumerate(
            zip(outline_ids, outline_titles, page_ids, strict=True)
        ):
            links = []
            if index:
                links.append(f"/Prev {outline_ids[index - 1]} 0 R")
            if index + 1 < len(outline_ids):
                links.append(f"/Next {outline_ids[index + 1]} 0 R")
            objects.append(
                f"<< /Title {_pdf_text(outline_title)} /Parent {outline_root_id} 0 R "
                f"/Dest [{page_id} 0 R /XYZ 0 792 1] {' '.join(links)} >>"
            )
    objects.append(f"<< /Title {_pdf_text(title)} >>")
    path.write_bytes(_serialize_pdf(objects, root=1, info=info_id))
    return path


def make_text_pdf(directory: Path, *, with_outline: bool = True) -> Path:
    return make_pdf(
        directory / "sach-thu.pdf",
        pages=(
            (
                (250, 720, "Ben phai cua dong dau tien."),
                (50, 720, "Ben trai cua dong dau tien."),
                (50, 662, "Noi dung o phia duoi trang mot."),
            ),
            ((50, 720, "Noi dung cua trang hai du dai."),),
        ),
        title="Sách đọc thử",
        outline_titles=("Mở đầu", "Tiếp theo") if with_outline else (),
    )


def make_blank_pdf(path: Path) -> Path:
    return make_pdf(path, pages=((),))


def make_short_pdf(path: Path) -> Path:
    return make_pdf(path, pages=(((50, 720, "Qua ngan"),),))


def make_encrypted_pdf(path: Path) -> Path:
    path.write_bytes(_ENCRYPTED_PDF)
    return path
