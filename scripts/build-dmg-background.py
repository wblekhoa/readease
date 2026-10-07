#!/usr/bin/env python3
"""Draw the disk image's backdrop (redesigned 07/10/2026).

    .venv/bin/python scripts/build-dmg-background.py [--version 0.1.19] [--out DIR]

A welcome, not a diagram: a quiet dotted paper, the app on the left and
Applications on the right (`scripts/dmg-settings.py` places both icons; the
picture only draws around them), a hand-drawn ink arrow between them with a
small brand-blue sound wave under it - words becoming a voice - a few
floating marks at the edges, a two-line welcome and the version.

Writes `dmg-background.png` (660x400) and its `@2x` twin into
`assets/branding` (or `--out`), which dmgbuild folds into one HiDPI TIFF.
The version defaults to `app/src-tauri/tauri.conf.json`; the release build
draws the picture for the version it packs. The type is the system's own San
Francisco - a Finder window is the Mac's, not the app's - and the colours are
the design system's (blue b100, the light neutral ramp).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_FONT = Path("/System/Library/Fonts/SFNS.ttf")
OUT = ROOT / "assets/branding"

W, H = 660, 400          # the Finder window's content area (dmg-settings.py)
S = 2                    # drawn at 2x, saved at both
APP_X, APPS_X, ICON_Y = 165, 495, 150   # icon centres, as dmg-settings.py places them

PAPER = (248, 248, 246)
DOT = (222, 224, 228)
INK = (28, 32, 44)
MUTE = (112, 118, 130)
BRAND = (43, 82, 212)    # blue b100, the brand since 21/09
BRAND_SOFT = (122, 148, 236)
AMBER = (238, 160, 62)
CORAL = (226, 96, 74)
GREEN = (52, 160, 108)


def font(weight: str, size: float) -> ImageFont.FreeTypeFont:
    """San Francisco at a named weight (it is a variable font)."""
    face = ImageFont.truetype(str(SYSTEM_FONT), round(size * S))
    face.set_variation_by_name(weight)
    return face


def centred(d: ImageDraw.ImageDraw, text: str, f, y: float, fill, tracking: float = 0) -> None:
    """One line, centred, with optional letter-spacing in points."""
    gap = tracking * S
    width = sum(d.textlength(ch, font=f) for ch in text) + gap * (len(text) - 1)
    x = (W * S - width) / 2
    for ch in text:
        d.text((x, y * S), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + gap


def sparkle(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill) -> None:
    """A four-pointed star: two pinched diamonds."""
    pts = []
    for i in range(16):
        a = math.pi / 8 * i
        rr = r if i % 4 == 0 else r * (0.18 if i % 2 else 0.32)
        pts.append(((cx + rr * math.cos(a)) * S, (cy + rr * math.sin(a)) * S))
    d.polygon(pts, fill=fill)


def bars(d: ImageDraw.ImageDraw, x: float, cy: float, heights, fill, w: float = 3.2, gap: float = 3.2) -> None:
    for h in heights:
        d.rounded_rectangle([x * S, (cy - h / 2) * S, (x + w) * S, (cy + h / 2) * S], radius=w / 2 * S, fill=fill)
        x += w + gap


def bezier(p0, p1, p2, steps: int = 64):
    for i in range(steps + 1):
        t = i / steps
        yield ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
               (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])


def draw(version: str) -> Image.Image:
    image = Image.new("RGB", (W * S, H * S), PAPER)
    d = ImageDraw.Draw(image)

    # Dotted paper.
    for gx in range(11, W, 22):
        for gy in range(11, H, 22):
            d.ellipse([(gx - 0.9) * S, (gy - 0.9) * S, (gx + 0.9) * S, (gy + 0.9) * S], fill=DOT)

    # Floating marks at the edges, each a little soft, none near an icon.
    marks = Image.new("RGBA", image.size, (0, 0, 0, 0))
    m = ImageDraw.Draw(marks)
    # top-left: a sound-wave chip
    m.rounded_rectangle([40 * S, 38 * S, 104 * S, 66 * S], radius=14 * S, fill=(255, 255, 255, 255), outline=(226, 229, 236, 255), width=S)
    bars(m, 52, 52, (6, 12, 16, 10, 14, 7, 4), BRAND + (255,), w=2.6, gap=3.4)
    # bottom-left: the letters the voice reads
    m.rounded_rectangle([48 * S, 300 * S, 92 * S, 344 * S], radius=12 * S, fill=(255, 255, 255, 255), outline=(226, 229, 236, 255), width=S)
    m.text((70 * S, 322 * S), "Aa", font=font("Semibold", 19), fill=INK + (255,), anchor="mm")
    # right edge: sparkles and a small play mark
    sparkle(m, 602, 58, 15, BRAND + (255,))
    sparkle(m, 626, 86, 6, AMBER + (255,))
    m.ellipse([586 * S, 304 * S, 620 * S, 338 * S], fill=(255, 255, 255, 255), outline=(226, 229, 236, 255), width=S)
    m.polygon([(599 * S, 313 * S), (599 * S, 329 * S), (611 * S, 321 * S)], fill=CORAL + (255,))
    sparkle(m, 28, 228, 5, GREEN + (255,))
    shadow = marks.split()[3].filter(ImageFilter.GaussianBlur(5 * S)).point(lambda a: a * 0.10)
    image.paste((40, 48, 70), (0, 3 * S), shadow)
    image.paste(marks, (0, 0), marks)
    d = ImageDraw.Draw(image)

    # The arrow: a trail of dots, then one ink stroke with a bend in it.
    for i, (dx, shade) in enumerate(((246, 196), (256, 150), (266, 90))):
        r = 2.4 + i * 0.5
        d.ellipse([(dx - r) * S, (ICON_Y - r) * S, (dx + r) * S, (ICON_Y + r) * S], fill=(shade, shade, shade + 8))
    p0, p1, p2 = (280, ICON_Y + 8), (338, ICON_Y - 36), (404, ICON_Y - 2)
    pts = [(x * S, y * S) for x, y in bezier(p0, p1, p2)]
    stroke = 5.2 * S
    d.line(pts, fill=INK, width=round(stroke), joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - stroke / 2, y - stroke / 2, x + stroke / 2, y + stroke / 2], fill=INK)
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for side in (1, -1):
        a = angle + math.pi - side * 0.62
        tip = (p2[0] * S, p2[1] * S)
        end = (tip[0] + 17 * S * math.cos(a), tip[1] + 17 * S * math.sin(a))
        d.line([tip, end], fill=INK, width=round(stroke))
        d.ellipse([end[0] - stroke / 2, end[1] - stroke / 2, end[0] + stroke / 2, end[1] + stroke / 2], fill=INK)
    # ... and under it, the voice.
    heights = (5, 9, 14, 8, 12, 6, 10, 4)
    total = len(heights) * 3.2 + (len(heights) - 1) * 3.2
    bars(d, (W - total) / 2 + 12, ICON_Y + 38, heights, BRAND_SOFT)

    # The welcome.
    centred(d, "Chào mừng đến với ReadEase", font("Bold", 25), 284, INK)
    centred(d, "Kéo ReadEase vào Applications để bắt đầu", font("Regular", 13.5), 322, MUTE)
    centred(d, "DRAG THE APP INTO APPLICATIONS TO GET STARTED", font("Medium", 9.5), 344, MUTE, tracking=1.4)
    centred(d, f"v{version}", font("Medium", 10), 372, (150, 155, 166), tracking=0.6)
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    version = args.version or json.loads((ROOT / "app/src-tauri/tauri.conf.json").read_text())["version"]
    args.out.mkdir(parents=True, exist_ok=True)
    image = draw(version)
    image.save(args.out / "dmg-background@2x.png", optimize=True)
    image.resize((W, H), Image.LANCZOS).save(args.out / "dmg-background.png", optimize=True)
    print(f"DMG_BACKGROUND PASS {W}x{H} and @2x, v{version} -> {args.out}")


if __name__ == "__main__":
    main()
