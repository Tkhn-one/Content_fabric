"""Шаг 3: озвучка. edge-tts бесплатно; при ошибке — помечаем и продолжаем."""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, Topic
from app.providers.registry import get_provider_settings
from app.providers.tts.edge import EdgeTTS

logger = logging.getLogger(__name__)


async def run(db: Session, job: Job, topic: Topic) -> None:
    script = (job.payload or {}).get("script", "")
    if not script:
        raise RuntimeError("Нет сценария — шаг «script» не выполнен")

    job_dir = settings.media_dir / "jobs" / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    voice_path = job_dir / "voice.mp3"

    tts_name, payload = get_provider_settings(db, "tts") or ("edge_tts", {})
    data = dict(job.payload or {})
    try:
        if tts_name == "elevenlabs" and payload.get("api_key"):
            raise NotImplementedError("ElevenLabs — этап 4")
        provider = EdgeTTS()
        await provider.synthesize(script, topic.voice_id or payload.get("voice_id"), topic.language, voice_path)
        data["voice_path"] = str(voice_path)
        data["voice_note"] = "edge-tts"
    except Exception as exc:  # нет сети/ffmpeg и т.п. — не валим пайплайн на этапе 0
        logger.warning("Озвучка пропущена: %s", exc)
        data["voice_path"] = None
        data["voice_note"] = f"озвучка пропущена: {exc}"
    job.payload = data
    db.commit()
