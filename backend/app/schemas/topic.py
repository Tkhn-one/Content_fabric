from datetime import datetime

from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    niche: str = Field(min_length=2, max_length=256)
    language: str = "ru"
    tone: str = "casual"
    template: str = "facts"
    schedule_cron: str = "0 9,18 * * *"
    videos_per_day: int = Field(default=2, ge=1, le=50)
    enabled: bool = True
    platforms: list[str] = []
    auto_publish: bool = False
    auto_hashtags: bool = True
    voice_id: str | None = None
    avatar_id: str | None = None


class TopicUpdate(BaseModel):
    name: str | None = None
    niche: str | None = None
    language: str | None = None
    tone: str | None = None
    template: str | None = None
    schedule_cron: str | None = None
    videos_per_day: int | None = Field(default=None, ge=1, le=50)
    enabled: bool | None = None
    platforms: list[str] | None = None
    auto_publish: bool | None = None
    auto_hashtags: bool | None = None
    voice_id: str | None = None
    avatar_id: str | None = None


class TopicOut(TopicCreate):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
