"""Точка входа: FastAPI-приложение, lifespan, роутеры, статика SPA."""
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, jobs, publish, settings as settings_api, stats as stats_api, topics
from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.core.security import hash_password
from app.models import User
from app.scheduler import scheduler, start as start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _ensure_env_file() -> None:
    """Вариант Б (запуск без Docker): при первом старте создаёт .env с конфигом.

    Не создаёт .env, если конфигурация задана явно (Docker через compose
    или переменные окружения) или файл уже существует.
    """
    if os.environ.get("CF_DB_URL"):
        return  # Docker / явная конфигурация — .env не нужен
    env_path = Path(".env")
    if env_path.exists():
        return
    secret = secrets.token_urlsafe(32)
    env_path.write_text(
        "# Content Factory — локальный конфиг (создан автоматически при первом запуске)\n"
        "# Смените пароль в панели (Настройки → Безопасность) или здесь.\n"
        f"CF_SECRET_KEY={secret}\n"
        "CF_ADMIN_USERNAME=admin\n"
        "CF_ADMIN_PASSWORD=admin123\n"
        "CF_LICENSE_REQUIRED=false\n"
        "CF_DEMO_MODE=true\n",
        encoding="utf-8",
    )
    # чтобы первый запуск сразу использовал нормальный ключ (без предупреждения в логе)
    if not os.environ.get("CF_SECRET_KEY"):
        settings.secret_key = secret
    logger.info("Создан файл .env с конфигурацией по умолчанию (логин: admin / admin123). Смените пароль!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_env_file()
    # защита от дефолтного секрета: если остался "change-me", заменяем на рантайм-ключ
    if settings.secret_key == "change-me-in-production":
        _tmp = secrets.token_urlsafe(32)
        settings.secret_key = _tmp
        logger.warning("CF_SECRET_KEY не задан — использован временный ключ (перезапуск инвалидирует JWT). Задайте CF_SECRET_KEY в .env!")
    init_db()
    _ensure_admin()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        start_scheduler(db)
    logger.info("%s v%s запущен", settings.app_name, settings.version)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


def _ensure_admin() -> None:
    """Первый администратор из env (CF_ADMIN_USERNAME / CF_ADMIN_PASSWORD)."""
    with SessionLocal() as db:
        if db.query(User).count() == 0:
            db.add(
                User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    is_admin=True,
                )
            )
            db.commit()
            logger.info("Создан администратор %s", settings.admin_username)


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

# --- CORS: "*" с credentials запрещён браузером — исправляем ---
if settings.cors_origins:
    _origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    _allow_credentials = True
    if _origins == ["*"]:
        _allow_credentials = False  # Starlette: нельзя ["*"] + credentials=True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def _security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(jobs.router)
app.include_router(settings_api.router)
app.include_router(publish.router)
app.include_router(stats_api.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


# Медиа (готовые ролики) — статикой
settings.media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")

# SPA: если frontend собран — отдаём статику с фолбэком на index.html
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
