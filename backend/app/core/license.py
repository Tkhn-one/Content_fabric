"""Лицензирование: Ed25519-подпись ключа, маска функций и тариф.

Формат ключа:  base64(payload).base64(signature)
payload (JSON): {tier, features: [..], channels, support_until, customer}

На этапе 0 лицензия опциональна: без ключа и без CF_LICENSE_PUBKEY работаем в demo-режиме
(watermark), что удобно для продажи «попробуй перед покупкой».
"""
import base64
import json
from datetime import date

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .config import settings

DEMO_MAX_VIDEOS = 3  # лимит роликов в демо-режиме


def demo_limit_reached(db) -> bool:
    """True, если демо-режим и лимит роликов исчерпан."""
    from app.models import LicenseKey, PublishLog

    row = db.query(LicenseKey).first()
    info = parse_license(row.key if row else "")
    if not info.demo:
        return False
    published = db.query(PublishLog).filter(PublishLog.status == "published").count()
    return published >= DEMO_MAX_VIDEOS


TIERS = {
    "basic": {
        "features": [
            "faceless", "youtube", "sheets_drive", "review_queue",
            "research", "templates", "scheduler",
        ],
        "channels": 1,
    },
    "pro": {
        "features": [
            "faceless", "youtube", "sheets_drive", "review_queue",
            "research", "templates", "scheduler",
            "avatar", "voice_clone", "tiktok", "telegram", "multilang",
            "hashtags",
        ],
        "channels": 3,
    },
    "unlimited": {
        "features": [
            "faceless", "youtube", "sheets_drive", "review_queue",
            "research", "templates", "scheduler",
            "avatar", "voice_clone", "tiktok", "telegram", "multilang",
            "hashtags", "reels", "vk", "analytics", "multichannel",
            "white_label", "reseller_keys",
        ],
        "channels": 10,
    },
}


class LicenseInfo:
    def __init__(self, payload: dict | None):
        self.payload = payload or {}
        self.valid = bool(self.payload)
        self.demo = payload is None or payload.get("demo", False)
        self.tier = self.payload.get("tier", "demo")
        self.features = set(self.payload.get("features", []) if self.payload else [])
        self.channels = int(self.payload.get("channels", 1) or 1)
        self.customer = self.payload.get("customer", "")
        self.support_until = self.payload.get("support_until", "")

    def has_feature(self, feature: str) -> bool:
        if self.demo:
            # в demo открываем всё, но помечаем водяным знаком
            return True
        return feature in self.features


def _load_public_key() -> Ed25519PublicKey | None:
    if not settings.license_pubkey:
        return None
    try:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(settings.license_pubkey))
    except Exception:
        return None


def parse_license(key: str) -> LicenseInfo:
    """Проверяет ключ лицензии. Без настроенного pubkey — demo-режим."""
    if not settings.license_pubkey:
        return LicenseInfo({"demo": True})
    if not key:
        return LicenseInfo(None)
    try:
        payload_b64, sig_b64 = key.strip().split(".")
        pub = _load_public_key()
        if pub is None:
            return LicenseInfo({"demo": True})
        pub.verify(base64.b64decode(sig_b64), payload_b64.encode())
        payload = json.loads(base64.b64decode(payload_b64))
        if payload.get("support_until") and payload["support_until"] < date.today().isoformat():
            return LicenseInfo(None)
        return LicenseInfo(payload)
    except (ValueError, InvalidSignature, json.JSONDecodeError):
        return LicenseInfo(None)
