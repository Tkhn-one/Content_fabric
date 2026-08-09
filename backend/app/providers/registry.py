"""Реестр провайдеров + хелперы доступа к сохранённым настройкам.

PROVIDERS — справочник для мастера настройки в панели:
  (type, name, metadata: описание, ссылка, бесплатный?, поля формы)
"""
from sqlalchemy.orm import Session

from app.core.security import decrypt_secrets
from app.models import ProviderSettings

PROVIDERS: list[tuple[str, str, dict]] = [
    (
        "llm", "openai",
        {"description": "ChatGPT: идеи, сценарии, хештеги", "url": "platform.openai.com",
         "free": False, "fields": ["api_key"]},
    ),
    (
        "llm", "gemini",
        {"description": "Gemini (Google) — есть бесплатный тариф", "url": "aistudio.google.com",
         "free": True, "fields": ["api_key"]},
    ),
    (
        "llm", "mock",
        {"description": "Встроенный генератор без ключей (демо-режим)", "url": "",
         "free": True, "fields": []},
    ),
    (
        "tts", "edge_tts",
        {"description": "Нейроголоса Microsoft (бесплатно, без ключа)", "url": "",
         "free": True, "fields": []},
    ),
    (
        "tts", "elevenlabs",
        {"description": "Качественные голоса + клон голоса", "url": "elevenlabs.io",
         "free": False, "fields": ["api_key", "voice_id"]},
    ),
    (
        "avatar", "heygen",
        {"description": "HeyGen: AI-аватар, читающий сценарий (Pro+)", "url": "heygen.com",
         "free": False, "fields": ["api_key", "avatar_id", "voice_id"]},
    ),
    (
        "avatar", "did",
        {"description": "D-ID: AI-аватар (Pro+, подключится позже)", "url": "d-id.com",
         "free": False, "fields": ["api_key", "avatar_id"]},
    ),
    (
        "stock", "pexels",
        {"description": "Стоковые кадры Pexels (бесплатно)", "url": "pexels.com/api",
         "free": True, "fields": ["api_key"]},
    ),
    (
        "stock", "pixabay",
        {"description": "Стоковые кадры Pixabay (бесплатно)", "url": "pixabay.com/api",
         "free": True, "fields": ["api_key"]},
    ),
    (
        "stock", "picsum",
        {"description": "Заглушка-сток без ключа (демо)", "url": "", "free": True, "fields": []},
    ),
    (
        "publish", "youtube",
        {"description": "YouTube Data API v3 — публикация Shorts", "url": "console.cloud.google.com",
         "free": True, "fields": ["client_id", "client_secret", "refresh_token", "channel_id"]},
    ),
    (
        "publish", "telegram",
        {"description": "Telegram Bot API — публикация в канал", "url": "t.me/BotFather",
         "free": True, "fields": ["bot_token", "chat_id"]},
    ),
    (
        "publish", "tiktok",
        {"description": "TikTok Content Posting API (нужна модерация приложения)",
         "url": "developers.tiktok.com", "free": True,
         "fields": ["client_key", "client_secret", "access_token", "refresh_token"]},
    ),
    (
        "publish", "vk",
        {"description": "VK API — клипы на стену сообщества", "url": "vk.com/dev",
         "free": True, "fields": ["access_token", "group_id"]},
    ),
    (
        "publish", "instagram",
        {"description": "Instagram Graph API — Reels (Business-аккаунт, нужен публичный server_url)",
         "url": "developers.facebook.com", "free": True,
         "fields": ["access_token", "user_id", "server_url"]},
    ),
    (
        "storage", "google_sheets",
        {"description": "Журнал публикаций в Google Sheets (service account)",
         "url": "console.cloud.google.com", "free": True,
         "fields": ["service_account_json", "spreadsheet_id"]},
    ),
    (
        "storage", "google_drive",
        {"description": "Архив готовых роликов в Google Drive (service account)",
         "url": "console.cloud.google.com", "free": True,
         "fields": ["service_account_json", "folder_id"]},
    ),
]

DEFAULT_BY_TYPE = {"llm": "mock", "tts": "edge_tts", "stock": "picsum"}


def get_provider_settings(db: Session, ptype: str, default_name: str | None = None) -> tuple[str, dict] | None:
    """Возвращает (provider_name, расшифрованный payload) для включённого провайдера типа ptype."""
    name = default_name or DEFAULT_BY_TYPE.get(ptype)
    rows = db.query(ProviderSettings).filter(
        ProviderSettings.provider_type == ptype,
        ProviderSettings.is_enabled.is_(True),
    ).all()
    if not rows:
        if ptype in DEFAULT_BY_TYPE:
            return DEFAULT_BY_TYPE[ptype], {}
        return None
    # предпочитаем default, иначе — последний сохранённый
    rows.sort(key=lambda r: (not r.is_default, -r.id))
    row = rows[0]
    return row.provider_name, decrypt_secrets(row.encrypted_payload)


def get_provider_settings_named(db: Session, ptype: str, provider_name: str) -> dict | None:
    """Настройки конкретного провайдера (например, publish + youtube)."""
    row = (
        db.query(ProviderSettings)
        .filter(
            ProviderSettings.provider_type == ptype,
            ProviderSettings.provider_name == provider_name,
            ProviderSettings.is_enabled.is_(True),
        )
        .first()
    )
    if row is None:
        return None
    return {"provider_name": row.provider_name, "payload": decrypt_secrets(row.encrypted_payload)}
