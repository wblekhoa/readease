"""What a shelf needs from a cover: a small picture, not the print master.

The owner's own library carries a 2 MB, 1296x1944 PNG as one cover - which
the shelf shows 150 px wide, and which would otherwise travel base64-encoded
down the same pipe as the audio. Anything bigger than a thumbnail is
re-encoded to a JPEG of COVER_HEIGHT_PX; small files and SVGs pass through.
"""
from __future__ import annotations

from io import BytesIO

import PIL.Image

COVER_HEIGHT_PX = 600
SHRINK_ABOVE_BYTES = 300_000
SHRINK_ABOVE_HEIGHT = 900
_RASTER = {"image/png", "image/jpeg", "image/gif"}


def shrink_cover(payload: bytes, media_type: str) -> tuple[bytes, str]:
    """Return the cover at shelf size; on any decoding trouble, the original."""

    if media_type not in _RASTER:
        return payload, media_type
    try:
        with PIL.Image.open(BytesIO(payload)) as image:
            _width, height = image.size
            if len(payload) <= SHRINK_ABOVE_BYTES and height <= SHRINK_ABOVE_HEIGHT:
                return payload, media_type
            image.thumbnail((COVER_HEIGHT_PX * 4, COVER_HEIGHT_PX))
            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=82, optimize=True)
            return buffer.getvalue(), "image/jpeg"
    except (OSError, ValueError, MemoryError):
        return payload, media_type
