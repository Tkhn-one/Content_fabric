"""Шаг 1: идеи и «конкуренты» по теме. На этапе 0 — mock LLM (без ключей)."""
from sqlalchemy.orm import Session

from app.models import Job, Topic
from app.providers.llm.mock import MockLLM
from app.providers.registry import get_provider_settings


async def run(db: Session, job: Job, topic: Topic) -> None:
    llm_name, payload = get_provider_settings(db, "llm") or ("mock", {})
    # этап 2+: реальные провайдеры (OpenAI/Gemini) подключатся по имени из настроек;
    # пока всегда используем встроенный генератор (без ключей)
    llm = MockLLM()

    ideas = await llm.generate_ideas(topic.niche, count=6)
    # «конкуренты»: на этапе 0 — заглушка (реальный поиск через YouTube API на этапе 2)
    competitors = [f"Анализ трендов по запросу «{topic.niche}» (YouTube Data API — этап 2)"]

    payload_data = dict(job.payload or {})
    payload_data["ideas"] = ideas
    payload_data["idea"] = ideas[0] if ideas else topic.niche
    payload_data["competitors"] = competitors
    job.payload = payload_data
