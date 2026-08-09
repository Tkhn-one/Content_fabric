"""Instagram Reels: публикация через Graph API (бесплатно, Business-аккаунт).

ВАЖНО: API принимает ТОЛЬКО публичный URL видео. Нужен публичный домен системы
(поле server_url в настройках) — видео подтягивается по /media/... .
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class PublishMeta:
    title: str
    description: str = ""
    tags: list[str] | None = None


GRAPH = "https://graph.facebook.com/v21.0"


class InstagramPublisher:
    def __init__(self, access_token: str, user_id: str, server_url: str = ""):
        self.access_token = access_token
        self.user_id = user_id
        self.server_url = server_url.rstrip("/")

    async def publish(self, video: Path, meta: PublishMeta) -> dict:
        if not self.server_url:
            raise RuntimeError("Instagram требует публичный server_url (адрес вашей системы)")

        # видео должно быть доступно по публичному URL
        rel = str(video).replace("\\", "/")
        # ищем подстроку "media/..." в пути
        idx = rel.find("media/")
        if idx == -1:
            raise RuntimeError("Не удалось построить публичный URL видео")
        video_url = f"{self.server_url}/{rel[idx:]}"
        caption = (meta.title + "\n\n" + " ".join(meta.tags or []))[:2200]

        async with httpx.AsyncClient(timeout=120) as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}

            # 1) создать контейнер
            resp = await client.post(
                f"{GRAPH}/{self.user_id}/media",
                headers=headers,
                data={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "share_to_feed": "true",
                },
            )
            resp.raise_for_status()
            container_id = resp.json().get("id")

            # 2) дождаться готовности
            for _ in range(60):
                status_resp = await client.get(
                    f"{GRAPH}/{container_id}",
                    headers=headers,
                    params={"fields": "status_code"},
                )
                status_resp.raise_for_status()
                if status_resp.json().get("status_code") == "FINISHED":
                    break
                await asyncio.sleep(5)
            else:
                raise RuntimeError("Instagram: контейнер не готов за 5 мин")

            # 3) опубликовать
            pub = await client.post(
                f"{GRAPH}/{self.user_id}/media_publish",
                headers=headers,
                data={"creation_id": container_id},
            )
            pub.raise_for_status()
            media_id = pub.json().get("id", "")

        return {
            "external_id": str(media_id),
            "url": f"https://www.instagram.com/reel/{media_id}",
            "raw": {"container": container_id},
        }
