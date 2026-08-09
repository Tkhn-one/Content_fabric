"""Безопасность: пароли (PBKDF2), JWT, Fernet-шифрование ключей провайдеров."""
import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet

from .config import settings

ALGORITHM = "HS256"


# --- Пароли ---------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, dk_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return secrets.compare_digest(base64.b64encode(dk).decode(), dk_b64)
    except Exception:
        return False


# --- JWT ------------------------------------------------------------------
def create_access_token(subject: str, expires_minutes: int = 60 * 24 * 7) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode({"sub": subject, "exp": exp}, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


# --- Fernet (хранение API-ключей заказчика) -------------------------------
def _fernet() -> Fernet:
    if settings.fernet_key:
        return Fernet(settings.fernet_key.encode())
    # детерминированный вывод из secret_key — удобно для деплоя без доп. ключа
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt_secrets(data: dict) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_secrets(payload: str | None) -> dict:
    if not payload:
        return {}
    try:
        return json.loads(_fernet().decrypt(payload.encode()))
    except Exception:
        return {}
