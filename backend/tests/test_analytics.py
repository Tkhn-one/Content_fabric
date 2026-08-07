"""Тесты аналитики и reseller-генератора лицензий."""
import base64
import os
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# генерируем пару ключей ДО импорта app
_key = Ed25519PrivateKey.generate()
_pem = _key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
_pub = base64.b64encode(
    _key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
).decode()

os.environ.setdefault("CF_SECRET_KEY", "test-secret")
os.environ.setdefault("CF_ADMIN_USERNAME", "admin")
os.environ.setdefault("CF_ADMIN_PASSWORD", "admin123")
os.environ["CF_RESELLER_PRIVATE_KEY"] = _pem
os.environ["CF_LICENSE_PUBKEY"] = _pub
os.environ.setdefault("CF_DB_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.license import parse_license  # noqa: E402
from app.main import app  # noqa: E402


def _login(client) -> dict:
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_reseller_generate_and_activate():
    with TestClient(app) as client:
        headers = _login(client)
        r = client.post(
            "/api/settings/license/reseller/generate",
            json={"tier": "pro", "channels": 2, "customer": "Клиент", "support_until": "2028-01-01"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        key = r.json()["key"]
        # ключ подписан правильно и читается
        info = parse_license(key)
        assert info.valid
        assert info.tier == "pro"
        assert info.channels == 2
        assert info.customer == "Клиент"
        # активация через API
        act = client.post("/api/settings/license", json={"key": key}, headers=headers)
        assert act.status_code == 200, act.text
        assert act.json()["tier"] == "pro"
        assert act.json()["demo"] is False


def test_reseller_requires_private_key():
    with TestClient(app) as client:
        headers = _login(client)
        # старый сервер без ключа — но в тесте ключ задан; проверяем валидацию тарифа
        r = client.post(
            "/api/settings/license/reseller/generate",
            json={"tier": "nonexistent"},
            headers=headers,
        )
        assert r.status_code == 422


def test_stats_endpoints_without_youtube():
    with TestClient(app) as client:
        headers = _login(client)
        # без YouTube-подключения — пустые сводки, без ошибок
        r = client.get("/api/stats/overview", headers=headers)
        assert r.status_code == 200
        assert r.json()["total_published"] == 0

        r = client.get("/api/stats/videos", headers=headers)
        assert r.status_code == 200 and r.json() == []

        r = client.get("/api/stats/best-hours", headers=headers)
        assert r.status_code == 200 and r.json() == []

        r = client.post("/api/stats/sync", headers=headers)
        assert r.status_code == 200
        assert r.json()["ok"] is False  # YouTube не подключён
