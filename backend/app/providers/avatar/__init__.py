"""AI-аватары (Pro+): HeyGen, D-ID. Возвращают готовое видео с говорящим аватаром."""
from abc import ABC, abstractmethod
from pathlib import Path


class AvatarProvider(ABC):
    @abstractmethod
    async def render(self, script: str, avatar_id: str, voice_id: str | None, out_path: Path) -> Path:
        """Генерирует видео с аватаром, читающим сценарий."""
