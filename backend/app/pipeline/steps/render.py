"""Шаг 4: монтаж. Этап 0 — проверка окружения и создание заготовки ролика.

Реальный монтаж (сток-кадры, кинетические субтитры, музыка, ffmpeg) — этап 1.
"""
import logging
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, Topic

logger = logging.getLogger(__name__)


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


async def run(db: Session, job: Job, topic: Topic) -> None:
    job_dir = settings.media_dir / "jobs" / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    data = dict(job.payload or {})

    if _ffmpeg_available():
        try:
            video_path = job_dir / "video.mp4"
            # чёрно-белый вертикальный ролик 2 сек — заготовка для этапа 1
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-shortest", str(video_path),
                ],
                check=True, capture_output=True,
            )
            data["video_path"] = str(video_path)
            data["video_note"] = "заготовка (этап 0)"
        except subprocess.CalledProcessError as exc:
            logger.warning("ffmpeg-сборка не удалась: %s", exc.stderr.decode(errors="ignore")[:300])
            data["video_path"] = None
            data["video_note"] = "ffmpeg недоступен в этой среде"
    else:
        data["video_path"] = None
        data["video_note"] = "ffmpeg не установлен (этап 1: сборка с кадрами и субтитрами)"

    job.payload = data
    db.commit()
