from datetime import datetime

from pydantic import BaseModel


class JobCreate(BaseModel):
    """Запуск вручную: указать тему или сразу тему+нишу."""

    topic_id: int | None = None
    niche: str | None = None          # разовый запуск без сохранения темы
    name: str | None = None
    language: str = "ru"
    tone: str = "casual"
    template: str = "facts"
    platforms: list[str] = []
    auto_publish: bool = False


class JobOut(BaseModel):
    id: int
    topic_id: int | None = None
    status: str
    step: str
    error: str | None = None
    retry_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
