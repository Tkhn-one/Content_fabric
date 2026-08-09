"""Поиск системного шрифта для Pillow-рендеров (работает на Windows/Linux/macOS)."""
import os

# В порядке приоритета: сначала системные шрифты Windows, потом Linux, macOS
CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\verdanab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
]


def find_font() -> str:
    """Возвращает путь к первому найденному шрифту (для ImageFont.truetype)."""
    for path in CANDIDATES:
        if os.path.exists(path):
            return path
    # если ничего не нашли — отдадим первый; ImageFont сам бросит понятную ошибку
    return CANDIDATES[0]
