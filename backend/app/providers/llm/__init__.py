"""Фабрика LLM-провайдеров: по настройкам выбирает OpenAI/Gemini или встроенный mock."""
from sqlalchemy.orm import Session

from app.providers.base import LLMProvider
from app.providers.llm.gemini import GeminiLLM
from app.providers.llm.mock import MockLLM
from app.providers.llm.openai import OpenAILLM
from app.providers.registry import get_provider_settings


def get_llm(db: Session) -> LLMProvider:
    """Возвращает LLM по настройкам; без ключа — встроенный mock (без внешних API)."""
    cfg = get_provider_settings(db, "llm")
    name, payload = cfg or ("mock", {})
    key = (payload or {}).get("api_key")
    if name == "openai" and key:
        return OpenAILLM(key, payload.get("model") or "gpt-4o-mini")
    if name == "gemini" and key:
        return GeminiLLM(key, payload.get("model") or "gemini-1.5-flash")
    return MockLLM()
