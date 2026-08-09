"""Обложки для YouTube: генерация 1280x720 через Pillow (локально, без ключей)."""
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
PALETTES = [
    ((30, 27, 75), (76, 29, 149)),
    ((12, 74, 110), (190, 24, 93)),
    ((16, 23, 42), (30, 58, 138)),
    ((59, 7, 100), (134, 25, 143)),
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    from app.services.fonts import find_font

    return ImageFont.truetype(find_font(), size)


def generate_cover(title: str, niche: str, out_path: str | Path, brand: str = "Content Factory", seed: int = 0) -> Path:
    out_path = Path(out_path)
    c1, c2 = PALETTES[seed % len(PALETTES)]

    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        color = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=color)

    # заголовок (2-3 строки)
    font_title = _font(72)
    lines = textwrap.wrap(title, 26) or [title]
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][:-3] + "..."
    y = 180
    for ln in lines:
        bbox = d.textbbox((0, 0), ln, font=font_title)
        d.text(((W - (bbox[2] - bbox[0])) // 2, y), ln, font=font_title, fill=(255, 255, 255))
        y += 100

    # ниша-бейдж
    font_badge = _font(40)
    bbox = d.textbbox((0, 0), niche, font=font_badge)
    bw = bbox[2] - bbox[0] + 48
    bx = (W - bw) // 2
    d.rounded_rectangle([bx, y + 40, bx + bw, y + 40 + 70], 35, fill=(0, 0, 0, 90))
    d.text((bx + 24, y + 55), niche, font=font_badge, fill=(255, 255, 255))

    # бренд внизу
    font_brand = _font(32)
    d.text((40, H - 60), brand, font=font_brand, fill=(255, 255, 255, 140))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
