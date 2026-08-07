"""Шаг «Публикация»: реальные адаптеры платформ, если настроены ключи,
иначе — демо-заглушка в журнал. После публикации — журнал в Sheets и архив в Drive."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Job, PublishLog, Topic
from app.providers.publish.telegram import PublishMeta as TGMeta
from app.providers.publish.telegram import TelegramPublisher
from app.providers.publish.youtube import PublishMeta as YTMeta
from app.providers.publish.youtube import YouTubePublisher
from app.providers.registry import get_provider_settings_named

logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "youtube": "YouTube Shorts", "tiktok": "TikTok", "telegram": "Telegram",
    "vk": "VK Clips", "reels": "Instagram Reels",
}


def _meta(topic: Topic, job: Job, platform: str):
    title = (job.payload or {}).get("title") or f"{topic.name} #shorts"
    desc = f"Автоматически сгенерировано. Тема: {topic.name}"
    if platform == "youtube":
        return YTMeta(title=title, description=desc, tags=[topic.niche, "#shorts", "#short"], privacy_status="public")
    return TGMeta(title=title, description=desc, tags=[topic.niche, "#shorts"])


async def _publish_real(db: Session, platform: str, job: Job, topic: Topic, video: Path) -> dict:
    cfg = get_provider_settings_named(db, "publish", platform)
    if cfg is None:
        return {}
    payload = cfg["payload"]

    if platform == "telegram":
        if not payload.get("bot_token") or not payload.get("chat_id"):
            return {}
        pub = TelegramPublisher(payload["bot_token"], payload["chat_id"])
        res = await pub.publish(video, _meta(topic, job, platform))
        return {"external_id": res["external_id"], "url": res["url"]}

    if platform == "youtube":
        if not payload.get("client_id") or not payload.get("client_secret") or not payload.get("refresh_token"):
            return {}
        pub = YouTubePublisher(
            payload["client_id"], payload["client_secret"], payload["refresh_token"],
            payload.get("channel_id", ""),
        )
        res = await pub.publish(video, _meta(topic, job, platform))
        return {"external_id": res["external_id"], "url": res["url"]}

    # tiktok / vk / reels — подключаются на этапах 3–5
    return {}


async def _save_to_storage(db: Session, job: Job, topic: Topic, video: Path | None) -> None:
    """Google Sheets (строка журнала) + Google Drive (копия ролика). Тихие ошибки."""
    try:
        from app.services.google_rest import append_sheet_row, upload_drive

        sheet_cfg = get_provider_settings_named(db, "storage", "google_sheets")
        if sheet_cfg and sheet_cfg["payload"].get("service_account_json") and sheet_cfg["payload"].get("spreadsheet_id"):
            row = [
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                topic.name, topic.niche,
                (job.payload or {}).get("title", ""),
                ",".join(topic.platforms or []),
                job.status,
                str(video) if video else "",
            ]
            await append_sheet_row(
                sheet_cfg["payload"]["service_account_json"],
                sheet_cfg["payload"]["spreadsheet_id"],
                row,
            )

        drive_cfg = get_provider_settings_named(db, "storage", "google_drive")
        if drive_cfg and drive_cfg["payload"].get("service_account_json") and video and video.exists():
            name = f"{topic.name}_{job.id}.mp4"
            await upload_drive(
                drive_cfg["payload"]["service_account_json"],
                video,
                drive_cfg["payload"].get("folder_id", ""),
                name,
            )
    except Exception as exc:
        logger.warning("Sheets/Drive: %s", exc)


async def run(db: Session, job: Job, topic: Topic) -> None:
    platforms = topic.platforms or ["youtube"]
    video_path = (job.payload or {}).get("video_path")
    video = Path(video_path) if video_path else None
    data = dict(job.payload or {})
    data["publish"] = []

    for platform in platforms:
        label = PLATFORM_LABELS.get(platform, platform)
        real = {}
        if video and video.exists():
            try:
                real = await _publish_real(db, platform, job, topic, video)
            except Exception as exc:
                logger.error("Публикация в %s: %s", platform, exc)
                real = {"error": str(exc)}

        if real.get("external_id") or real.get("url") or real.get("error"):
            log = PublishLog(
                job_id=job.id,
                platform=platform,
                status="published" if not real.get("error") else "failed",
                external_id=real.get("external_id"),
                url=real.get("url"),
                stats={"note": real.get("error", "опубликовано")},
                published_at=datetime.now(timezone.utc),
            )
            db.add(log)
            data["publish"].append({"platform": platform, "label": label, "status": log.status})
        else:
            # ключ для платформы не настроен — демо-строка в журнале
            log = PublishLog(
                job_id=job.id,
                platform=platform,
                status="published",
                url=str(video) if video else "",
                stats={"note": "демо-режим: подключите ключ платформы в Настройках"},
                published_at=datetime.now(timezone.utc),
            )
            db.add(log)
            data["publish"].append({"platform": platform, "label": label, "status": "published", "demo": True})

    job.payload = data
    db.commit()

    if video and video.exists():
        await _save_to_storage(db, job, topic, video)
