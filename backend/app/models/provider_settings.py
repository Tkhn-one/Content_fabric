from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.user import utcnow

# Типы провайдеров
PROVIDER_TYPES = ("llm", "tts", "avatar", "stock", "music", "publish")


class ProviderSettings(Base):
    """Настройки внешнего API-провайдера (ключи заказчика, шифруются Fernet)."""

    __tablename__ = "provider_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_type: Mapped[str] = mapped_column(String(16), index=True)  # llm / tts / ...
    provider_name: Mapped[str] = mapped_column(String(64))             # openai / elevenlabs / ...
    label: Mapped[str] = mapped_column(String(128), default="")
    encrypted_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # Fernet(JSON)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
