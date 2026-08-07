"""Gemini (Google): идеи, сценарии, хештеги. Есть бесплатный тариф."""
import httpx

from app.providers.base import LLMProvider


class GeminiLLM(LLMProvider):
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    async def _generate(self, prompt: str, max_tokens: int = 800) -> str:
        url = f"{self.BASE}/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.8},
                },
            )
            resp.raise_for_status()
            parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()

    async def generate_ideas(self, niche: str, count: int = 5) -> list[str]:
        text = await self._generate(
            f"Придумай {count} цепляющих идей для вертикальных видео по теме: {niche}.\n"
            "Верни ТОЛЬКО список, по одной на строку, без нумерации.",
        )
        return [line.strip(" -•1234567890.") for line in text.splitlines() if line.strip()][:count]

    async def generate_script(self, prompt: str) -> str:
        return await self._generate(
            "Ты — сценарист вертикальных видео (Shorts). Пиши живо, короткими фразами,"
            " без заголовков, готовый текст для озвучки 30-50 секунд.\n\n" + prompt
        )

    async def generate_hashtags(self, title: str, niche: str) -> list[str]:
        text = await self._generate(
            f"Заголовок: {title}. Тема: {niche}.\n"
            "Верни список релевантных хештегов через пробел (5-10 шт), без пояснений.",
            max_tokens=200,
        )
        return [t.strip() for t in text.replace(",", " ").split() if t.startswith("#")][:10]
