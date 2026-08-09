from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.user import utcnow


class LicenseKey(Base):
    """Активированный лицензионный ключ (тариф, маска функций)."""

    __tablename__ = "license_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(String(32), default="demo")
    customer: Mapped[str] = mapped_column(String(128), default="")
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
