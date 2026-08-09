"""Подключение к БД (SQLAlchemy 2)."""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}
engine = create_engine(settings.db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Создаёт таблицы (этап 0 — без Alembic; миграции подключим перед релизом)."""
    from app import models  # noqa: F401  (регистрация моделей)

    if settings.db_url.startswith("sqlite"):
        db_path = Path(settings.db_url.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
