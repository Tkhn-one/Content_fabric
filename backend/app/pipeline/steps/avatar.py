"""Шаг «Аватар» (Pro+): если задан avatar_id и настроен провайдер —
генерирует видео с говорящим аватаром. Иначе шаг пропускается (фейслесс-режим)."""
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, Topic
from app.providers.avatar.heygen import HeyGenAvatar
from app.providers.registry import get_provider_settings_named

logger = logging.getLogger(__name__)


async def run(db: Session, job: Job, topic: Topic) -> None:
    data = dict(job.payload or {})
    avatar_id = topic.avatar_id
    cfg = get_provider_settings_named(db, "avatar", "heygen")
    if not avatar_id or not (cfg and cfg["payload"].get("api_key")):
        data["avatar_path"] = None
        data["avatar_note"] = "аватар не настроен (фейслесс-режим)"
        job.payload = data
        db.commit()
        return

    script = data.get("script", "")
    if not script:
        raise RuntimeError("Нет сценария для аватара")

    job_dir = settings.media_dir / "jobs" / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    out = job_dir / "avatar.mp4"
    try:
        provider = HeyGenAvatar(cfg["payload"]["api_key"])
        voice_id = cfg["payload"].get("voice_id") or topic.voice_id
        await provider.render(script, avatar_id, voice_id, out)
        data["avatar_path"] = str(out)
        data["avatar_note"] = "heygen"
        data["voice_path"] = None          # аватар озвучивает сам
        data["voice_note"] = "аватар (heygen) озвучивает сам"
    except Exception as exc:
        logger.error("Аватар не сгенерирован: %s", exc)
        data["avatar_path"] = None
        data["avatar_note"] = f"ошибка аватара: {exc}"
    job.payload = data
    db.commit()
