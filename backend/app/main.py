"""Точка входа: FastAPI-приложение, lifespan, роутеры, статика SPA."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, jobs, publish, settings as settings_api, topics
from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.core.security import hash_password
from app.models import User
from app.scheduler import scheduler, start as start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
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

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(jobs.router)
app.include_router(settings_api.router)
app.include_router(publish.router)


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
