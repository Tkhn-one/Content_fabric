"""VK: публикация клипа на стену сообщества (бесплатно, токен сообщества).

Flow: video.save → загрузка на upload_url → wall.post с attachment.
"""
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class PublishMeta:
    title: str
    description: str = ""
    tags: list[str] | None = None


class VKPublisher:
    API = "https://api.vk.com/method"

    def __init__(self, access_token: str, group_id: str, api_version: str = "5.199"):
        self.access_token = access_token
        self.group_id = group_id.lstrip("-")
        self.api_version = api_version

    async def publish(self, video: Path, meta: PublishMeta) -> dict:
        async with httpx.AsyncClient(timeout=300) as client:
            # 1) получить upload_url
            save_resp = await client.post(
                f"{self.API}/video.save",
                data={
                    "access_token": self.access_token,
                    "v": self.api_version,
                    "group_id": self.group_id,
                    "name": meta.title[:128],
                    "description": (meta.description + " " + " ".join(meta.tags or []))[:256],
                    "wallpost": 1,
                },
            )
            save_resp.raise_for_status()
            saved = save_resp.json()
            if "error" in saved:
                raise RuntimeError(f"VK video.save: {saved['error']}")
            upload_url = saved["response"]["upload_url"]
            video_id = saved["response"]["video_id"]
            owner_id = saved["response"]["owner_id"]

            # 2) загрузить файл
            with open(video, "rb") as f:
                up = await client.post(upload_url, files={"video_file": (video.name, f, "video/mp4")})
            up.raise_for_status()

            # 3) опубликовать на стену (wallpost=1 уже поставил, но для надёжности)
            wall = await client.post(
                f"{self.API}/wall.post",
                data={
                    "access_token": self.access_token,
                    "v": self.api_version,
                    "owner_id": -int(self.group_id),
                    "message": meta.title[:500],
                    "attachments": f"video{owner_id}_{video_id}",
                },
            )
            wall.raise_for_status()
            wall_json = wall.json()
            if "error" in wall_json:
                # запись на стену могла создаться автоматически (wallpost=1) — не критично
                pass

        return {
            "external_id": str(video_id),
            "url": f"https://vk.com/video{owner_id}_{video_id}",
            "raw": {"owner_id": owner_id},
        }
