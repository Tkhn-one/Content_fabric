"""Общая настройка тестов: единая БД, пересоздаётся перед каждым тестом.

ВАЖНО: conftest импортируется раньше тест-модулей, поэтому env здесь
перекрывает setdefault(...) в отдельных файлах тестов.
"""
import os
import tempfile

_DB_PATH = tempfile.mktemp(prefix="cf_test_", suffix=".db")
os.environ["CF_DB_URL"] = f"sqlite:///{_DB_PATH}"
os.environ.setdefault("CF_SECRET_KEY", "test-secret")
os.environ.setdefault("CF_ADMIN_USERNAME", "admin")
os.environ.setdefault("CF_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("CF_MEDIA_DIR", tempfile.mkdtemp(prefix="cf_media_t_"))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Свежая пустая БД перед каждым тестом (изоляция от остальных тестов)."""
    from app.core.db import engine, init_db

    engine.dispose()  # закрыть соединения к старому файлу
    if os.path.exists(_DB_PATH):
        os.remove(_DB_PATH)
    init_db()
    yield
    engine.dispose()
