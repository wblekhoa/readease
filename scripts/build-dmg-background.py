#!/usr/bin/env python3
"""Draw the disk image's backdrop: app on the left, Applications on the
right, the brand-blue arrow between them, one line saying what to do.

    .venv/bin/python scripts/build-dmg-background.py

Writes `assets/branding/dmg-background.png` (660x400) and its `@2x` twin,
which `build-release-app.sh` folds into one HiDPI TIFF for `dmgbuild`. The
icon slots match `scripts/dmg-settings.py`: the image only draws around
them. The caption is set in the system's own San Francisco - a Finder
window is the Mac's, not the app's, and the app's web fonts ship only as
subsets that PIL cannot fall back between; the colours are the design
system's (blue b100, the light neutral ramp).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_FONT = Path("/System/Library/Fonts/SFNS.ttf")
OUT = ROOT / "assets/branding"

W, H = 660, 400          # the Finder window's content area (dmg-settings.py)
SCALE = 2                # drawn at 2x, saved at both
APP_X, APPS_X, ICON_Y = 165, 495, 175   # icon centres, as dmg-settings.py places them

PAPER = (247, 248, 251)  # light neutral, close to the app's own desk
INK = (31, 36, 51)
MUTE = (107, 114, 128)
BRAND = (43, 82, 212)    # blue b100, the brand since 21/09


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """San Francisco at a named weight (it is a variable font)."""
    face = ImageFont.truetype(str(SYSTEM_FONT), size * SCALE)
    face.set_variation_by_name(weight)
    return face


def draw() -> Image.Image:
    image = Image.new("RGB", (W * SCALE, H * SCALE), PAPER)
    d = ImageDraw.Draw(image)
    s = SCALE

    # The arrow: a bar and a chevron, rounded, in the brand's blue.
    y = ICON_Y * s
    x0, x1 = (APP_X + 92) * s, (APPS_X - 92) * s
    stroke = 6 * s
    d.line([(x0, y), (x1 - 4 * s, y)], fill=BRAND, width=stroke)
    head = 22 * s
    d.line([(x1 - head, y - head), (x1, y), (x1 - head, y + head)], fill=BRAND, width=stroke, joint="curve")
    for cx, cy in ((x0, y), (x1 - head, y - head), (x1 - head, y + head)):
        d.ellipse([cx - stroke / 2, cy - stroke / 2, cx + stroke / 2, cy + stroke / 2], fill=BRAND)

    # One line in each language, under the icons and their labels.
    title = font("Medium", 16)
    sub = font("Regular", 13)
    line1 = "Kéo ReadEase vào Applications để cài"
    line2 = "Drag ReadEase into Applications to install"
    for text, f, fill, yy in ((line1, title, INK, 318), (line2, sub, MUTE, 344)):
        width = d.textlength(text, font=f)
        d.text(((W * s - width) / 2, yy * s), text, font=f, fill=fill)
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    image = draw()
    image.save(OUT / "dmg-background@2x.png", optimize=True)
    image.resize((W, H), Image.LANCZOS).save(OUT / "dmg-background.png", optimize=True)
    print(f"DMG_BACKGROUND PASS {W}x{H} and @2x -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
