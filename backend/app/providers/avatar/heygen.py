"""HeyGen: AI-аватар, читающий сценарий (Pro+). Ключ заказчика в настройках.

Flow: POST /v2/video/generate → poll /v1/video_status.get → скачать видео.
"""
import asyncio
from pathlib import Path

import httpx

from app.providers.avatar import AvatarProvider


class HeyGenAvatar(AvatarProvider):
    BASE = "https://api.heygen.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def render(self, script: str, avatar_id: str, voice_id: str | None, out_path: Path) -> Path:
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE}/v2/video/generate",
                headers=headers,
                json={
                    "caption": False,
                    "title": "Content Factory video",
                    "video_inputs": [
                        {
                            "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
                            "voice": {
                                "type": "text",
                                "input_text": script[:1900],
                                **({"voice_id": voice_id} if voice_id else {}),
                            },
                            "dimension": {"width": 1080, "height": 1920},
                        }
                    ],
                },
            )
            resp.raise_for_status()
            video_id = resp.json()["data"]["video_id"]

            # поллинг статуса (до ~10 минут)
            for _ in range(120):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"{self.BASE}/v1/video_status.get",
                    params={"video_id": video_id},
                    headers={"X-Api-Key": self.api_key},
                )
                status_resp.raise_for_status()
                status = status_resp.json().get("data", {})
                if status.get("status") == "completed":
                    video_url = status.get("video_url")
                    if not video_url:
                        raise RuntimeError("HeyGen: completed, но нет video_url")
                    video_resp = await client.get(video_url)
                    video_resp.raise_for_status()
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(video_resp.content)
                    return out_path
                if status.get("status") == "failed":
                    raise RuntimeError(f"HeyGen: генерация не удалась — {status.get('error')}")
            raise RuntimeError("HeyGen: таймаут генерации (10 мин)")
