from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.user import utcnow


class Topic(Base):
    """Тема/ниша: что генерируем, по какому расписанию, куда публикуем."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(128))                     # «Факты о космосе»
    niche: Mapped[str] = mapped_column(String(256))                    # ключевые слова темы
    language: Mapped[str] = mapped_column(String(8), default="ru")     # ru / en / ...
    tone: Mapped[str] = mapped_column(String(32), default="casual")    # casual / dramatic / expert
    template: Mapped[str] = mapped_column(String(32), default="facts") # шаблон сценария

    # Расписание (cron-строка) и лимит видео в день
    schedule_cron: Mapped[str] = mapped_column(String(64), default="0 9,18 * * *")
    videos_per_day: Mapped[int] = mapped_column(Integer, default=2)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Куда публиковать: ["youtube", "tiktok", "telegram", "vk", "reels"]
    platforms: Mapped[list] = mapped_column(JSON, default=list)
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False)  # иначе очередь модерации
    auto_hashtags: Mapped[bool] = mapped_column(Boolean, default=True)

    voice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    avatar_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    jobs = relationship("Job", back_populates="topic", cascade="all, delete-orphan")
