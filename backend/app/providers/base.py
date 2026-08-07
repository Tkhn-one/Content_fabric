"""Абстракции провайдеров. Каждый внешний сервис — адаптер с единым контрактом."""
from abc import ABC, abstractmethod
from pathlib import Path


class LLMProvider(ABC):
    """Генерация идей, сценариев, хештегов."""

    @abstractmethod
    async def generate_ideas(self, niche: str, count: int = 5) -> list[str]: ...

    @abstractmethod
    async def generate_script(self, prompt: str) -> str: ...

    @abstractmethod
    async def generate_hashtags(self, title: str, niche: str) -> list[str]: ...


class TTSProvider(ABC):
    """Озвучка текста в аудиофайл."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str | None, lang: str, out_path: Path) -> Path: ...


class StockProvider(ABC):
    """Стоковые кадры по ключевым словам."""

    @abstractmethod
    async def search(self, query: str, n: int = 5, orientation: str = "vertical") -> list[str]: ...
