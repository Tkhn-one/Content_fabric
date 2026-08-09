"""Smoke-тесты этапа 0: авторизация → тема → пайплайн → публикация.

Запуск:  cd backend && PYTHONPATH=. pytest tests/ -v
"""
import os
import tempfile
import time

os.environ.setdefault("CF_SECRET_KEY", "test-secret")
os.environ.setdefault("CF_ADMIN_USERNAME", "admin")
os.environ.setdefault("CF_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("CF_DB_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _login(client) -> dict:
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _wait_status(client, headers, job_id, targets, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/jobs/{job_id}", headers=headers)
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status in targets:
            return resp.json()
        time.sleep(1)
    raise AssertionError(f"job {job_id} не достиг статуса {targets}")


def test_full_flow():
    with TestClient(app) as client:
        headers = _login(client)

        # тема
        r = client.post(
            "/api/topics",
            json={
                "name": "Факты о космосе", "niche": "космос", "language": "ru",
                "template": "facts", "schedule_cron": "0 9,18 * * *",
                "platforms": ["youtube", "telegram"], "auto_publish": False,
            },
            headers=headers,
        )
        assert r.status_code == 200, r.text
        topic_id = r.json()["id"]

        # ручной запуск → пайплайн доходит до модерации (auto_publish=False)
        r = client.post("/api/jobs", json={"topic_id": topic_id}, headers=headers)
        assert r.status_code == 200, r.text
        job_id = r.json()["id"]
        data = _wait_status(client, headers, job_id, {"review", "done"})
        assert data["status"] == "review", data
        assert data["payload"].get("script"), "сценарий должен быть сгенерирован"

        # модерация → публикация (ключи платформ не настроены → статусы skipped)
        r = client.post(f"/api/jobs/{job_id}/approve", headers=headers)
        assert r.status_code == 200, r.text
        data = _wait_status(client, headers, job_id, {"done"})
        assert len(data["publish_logs"]) == 2, data["publish_logs"]
        assert all(p["status"] == "skipped" for p in data["publish_logs"]), data["publish_logs"]

        # журнал
        r = client.get("/api/publish/log", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 2

        # авто-режим (без модерации)
        r = client.post(
            "/api/jobs",
            json={"niche": "деньги", "platforms": ["youtube"], "auto_publish": True},
            headers=headers,
        )
        job_id = r.json()["id"]
        data = _wait_status(client, headers, job_id, {"done"})
        assert data["status"] == "done"


def test_provider_settings_encrypted():
    with TestClient(app) as client:
        headers = _login(client)

        r = client.post(
            "/api/settings/providers",
            json={"provider_type": "llm", "provider_name": "openai", "payload": {"api_key": "sk-super-secret"}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        # в ответе не должно быть ключа
        assert "sk-super-secret" not in r.text

        # справочник провайдеров
        r = client.get("/api/settings/providers/catalog", headers=headers)
        assert r.status_code == 200
        assert any(p["name"] == "youtube" for p in r.json())
