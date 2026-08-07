"""Шаг «Публикация»: реальные адаптеры платформ (если ключи настроены),
иначе — строка «skipped» в журнале с пояснением. После — Sheets + Drive."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Job, PublishLog, Topic
from app.providers.publish.instagram import InstagramPublisher, PublishMeta as IG_Meta
from app.providers.publish.telegram import PublishMeta as TG_Meta
from app.providers.publish.telegram import TelegramPublisher
from app.providers.publish.tiktok import PublishMeta as TT_Meta
from app.providers.publish.tiktok import TikTokOAuth, TikTokPublisher
from app.providers.publish.vk import PublishMeta as VK_Meta
from app.providers.publish.vk import VKPublisher
from app.providers.publish.youtube import PublishMeta as YT_Meta
from app.providers.publish.youtube import YouTubePublisher
from app.providers.registry import get_provider_settings_named

logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "youtube": "YouTube Shorts", "tiktok": "TikTok", "telegram": "Telegram",
    "vk": "VK Clips", "reels": "Instagram Reels",
}


def _meta(topic: Topic, job: Job, platform: str, hashtags: list[str]):
    title = (job.payload or {}).get("title") or f"{topic.name} #shorts"
    desc = f"Автоматически сгенерировано. Тема: {topic.name}"
    tags = hashtags or [topic.niche, "#shorts"]
    if platform == "youtube":
        return YT_Meta(title=title, description=desc, tags=tags, privacy_status="public")
    if platform == "tiktok":
        return TT_Meta(title=title, description=desc, tags=tags)
    if platform == "vk":
        return VK_Meta(title=title, description=desc, tags=tags)
    if platform == "reels":
        return IG_Meta(title=title, description=desc, tags=tags)
    return TG_Meta(title=title, description=desc, tags=tags)


async def _publish_real(db: Session, platform: str, job: Job, topic: Topic, video: Path, hashtags: list[str]) -> dict:
    cfg = get_provider_settings_named(db, "publish", platform)
    if cfg is None:
        return {"error": "ключ платформы не настроен (Подключения → publish)"}
    payload = cfg["payload"]

    if platform == "telegram":
        if not payload.get("bot_token") or not payload.get("chat_id"):
            return {"error": "нет bot_token/chat_id"}
        pub = TelegramPublisher(payload["bot_token"], payload["chat_id"])
        res = await pub.publish(video, _meta(topic, job, platform, hashtags))
        return {"external_id": res["external_id"], "url": res["url"]}

    if platform == "youtube":
        if not payload.get("client_id") or not payload.get("client_secret") or not payload.get("refresh_token"):
            return {"error": "нет client_id/client_secret/refresh_token"}
        pub = YouTubePublisher(
            payload["client_id"], payload["client_secret"], payload["refresh_token"],
            payload.get("channel_id", ""),
        )
        res = await pub.publish(video, _meta(topic, job, platform, hashtags))
        return {"external_id": res["external_id"], "url": res["url"]}

    if platform == "tiktok":
        if not payload.get("access_token"):
            return {"error": "нет access_token TikTok (нужна модерация приложения)"}
        token = payload["access_token"]
        refresh = payload.get("refresh_token", "")
        # токены живут 24 ч — пробуем обновить, если есть refresh_token
        if refresh and payload.get("client_key") and payload.get("client_secret"):
            try:
                r = await TikTokOAuth.refresh(payload["client_key"], payload["client_secret"], refresh)
                if r.get("access_token") and r["access_token"] != token:
                    token = r["access_token"]
                    from app.core.security import encrypt_secrets

                    payload["access_token"] = token
                    if r.get("refresh_token"):
                        payload["refresh_token"] = r["refresh_token"]
                    # обновить зашифрованную запись
                    from app.models import ProviderSettings

                    row_db = (
                        db.query(ProviderSettings)
                        .filter(
                            ProviderSettings.provider_type == "publish",
                            ProviderSettings.provider_name == "tiktok",
                        )
                        .first()
                    )
                    if row_db:
                        row_db.encrypted_payload = encrypt_secrets(payload)
                        db.commit()
            except Exception as exc:
                logger.warning("TikTok refresh: %s", exc)
        pub = TikTokPublisher(
            payload.get("client_key", ""), payload.get("client_secret", ""), token, refresh,
        )
        res = await pub.publish(video, _meta(topic, job, platform, hashtags))
        return {"external_id": res["external_id"], "url": res["url"]}

    if platform == "vk":
        if not payload.get("access_token") or not payload.get("group_id"):
            return {"error": "нет access_token/group_id VK"}
        pub = VKPublisher(payload["access_token"], payload["group_id"])
        res = await pub.publish(video, _meta(topic, job, platform, hashtags))
        return {"external_id": res["external_id"], "url": res["url"]}

    if platform == "reels":
        if not payload.get("access_token") or not payload.get("user_id"):
            return {"error": "нет access_token/user_id Instagram"}
        pub = InstagramPublisher(payload["access_token"], payload["user_id"], payload.get("server_url", ""))
        res = await pub.publish(video, _meta(topic, job, platform, hashtags))
        return {"external_id": res["external_id"], "url": res["url"]}

    return {"error": f"платформа {platform} не реализована"}


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
    hashtags = (job.payload or {}).get("hashtags", [])
    data = dict(job.payload or {})
    data["publish"] = []

    for platform in platforms:
        label = PLATFORM_LABELS.get(platform, platform)
        real: dict = {}
        if video and video.exists():
            try:
                real = await _publish_real(db, platform, job, topic, video, hashtags)
            except Exception as exc:
                logger.error("Публикация в %s: %s", platform, exc)
                real = {"error": str(exc)}
        elif not video:
            real = {"error": "нет готового видео (шаг рендера не выполнен)"}

        if real.get("error"):
            log = PublishLog(
                job_id=job.id,
                platform=platform,
                status="skipped",
                stats={"note": real["error"]},
            )
            db.add(log)
            data["publish"].append({"platform": platform, "label": label, "status": "skipped", "error": real["error"]})
        elif real.get("external_id") or real.get("url"):
            log = PublishLog(
                job_id=job.id,
                platform=platform,
                status="published",
                external_id=real.get("external_id"),
                url=real.get("url"),
                stats={"note": "опубликовано"},
                published_at=datetime.now(timezone.utc),
            )
            db.add(log)
            data["publish"].append({"platform": platform, "label": label, "status": "published"})
        else:
            log = PublishLog(
                job_id=job.id,
                platform=platform,
                status="skipped",
                stats={"note": "нет ключа платформы"},
            )
            db.add(log)
            data["publish"].append({"platform": platform, "label": label, "status": "skipped"})

    job.payload = data
    db.commit()

    if video and video.exists():
        await _save_to_storage(db, job, topic, video)
