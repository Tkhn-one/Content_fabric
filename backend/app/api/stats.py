"""Аналитика: сводка, статистика по видео, лучшие часы публикации."""
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Job, PublishLog, Topic, User
from app.services.analytics import sync_youtube_stats

from .deps import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _user_logs(db: Session, user: User) -> list[PublishLog]:
    return (
        db.query(PublishLog)
        .join(Job)
        .join(Topic)
        .filter(Topic.user_id == user.id)
        .all()
    )


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = _user_logs(db, user)
    published = [l for l in logs if l.status == "published"]
    by_platform: dict[str, dict] = defaultdict(lambda: {"count": 0, "views": 0, "likes": 0, "comments": 0})
    for l in published:
        d = by_platform[l.platform]
        d["count"] += 1
        d["views"] += int((l.stats or {}).get("views", 0))
        d["likes"] += int((l.stats or {}).get("likes", 0))
        d["comments"] += int((l.stats or {}).get("comments", 0))
    return {
        "total_published": len(published),
        "total_views": sum(d["views"] for d in by_platform.values()),
        "total_likes": sum(d["likes"] for d in by_platform.values()),
        "total_comments": sum(d["comments"] for d in by_platform.values()),
        "by_platform": {k: dict(v) for k, v in by_platform.items()},
    }


@router.get("/videos")
def videos(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = _user_logs(db, user)
    rows = []
    for l in sorted(logs, key=lambda x: x.published_at or x.created_at, reverse=True)[:100]:
        rows.append(
            {
                "id": l.id,
                "topic": l.job.topic.name if l.job and l.job.topic else "",
                "platform": l.platform,
                "status": l.status,
                "url": l.url,
                "views": int((l.stats or {}).get("views", 0)),
                "likes": int((l.stats or {}).get("likes", 0)),
                "comments": int((l.stats or {}).get("comments", 0)),
                "published_at": l.published_at.isoformat() if l.published_at else None,
            }
        )
    return rows


@router.get("/best-hours")
def best_hours(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Просмотры по часу публикации (UTC) — подсказка, когда лучше постить."""
    logs = [l for l in _user_logs(db, user) if l.status == "published" and l.published_at]
    by_hour: dict[int, dict] = defaultdict(lambda: {"count": 0, "views": 0})
    for l in logs:
        h = l.published_at.hour
        by_hour[h]["count"] += 1
        by_hour[h]["views"] += int((l.stats or {}).get("views", 0))
    return [
        {"hour": h, "count": d["count"], "views": d["views"]}
        for h, d in sorted(by_hour.items())
    ]


@router.post("/sync")
async def sync(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Синхронизировать статистику YouTube по опубликованным видео."""
    return await sync_youtube_stats(db)
