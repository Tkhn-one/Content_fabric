"""LLM-провайдеры. На этапе 0 работает встроенный mock-генератор без ключей."""
from app.providers.base import LLMProvider


class MockLLM(LLMProvider):
    """Встроенный генератор: шаблонные идеи и сценарии без внешних API (демо-режим)."""

    async def generate_ideas(self, niche: str, count: int = 5) -> list[str]:
        hooks = [
            "Почему это меняет всё",
            "Что вы не знали",
            "Секрет, о котором молчат",
            "Как это работает на самом деле",
            "Факт, который звучит как ложь",
        ]
        angles = [
            f"5 фактов о {niche}, которые удивят",
            f"Самая большая ошибка в {niche}",
            f"{niche}: как это устроено за 30 секунд",
            f"Мифы о {niche}, в которые мы верим",
            f"Что будет через 10 лет: {niche}",
        ]
        return [f"{h}: {a}" for h, a in zip(hooks[: count // 2 + 1], angles[:count])][:count]

    async def generate_script(self, prompt: str) -> str:
        return prompt

    async def generate_hashtags(self, title: str, niche: str) -> list[str]:
        tags = {"#shorts", "#fyp"}
        words = [w.strip("# ").lower() for w in (title + " " + niche).split()]
        tags |= {f"#{w}" for w in words if len(w) > 3}
        return list(tags)[:10]
