"""YouTube: публикация Shorts через Data API v3 (resumable upload, OAuth refresh-token).

Ключи заказчика: client_id, client_secret, refresh_token (см. tools/oauth/youtube_oauth.py).
Бесплатно: квота 10 000 ед./день; загрузка ~100 ед. → десятки роликов в день.
"""
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class PublishMeta:
    title: str
    description: str = ""
    tags: list[str] | None = None
    category_id: str = "22"            # Люди и блоги
    privacy_status: str = "public"     # public / unlisted / private


class YouTubePublisher:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, channel_id: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.channel_id = channel_id

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

    async def publish(self, video: Path, meta: PublishMeta) -> dict:
        tags = " ".join(meta.tags or [])
        body_meta = {
            "snippet": {
                "title": meta.title[:100],
                "description": (meta.description + "\n" + tags).strip()[:5000],
                "tags": (meta.tags or [])[:500],
                "categoryId": meta.category_id,
            },
            "status": {"privacyStatus": meta.privacy_status, "selfDeclaredMadeForKids": False},
        }
        async with httpx.AsyncClient(timeout=300) as client:
            token = await self._access_token(client)
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}

            # 1) инициализация resumable-загрузки
            resp = await client.post(
                self.UPLOAD_URL,
                params={"part": "snippet,status", "uploadType": "resumable"},
                headers=headers,
                json=body_meta,
            )
            resp.raise_for_status()
            upload_url = resp.headers.get("Location")
            if not upload_url:
                raise RuntimeError("YouTube: нет Location для загрузки")

            # 2) выгрузка бинарника
            with open(video, "rb") as f:
                up = await client.put(
                    upload_url,
                    headers={"Content-Type": "video/*"},
                    content=f.read(),
                )
            up.raise_for_status()
            video_id = up.json().get("id", "")

            url = f"https://www.youtube.com/shorts/{video_id}" if video_id else ""

        return {"external_id": video_id, "url": url, "raw": {"status": "published"}}
