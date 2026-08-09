"""Аналитика канала: статистика по опубликованным видео через YouTube Data API.

Использует те же ключи, что и публикация (client_id / client_secret / refresh_token).
"""
import logging

import httpx
from sqlalchemy.orm import Session

from app.models import PublishLog
from app.providers.registry import get_provider_settings_named

logger = logging.getLogger(__name__)


class YouTubeAnalytics:
    API = "https://www.googleapis.com/youtube/v3"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def fetch_video_stats(self, video_ids: list[str]) -> dict[str, dict]:
        """Возвращает {video_id: {views, likes, comments}} для id (до 50 за вызов)."""
        result: dict[str, dict] = {}
        if not video_ids:
            return result
        async with httpx.AsyncClient(timeout=60) as client:
            token = await self._access_token(client)
            headers = {"Authorization": f"Bearer {token}"}
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i : i + 50]
                resp = await client.get(
                    f"{self.API}/videos",
                    headers=headers,
                    params={"part": "statistics", "id": ",".join(chunk)},
                )
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    st = item.get("statistics", {})
                    result[item["id"]] = {
                        "views": int(st.get("viewCount", 0)),
                        "likes": int(st.get("likeCount", 0)),
                        "comments": int(st.get("commentCount", 0)),
                    }
        return result

    async def fetch_channel_stats(self) -> dict:
        """Статистика канала: подписчики, всего просмотров, видео."""
        async with httpx.AsyncClient(timeout=60) as client:
            token = await self._access_token(client)
            resp = await client.get(
                f"{self.API}/channels",
                headers={"Authorization": f"Bearer {token}"},
                params={"part": "statistics", "mine": "true"},
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                return {}
            st = items[0].get("statistics", {})
            return {
                "subscribers": int(st.get("subscriberCount", 0)),
                "total_views": int(st.get("viewCount", 0)),
                "total_videos": int(st.get("videoCount", 0)),
            }


async def sync_youtube_stats(db: Session) -> dict:
    """Тянет статистику по опубликованным YouTube-видео из БД и сохраняет в PublishLog.stats."""
    cfg = get_provider_settings_named(db, "publish", "youtube")
    if not cfg or not cfg["payload"].get("client_id"):
        return {"ok": False, "error": "YouTube не подключён (Подключения → publish → youtube)"}
    p = cfg["payload"]

    logs = (
        db.query(PublishLog)
        .filter(
            PublishLog.platform == "youtube",
            PublishLog.external_id.isnot(None),
            PublishLog.external_id != "",
        )
        .all()
    )
    ids = list({l.external_id for l in logs if l.external_id})
    if not ids:
        return {"ok": True, "synced": 0, "note": "нет опубликованных YouTube-видео"}

    analytics = YouTubeAnalytics(p["client_id"], p["client_secret"], p["refresh_token"])
    stats = await analytics.fetch_video_stats(ids)

    updated = 0
    for log in logs:
        if log.external_id in stats:
            merged = dict(log.stats or {})
            merged.update(stats[log.external_id])
            merged["synced_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            log.stats = merged
            updated += 1
    db.commit()
    return {"ok": True, "synced": updated}
