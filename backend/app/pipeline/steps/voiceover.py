"""Шаг «Озвучка»: edge-tts (бесплатно) + тайминги слов для кинетических субтитров.
Для формата «фейк-чат» — озвучка каждой реплики своим голосом + склейка с паузами."""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, Topic
from app.providers.registry import get_provider_settings
from app.providers.tts.edge import EdgeTTS
from app.services.ffmpeg import ffmpeg_available, ffmpeg_path, probe_duration

logger = logging.getLogger(__name__)

PAUSE = 0.35  # пауза между репликами, сек

# разные голоса для двух собеседников (ru/en)
DIALOGUE_VOICES = {
    "ru": ["ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"],
    "en": ["en-US-GuyNeural", "en-US-AriaNeural"],
}


def _concat_audio(files: list[Path], out: Path) -> None:
    """Склейка аудиофайлов в один (с паузами между ними) через ffmpeg."""
    exe = ffmpeg_path()
    # генерируем тишину
    silence = out.parent / "silence.mp3"
    import subprocess

    subprocess.run(
        [exe, "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", "-t", str(PAUSE), "-c:a", "aac", str(silence)],
        capture_output=True, text=True, timeout=60,
    )
    inputs: list[str] = []
    for f in files:
        inputs += ["-i", str(f)]
    inputs += ["-i", str(silence)]
    sil_idx = len(files)  # индекс silence среди входов
    n = len(files) * 2 - 1
    # чередуем: rep0, silence, rep1, silence, ..., repN
    parts: list[str] = []
    for i in range(len(files)):
        parts.append(f"[{i}:a]")
        if i < len(files) - 1:
            parts.append(f"[{sil_idx}:a]")
    fc = "".join(parts) + f"concat=n={n}:v=0:a=1[a]"
    cmd = [exe, "-y", *inputs, "-filter_complex", fc, "-map", "[a]", "-c:a", "aac", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg concat dialogue: {res.stderr[-400:]}")


async def _synth_dialogue(db: Session, job: Job, topic: Topic, data: dict) -> None:
    """Озвучивает диалог двумя голосами, склеивает, считает тайминги реплик."""
    dialogue = data.get("dialogue", [])
    job_dir = settings.media_dir / "jobs" / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)

    tts_name, payload = get_provider_settings(db, "tts") or ("edge_tts", {})
    provider = EdgeTTS() if tts_name != "elevenlabs" or not payload.get("api_key") else None
    voices = DIALOGUE_VOICES.get((topic.language or "ru").lower().split("-")[0], DIALOGUE_VOICES["ru"])

    files: list[Path] = []
    timings: list[dict] = []
    t = 0.0
    for i, rep in enumerate(dialogue):
        path = job_dir / f"rep_{i:02d}.mp3"
        voice = voices[rep.get("speaker", 0) % 2]
        try:
            if provider is None:
                raise NotImplementedError("ElevenLabs для диалогов — позже")
            await provider.synthesize(rep["text"], voice, topic.language, path)
            dur = probe_duration(path) or max(1.0, len(rep["text"]) / 13.0)
        except Exception as exc:
            logger.warning("Реплика %s не озвучена: %s", i, exc)
            # оцениваем длительность по тексту
            dur = max(1.2, len(rep["text"]) / 13.0)
        files.append(path)
        timings.append({"start": round(t, 2), "end": round(t + dur, 2), "speaker": rep["speaker"], "text": rep["text"]})
        t += dur + PAUSE

    data["dialogue_timings"] = timings
    try:
        if all(f.exists() for f in files):
            merged = job_dir / "voice.mp3"
            _concat_audio(files, merged)
            data["voice_path"] = str(merged)
            data["voice_note"] = f"edge-tts диалог ({len(dialogue)} реплик)"
    except Exception as exc:
        logger.warning("Склейка диалога не удалась: %s", exc)
        data["voice_path"] = None
        data["voice_note"] = f"склейка диалога пропущена: {exc}"


async def run(db: Session, job: Job, topic: Topic) -> None:
    script = (job.payload or {}).get("script", "")
    if not script:
        raise RuntimeError("Нет сценария — шаг «script» не выполнен")

    job_dir = settings.media_dir / "jobs" / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    voice_path = job_dir / "voice.mp3"
    data = dict(job.payload or {})

    # формат «фейк-чат» — озвучка по репликам
    if data.get("dialogue"):
        try:
            await _synth_dialogue(db, job, topic, data)
            job.payload = data
            db.commit()
            return
        except Exception as exc:
            logger.warning("Диалог-озвучка не удалась, падаем в обычный путь: %s", exc)

    tts_name, payload = get_provider_settings(db, "tts") or ("edge_tts", {})
    try:
        if tts_name == "elevenlabs" and payload.get("api_key"):
            raise NotImplementedError("ElevenLabs — этап 4 (Pro-тариф)")
        provider = EdgeTTS()
        path, words = await provider.synthesize(
            script, topic.voice_id or payload.get("voice_id"), topic.language, voice_path
        )
        data["voice_path"] = str(path)
        data["voice_note"] = "edge-tts"
        data["word_timings"] = [{"text": w.text, "start": w.start, "end": w.end} for w in words]
    except Exception as exc:  # нет сети / лимиты — не валим пайплайн, рендер соберёт без голоса
        logger.warning("Озвучка пропущена: %s", exc)
        data["voice_path"] = None
        data["voice_note"] = f"озвучка пропущена: {exc}"
        data["word_timings"] = []
    job.payload = data
    db.commit()
