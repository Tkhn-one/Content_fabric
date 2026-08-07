"""Кинетические субтитры: генерация ASS (karaoke) для вертикального видео.

Формат: один диалог на фразу, слова через \\k-тайминги (центisec).
libass подсвечивает уже произнесённую часть SecondaryColour (жёлтый) —
это и есть TikTok-стиль «кинетических» субтитров.
"""
from __future__ import annotations

from dataclasses import dataclass

WIDTH, HEIGHT = 1080, 1920

# &HAABBGGRR
STYLES = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},72,&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,50,50,260,1
Style: Watermark,{font},34,&H44FFFFFF,&H00000000,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,8,50,50,40,1
"""

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
"""


@dataclass
class Word:
    text: str
    start: float  # сек
    end: float    # сек


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def _fmt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def build_ass(
    phrases: list[tuple[str, list[Word]]],
    duration: float,
    watermark: str | None = None,
    font: str = "DejaVu Sans",
) -> str:
    """phrases: [(текст фразы, слова с таймингами внутри фразы)]"""
    lines = [HEADER.format(w=WIDTH, h=HEIGHT)]
    lines.append(STYLES.format(font=font))
    lines.append("")
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for phrase, words in phrases:
        if not words:
            continue
        start = words[0].start
        end = words[-1].end
        karaoke = "".join(
            f"{{\\k{max(1, int(round((w.end - w.start) * 100)))}}}{_ass_escape(w.text)}" for w in words
        )
        lines.append(
            f"Dialogue: 0,{_fmt_time(start)},{_fmt_time(end)},Cap,,0,0,0,,{karaoke}"
        )

    if watermark:
        lines.append(
            f"Dialogue: 1,{_fmt_time(0)},{_fmt_time(duration)},Watermark,,0,0,0,,{_ass_escape(watermark)}"
        )
    return "\n".join(lines) + "\n"
