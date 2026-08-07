from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.user import utcnow

JOB_STATUSES = ("queued", "research", "script", "review", "voiceover", "render", "publish", "done", "failed")


class Job(Base):
    """Задание пайплайна: одна тема → одно видео."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    step: Mapped[str] = mapped_column(String(32), default="queued")

    # Прогресс и результаты шагов (JSON-накопление)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    topic = relationship("Topic", back_populates="jobs")
    publish_logs = relationship("PublishLog", back_populates="job", cascade="all, delete-orphan")
