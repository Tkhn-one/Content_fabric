"""Движок пайплайна: конечный автомат шагов с retry и статусами в БД.

Статусы: queued → research → script → voiceover → render
         → (review | → publish → done)
Если topic.auto_publish=False — пайплайн останавливается на review
(очередь модерации: человек смотрит видео и жмёт «Опубликовать»).
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Job
from app.pipeline.steps import publish as step_publish
from app.pipeline.steps import render as step_render
from app.pipeline.steps import research as step_research
from app.pipeline.steps import script as step_script
from app.pipeline.steps import voiceover as step_voiceover

logger = logging.getLogger(__name__)

STEPS = [
    ("research", step_research.run),
    ("script", step_script.run),
    ("voiceover", step_voiceover.run),
    ("render", step_render.run),
]
MAX_RETRIES = 2


class PipelineEngine:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    # --- публичный API -----------------------------------------------------
    def start(self, db: Session, job_id: int) -> None:
        """Ставит задание в очередь (запускает фоновую задачу)."""
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = "queued"
        job.step = "queued"
        job.error = None
        db.commit()
        task = asyncio.create_task(self._run(job_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def approve(self, db: Session, job_id: int) -> None:
        """Продолжить после модерации: публикуем готовое видео."""
        job = db.get(Job, job_id)
        if job is None or job.status != "review":
            raise ValueError("Задание не в очереди модерации")
        task = asyncio.create_task(self._publish_only(job_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # --- внутренности ------------------------------------------------------
    async def _run(self, job_id: int) -> None:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job is None:
                return
            topic = job.topic
            for step_name, fn in STEPS:
                await self._set_step(db, job, step_name)
                try:
                    await fn(db, job, topic)
                except Exception as exc:
                    await self._fail(db, job, step_name, exc)
                    return
            if topic.auto_publish:
                await self._publish(db, job, topic)
            else:
                await self._set_status(db, job, "review", "render")
        finally:
            db.close()

    async def _publish_only(self, job_id: int) -> None:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if job is None:
                return
            await self._publish(db, job, job.topic)
        finally:
            db.close()

    async def _publish(self, db: Session, job: Job, topic) -> None:
        await self._set_step(db, job, "publish")
        try:
            await step_publish.run(db, job, topic)
        except Exception as exc:
            await self._fail(db, job, "publish", exc)
            return
        await self._set_status(db, job, "done", "done")

    async def _set_step(self, db: Session, job: Job, step: str) -> None:
        job.status = step
        job.step = step
        db.commit()

    async def _set_status(self, db: Session, job: Job, status: str, step: str) -> None:
        job.status = status
        job.step = step
        job.error = None
        db.commit()

    async def _fail(self, db: Session, job: Job, step: str, exc: Exception) -> None:
        job.status = "failed"
        job.step = step
        job.error = f"{step}: {exc}"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.error("Job %s failed on %s: %s", job.id, step, exc)
