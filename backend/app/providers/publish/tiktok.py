"""TikTok: публикация через Content Posting API (бесплатно, нужна модерация приложения).

Flow: refresh токена (24ч) → init (chunked upload) → загрузка чанков → опрос статуса.
Ключи заказчика: client_key, client_secret, access_token, refresh_token.
"""
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class PublishMeta:
    title: str
    description: str = ""
    tags: list[str] | None = None


CHUNK_SIZE = 4 * 1024 * 1024  # 4 МБ


class TikTokOAuth:
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

    @staticmethod
    async def refresh(client_key: str, client_secret: str, refresh_token: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                TikTokOAuth.TOKEN_URL,
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            resp.raise_for_status()
            return resp.json()


class TikTokPublisher:
    INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

    def __init__(self, client_key: str, client_secret: str, access_token: str, refresh_token: str = ""):
        self.client_key = client_key
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token

    async def publish(self, video: Path, meta: PublishMeta) -> dict:
        size = video.stat().st_size
        chunk_size = min(CHUNK_SIZE, size)
        chunks = max(1, (size + chunk_size - 1) // chunk_size)

        async with httpx.AsyncClient(timeout=600) as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            resp = await client.post(
                self.INIT_URL,
                headers=headers,
                json={
                    "post_info": {
                        "title": (meta.title + " " + " ".join(meta.tags or [])).strip()[:2200],
                        "privacy_level": "PUBLIC",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": size,
                        "chunk_size": chunk_size,
                        "total_chunk_count": chunks,
                    },
                },
            )
            resp.raise_for_status()
            body = resp.json().get("data", {})
            publish_id = body.get("publish_id")
            upload_url = body.get("upload_url")
            if not publish_id or not upload_url:
                raise RuntimeError(f"TikTok init: {body}")

            # загрузка чанков
            with open(video, "rb") as f:
                for i in range(chunks):
                    chunk = f.read(chunk_size)
                    start = i * chunk_size
                    end = start + len(chunk) - 1
                    up = await client.put(
                        upload_url,
                        headers={
                            "Content-Type": "video/mp4",
                            "Content-Range": f"bytes {start}-{end}/{size}",
                        },
                        content=chunk,
                    )
                    up.raise_for_status()

            # опрос статуса
            for _ in range(120):
                status_resp = await client.post(
                    self.STATUS_URL,
                    headers=headers,
                    json={"publish_id": publish_id},
                )
                status_resp.raise_for_status()
                st = status_resp.json().get("data", {}).get("status")
                if st == "PUBLISH_COMPLETE":
                    return {"external_id": publish_id, "url": "", "raw": {"status": st}}
                if st in ("FAILED", "PUBLISH_FAILED"):
                    raise RuntimeError(f"TikTok publish failed: {status_resp.json()}")
                import asyncio

                await asyncio.sleep(3)
            raise RuntimeError("TikTok: таймаут публикации")
