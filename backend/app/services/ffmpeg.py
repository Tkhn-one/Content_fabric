"""Хелперы для работы с ffmpeg: поиск бинарника, длительность медиа."""
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_FFMPEG: str | None = None


def ffmpeg_path() -> str:
    """Возвращает путь к ffmpeg: системный или статический из imageio-ffmpeg."""
    global _FFMPEG
    if _FFMPEG:
        return _FFMPEG
    system = shutil.which("ffmpeg")
    if system:
        _FFMPEG = system
        return system
    try:
        import imageio_ffmpeg

        _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        return _FFMPEG
    except Exception as exc:
        raise RuntimeError("ffmpeg не найден (нужен системный ffmpeg или pip install imageio-ffmpeg)") from exc


def ffmpeg_available() -> bool:
    try:
        ffmpeg_path()
        return True
    except Exception:
        return False


def ffmpeg_has_filter(name: str) -> bool:
    """Есть ли у текущего ffmpeg нужный фильтр (например, 'ass')."""
    try:
        exe = ffmpeg_path()
        res = subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30)
        return name in (res.stdout or "")
    except Exception:
        return False


def probe_duration(path: str | Path) -> float:
    """Длительность аудио/видео в секундах (ffprobe или ffmpeg -i)."""
    path = str(path)
    exe = ffmpeg_path()
    cmd = [exe, "-i", path, "-f", "null", "-"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        stderr = res.stderr or ""
        for line in stderr.splitlines():
            if "Duration:" in line:
                part = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = part.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 0.0
