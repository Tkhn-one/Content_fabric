"""Тесты новых фич этапа 6.5: фейк-чат, обложки, демо-лимит."""
import os
import tempfile

os.environ.setdefault("CF_SECRET_KEY", "test-secret")
os.environ.setdefault("CF_ADMIN_USERNAME", "admin")
os.environ.setdefault("CF_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("CF_DB_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ.setdefault("CF_MEDIA_DIR", tempfile.mkdtemp(prefix="cf_media2_"))

import pytest  # noqa: E402

from app.services.chat_render import render_chat_screenshot  # noqa: E402
from app.services.cover import generate_cover  # noqa: E402


def test_demo_limit():
    """В демо-режиме после 3 опубликованных роликов запуск запрещается."""
    from fastapi.testclient import TestClient

    from app.core.config import settings
    from app.core.license import DEMO_MAX_VIDEOS
    from app.main import app

    # другие тесты могли задать CF_LICENSE_PUBKEY — сбрасываем, чтобы был demo-режим
    old_pub = settings.license_pubkey
    settings.license_pubkey = None

    with TestClient(app) as client:
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        # заполняем журнал опубликованными роликами до лимита
        from app.core.db import SessionLocal
        from app.models import PublishLog

        db = SessionLocal()
        for i in range(DEMO_MAX_VIDEOS):
            db.add(PublishLog(job_id=1, platform="youtube", status="published"))
        db.commit()
        db.close()

        # запуск должен быть отклонён
        r = client.post("/api/jobs", json={"niche": "тест"}, headers=headers)
        assert r.status_code == 403
        assert "Демо-режим" in r.json()["detail"]
        settings.license_pubkey = old_pub


def test_chat_screenshot_generated():
    messages = [
        {"speaker": 0, "text": "Слышал, есть кое-что дикое про космос?"},
        {"speaker": 1, "text": "Что? Рассказывай!"},
        {"speaker": 0, "text": "На Венере сутки длиннее года!"},
        {"speaker": 1, "text": "Стоп, такого не может быть…"},
    ]
    out = render_chat_screenshot(messages, "/tmp/test_chat.png", brand="Content Factory")
    assert out.exists()
    assert out.stat().st_size > 10_000  # реально нарисовано
    from PIL import Image

    img = Image.open(out)
    assert img.size == (1080, 1920)


def test_chat_screenshot_many_messages():
    messages = [{"speaker": i % 2, "text": f"Сообщение номер {i} про интересную тему"} for i in range(15)]
    out = render_chat_screenshot(messages, "/tmp/test_chat_many.png")
    assert out.exists() and out.stat().st_size > 10_000


def test_cover_generated():
    out = generate_cover("Топ-5 фактов о космосе, которые удивят", "космос", "/tmp/test_cover.jpg", seed=2)
    assert out.exists()
    from PIL import Image

    img = Image.open(out)
    assert img.size == (1280, 720)


@pytest.mark.skipif(not os.environ.get("RUN_RENDER_TESTS"), reason="медленный тест, RUN_RENDER_TESTS=1")
def test_chat_video_renders():
    import asyncio

    from app.core.db import SessionLocal, init_db
    from app.models import Job, Topic
    from app.pipeline.steps import render as render_step
    from app.services.ffmpeg import ffmpeg_available, probe_duration

    if not ffmpeg_available():
        pytest.skip("нет ffmpeg")
    init_db()
    db = SessionLocal()
    topic = Topic(user_id=1, name="Чат", niche="космос", platforms=["youtube"], template="chat")
    db.add(topic)
    db.flush()
    job = Job(topic_id=topic.id)
    db.add(job)
    db.flush()
    job.payload = {
        "script": "Диалог про космос",
        "dialogue": [
            {"speaker": 0, "text": "Слышал, есть кое-что дикое про космос?"},
            {"speaker": 1, "text": "Что? Рассказывай!"},
            {"speaker": 0, "text": "На Венере сутки длиннее года!"},
        ],
    }
    db.commit()
    asyncio.run(render_step.run(db, job, topic))
    db.refresh(job)
    video = job.payload.get("video_path")
    assert video, job.payload.get("video_note")
    assert probe_duration(video) >= 3
    db.close()
