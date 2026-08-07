"""Шаг 5: публикация. Этап 0 — заглушка: пишем журнал без реальной отправки.

Реальные адаптеры (YouTube/TikTok/VK/TG/Reels) подключаются на этапах 2–3.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Job, PublishLog, Topic

PLATFORM_LABELS = {"youtube": "YouTube Shorts", "tiktok": "TikTok", "telegram": "Telegram", "vk": "VK Clips", "reels": "Instagram Reels"}


async def run(db: Session, job: Job, topic: Topic) -> None:
    platforms = topic.platforms or ["youtube"]
    data = dict(job.payload or {})
    data["publish"] = []

    for platform in platforms:
        label = PLATFORM_LABELS.get(platform, platform)
        log = PublishLog(
            job_id=job.id,
            platform=platform,
            status="published",
            url=(data.get("video_path") or ""),
            stats={"note": "демо-режим: реальная публикация подключается на этапе 2"},
            published_at=datetime.now(timezone.utc),
        )
        db.add(log)
        data["publish"].append({"platform": platform, "label": label, "status": "published"})

    job.payload = data
    db.commit()
