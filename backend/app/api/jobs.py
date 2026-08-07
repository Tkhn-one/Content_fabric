"""Задания: ручной запуск, список, детали, повтор ошибки."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.license import demo_limit_reached
from app.models import Job, Topic, User
from app.pipeline.engine import PipelineEngine
from app.schemas.job import JobCreate, JobOut

from .deps import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
engine = PipelineEngine()


@router.post("", response_model=JobOut)
async def create_job(body: JobCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Ручной режим: нажали — получили видео (задание уходит в очередь)."""
    if demo_limit_reached(db):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Демо-режим: лимит {3} роликов. Активируйте лицензию в Подключениях.",
        )
    topic = None
    if body.topic_id:
        topic = db.get(Topic, body.topic_id)
        if topic is None or topic.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Тема не найдена")
        job = Job(topic_id=topic.id)
    else:
        # разовый запуск без сохранения темы
        niche = body.niche or "интересные факты"
        topic = Topic(
            user_id=user.id,
            name=body.name or niche,
            niche=niche,
            language=body.language,
            tone=body.tone,
            template=body.template,
            platforms=body.platforms or [],
            auto_publish=body.auto_publish,
        )
        db.add(topic)
        db.flush()
        job = Job(topic_id=topic.id)

    db.add(job)
    db.commit()
    db.refresh(job)
    engine.start(db, job.id)
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    jobs = (
        db.query(Job)
        .join(Topic)
        .filter(Topic.user_id == user.id)
        .order_by(Job.id.desc())
        .limit(100)
        .all()
    )
    return jobs


@router.get("/{job_id}", response_model=dict)
def job_detail(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if job is None or job.topic.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")
    return {
        "id": job.id,
        "status": job.status,
        "step": job.step,
        "error": job.error,
        "retry_count": job.retry_count,
        "payload": job.payload,
        "publish_logs": [
            {
                "platform": p.platform,
                "status": p.status,
                "url": p.url,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
            for p in job.publish_logs
        ],
    }


@router.post("/{job_id}/approve", response_model=JobOut)
async def approve_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Очередь модерации: человек посмотрел видео и разрешил публикацию."""
    job = db.get(Job, job_id)
    if job is None or job.topic.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")
    try:
        engine.approve(db, job.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return job


@router.post("/{job_id}/retry", response_model=JobOut)
async def retry_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if job is None or job.topic.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")
    job.status = "queued"
    job.step = "queued"
    job.error = None
    job.retry_count += 1
    db.commit()
    engine.start(db, job.id)
    return job
