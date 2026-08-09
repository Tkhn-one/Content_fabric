"""Telegram: публикация видео в канал/чат через Bot API (бесплатно)."""
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class PublishMeta:
    title: str
    description: str = ""
    tags: list[str] | None = None


class TelegramPublisher:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def publish(self, video: Path, meta: PublishMeta) -> dict:
        caption = meta.title
        if meta.description:
            caption += "\n\n" + meta.description
        tags = " ".join(meta.tags or [])
        if tags:
            caption += "\n" + tags

        url = f"https://api.telegram.org/bot{self.bot_token}/sendVideo"
        with open(video, "rb") as f:
            files = {"video": (video.name, f, "video/mp4")}
            data = {"chat_id": self.chat_id, "caption": caption[:1024], "supports_streaming": True}
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, data=data, files=files)
                resp.raise_for_status()
                body = resp.json()
        message = body.get("result", {})
        chat = message.get("chat", {})
        message_id = message.get("message_id")
        return {
            "external_id": str(message_id),
            "url": f"https://t.me/{chat.get('username', 'c')}/{message_id}" if message_id else "",
            "raw": body,
        }
