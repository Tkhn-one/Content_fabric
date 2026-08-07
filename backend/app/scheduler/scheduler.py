"""Планировщик: cron-расписания тем → авто-создание заданий.

APScheduler (AsyncIOScheduler) + CronTrigger из строки cron.
Пересоздание расписаний — resync() при старте и после изменения тем.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, Topic
from app.pipeline.engine import PipelineEngine

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
engine = PipelineEngine()


def validate_cron(expr: str) -> bool:
    try:
        CronTrigger.from_crontab(expr)
        return True
    except ValueError:
        return False


def _on_topic_tick(topic_id: int) -> None:
    """Срабатывание расписания: создаём задание и запускаем пайплайн."""
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        topic = db.get(Topic, topic_id)
        if topic is None or not topic.enabled:
            return
        job = Job(topic_id=topic.id)
        db.add(job)
        db.commit()
        db.refresh(job)
        engine.start(db, job.id)
        logger.info("Планировщик: создано задание %s для темы %s", job.id, topic.name)
    finally:
        db.close()


def resync(db: Session) -> None:
    """Пересобирает cron-джобы для всех включённых тем."""
    if not settings.scheduler_enabled:
        return
    topics = db.query(Topic).filter(Topic.enabled.is_(True)).all()
    ids = set()
    for topic in topics:
        if not validate_cron(topic.schedule_cron):
            logger.warning("Тема %s: неверный cron %s", topic.id, topic.schedule_cron)
            continue
        job_id = f"topic-{topic.id}"
        ids.add(job_id)
        scheduler.add_job(
            _on_topic_tick,
            CronTrigger.from_crontab(topic.schedule_cron),
            args=[topic.id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
    # убираем джобы удалённых/отключённых тем
    for existing in list(scheduler.get_jobs()):
        if existing.id.startswith("topic-") and existing.id not in ids:
            scheduler.remove_job(existing.id)
    logger.info("Планировщик: %d расписаний активно", len(ids))


def start(db: Session) -> None:
    if not scheduler.running:
        scheduler.start()
    resync(db)
