"""Конфигурация приложения. Все значения переопределяются переменными окружения (префикс CF_)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="CF_", extra="ignore", case_sensitive=False
    )

    app_name: str = "Content Factory"
    version: str = "0.1.0"

    # Безопасность
    secret_key: str = "change-me-in-production"  # JWT-подпись
    fernet_key: str | None = None                # мастер-ключ шифрования ключей провайдеров
    admin_username: str = "admin"
    admin_password: str = "admin123"

    # База данных и медиа
    db_url: str = "sqlite:///./data/cf.db"
    media_dir: Path = Path("./data/media")

    # Лицензия (этап 0: опционально, демо-режим)
    license_pubkey: str | None = None
    license_required: bool = False
    demo_mode: bool = True

    # Планировщик
    scheduler_enabled: bool = True
    scheduler_interval_sec: int = 60

    # Водяной знак (демо-режим) и шрифт субтитров
    watermark: str = "Content Factory"
    subtitle_font: str = "DejaVu Sans"

    # CORS (для dev-режима frontend на отдельном порту)
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
