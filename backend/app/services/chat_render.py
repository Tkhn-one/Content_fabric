"""Рендер «фейк-чат» (Fake Chat): скриншот мессенджера с диалогом через Pillow.

Виральный формат Shorts: на экране переписка, голос за кадром читает реплики.
Каждое «сообщение» — отдельный кадр (сообщения накапливаются), склейка в видео
делается в шаге рендера. Работает полностью локально, без сети.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (11, 20, 26)          # тёмный фон (как Telegram night)
HEADER = (32, 44, 51)
BUBBLE_MINE = (37, 110, 235)     # синий (свои)
BUBBLE_THEM = (32, 44, 51)       # серый (собеседник)
TEXT = (240, 240, 240)
MUTED = (140, 150, 160)
ACCENT = (110, 200, 255)

MAX_VISIBLE = 8          # сколько сообщений помещается на экране
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def _fit_text(text: str, max_chars: int = 42, max_lines: int = 6) -> str:
    lines = textwrap.wrap(text, max_chars) or [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:-3] + "..."
    return "\n".join(lines)


def _draw_avatar(draw: ImageDraw.ImageDraw, x: int, y: int, r: int, seed: int) -> None:
    """Кружок-аватар с цветом по seed."""
    colors = [(76, 175, 80), (255, 152, 0), (233, 30, 99), (63, 81, 181), (0, 188, 212)]
    draw.ellipse([x - r, y - r, x + r, y + r], fill=colors[seed % len(colors)])
    draw.ellipse([x - r, y - r, x + r, y + r], outline=(11, 20, 26), width=3)


def render_chat_screenshot(
    messages: list[dict],
    out_path: str | Path,
    peer_name: str = "Собеседник",
    brand: str = "Content Factory",
) -> Path:
    """messages: [{speaker: 0|1, text: str}] — в порядке появления."""
    out_path = Path(out_path)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # --- шапка ---
    d.rectangle([0, 0, W, 150], fill=HEADER)
    _draw_avatar(d, 100, 75, 42, 7)
    d.text((165, 52), peer_name, font=_font(42), fill=TEXT)
    d.text((165, 105), "online", font=_font(28), fill=MUTED)

    # --- сообщения (последние MAX_VISIBLE) ---
    visible = messages[-MAX_VISIBLE:] if len(messages) > MAX_VISIBLE else messages
    skipped = len(messages) - len(visible)

    y = 200
    font_b = _font(40)
    font_s = _font(28)
    font_name = _font(30)

    if skipped > 0:
        d.text((60, y), "…", font=_font(56), fill=MUTED)
        y += 70

    for i, msg in enumerate(visible):
        text = _fit_text(msg["text"])
        lines = text.split("\n")
        tw = max(d.textbbox((0, 0), ln, font=font_b)[2] for ln in lines)
        line_h = 56
        bub_h = len(lines) * line_h + 36
        bw = min(860, tw + 64)

        mine = msg.get("speaker", 0) == 1
        if mine:
            x0 = W - 24 - bw
            d.rounded_rectangle([x0, y, W - 24, y + bub_h], 26, fill=BUBBLE_MINE)
        else:
            x0 = 150
            _draw_avatar(d, 78, y + bub_h // 2, 34, i % 4 + 1)
            d.rounded_rectangle([x0, y, x0 + bw, y + bub_h], 26, fill=BUBBLE_THEM)

        tx = x0 + 28
        ty = y + 18
        for ln in lines:
            d.text((tx, ty), ln, font=font_b, fill=TEXT)
            ty += line_h

        # время сообщения
        hh, mm = 10 + i // 6, (i * 7) % 60
        d.text((x0 + bw - 90, y + bub_h - 40), f"{hh:02d}:{mm:02d}", font=font_s, fill=MUTED)

        # имя спикера над пузырём (для чужих)
        if not mine:
            d.text((x0, y - 36), "Собеседник", font=font_name, fill=ACCENT)
        y += bub_h + 52

        if y > H - 260:
            break

    # --- поле ввода внизу ---
    d.rounded_rectangle([24, H - 170, W - 24, H - 60], 40, fill=HEADER)
    d.text((70, H - 138), "Сообщение…", font=font_b, fill=MUTED)

    # --- водяной знак (бренд) ---
    d.text((60, H - 44), brand, font=_font(26), fill=(255, 255, 255, 60))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
