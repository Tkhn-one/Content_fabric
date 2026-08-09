"""Шаг 1: идеи и «конкуренты» по теме (LLM или встроенный генератор)."""
from sqlalchemy.orm import Session

from app.models import Job, Topic
from app.providers.llm import get_llm


async def run(db: Session, job: Job, topic: Topic) -> None:
    llm = get_llm(db)
    ideas = await llm.generate_ideas(topic.niche, count=6)
    if not ideas:
        ideas = [f"Интересный факт про {topic.niche}", f"Топ-5 {topic.niche}", f"Мифы о {topic.niche}"]

    # «конкуренты»: реальный поиск по YouTube Data API подключится на этапе 6 (аналитика);
    # пока — справочная строка
    competitors = [f"Анализ трендов по запросу «{topic.niche}» (YouTube Data API — этап 6)"]

    payload_data = dict(job.payload or {})
    payload_data["ideas"] = ideas
    payload_data["idea"] = ideas[0] if ideas else topic.niche
    payload_data["competitors"] = competitors
    job.payload = payload_data
    db.commit()
