"""Журнал публикаций (для панели и экспорта в Sheets на этапе 2)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Job, PublishLog, Topic, User

from .deps import get_current_user

router = APIRouter(prefix="/api/publish", tags=["publish"])


@router.get("/log")
def publish_log(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(PublishLog)
        .join(Job)
        .join(Topic)
        .filter(Topic.user_id == user.id)
        .order_by(PublishLog.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "platform": r.platform,
            "status": r.status,
            "url": r.url,
            "stats": r.stats,
            "published_at": r.published_at.isoformat() if r.published_at else None,
        }
        for r in rows
    ]
