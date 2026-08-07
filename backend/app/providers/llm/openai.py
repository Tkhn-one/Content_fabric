"""OpenAI (ChatGPT): идеи, сценарии, хештеги. Ключ заказчика в настройках."""
import httpx

from app.providers.base import LLMProvider


class OpenAILLM(LLMProvider):
    BASE = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def _chat(self, system: str, user: str, max_tokens: int = 600) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.BASE,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.8,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def generate_ideas(self, niche: str, count: int = 5) -> list[str]:
        text = await self._chat(
            "Ты — контент-стратег для вертикальных видео. Возвращай ТОЛЬКО список идей,"
            " по одной на строку, без нумерации и пояснений.",
            f"Придумай {count} цепляющих идей для видео по теме: {niche}. Формат: короткий заголовок.",
        )
        return [line.strip(" -•1234567890.") for line in text.splitlines() if line.strip()][:count]

    async def generate_script(self, prompt: str) -> str:
        return await self._chat(
            "Ты — сценарист вертикальных видео (Shorts). Пиши живо, короткими фразами,"
            " без заголовков, готовый текст для озвучки 30-50 секунд.",
            prompt,
            max_tokens=800,
        )

    async def generate_hashtags(self, title: str, niche: str) -> list[str]:
        text = await self._chat(
            "Ты — SMM-специалист. Верни список хештегов через пробел (5-10 шт),"
            " релевантных теме, без пояснений.",
            f"Заголовок: {title}. Тема: {niche}",
            max_tokens=200,
        )
        return [t.strip() for t in text.replace(",", " ").split() if t.startswith("#")][:10]
