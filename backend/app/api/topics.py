"""Темы: CRUD + переключение расписания."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Topic, User
from app.schemas.topic import TopicCreate, TopicOut, TopicUpdate
from app.scheduler import resync, validate_cron

from .deps import get_current_user

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("", response_model=list[TopicOut])
def list_topics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Topic).filter(Topic.user_id == user.id).order_by(Topic.id.desc()).all()


@router.post("", response_model=TopicOut)
def create_topic(body: TopicCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not validate_cron(body.schedule_cron):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неверная cron-строка расписания")
    topic = Topic(user_id=user.id, **body.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    resync(db)
    return topic


@router.get("/{topic_id}", response_model=TopicOut)
def get_topic(topic_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = db.get(Topic, topic_id)
    if topic is None or topic.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тема не найдена")
    return topic


@router.patch("/{topic_id}", response_model=TopicOut)
def update_topic(
    topic_id: int,
    body: TopicUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = db.get(Topic, topic_id)
    if topic is None or topic.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тема не найдена")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(topic, field, value)
    if not validate_cron(topic.schedule_cron):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неверная cron-строка расписания")
    db.commit()
    db.refresh(topic)
    resync(db)
    return topic


@router.delete("/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = db.get(Topic, topic_id)
    if topic is None or topic.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тема не найдена")
    db.delete(topic)
    db.commit()
    resync(db)
    return {"ok": True}
