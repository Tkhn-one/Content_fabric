"""ElevenLabs: качественные голоса и клон голоса (Pro+). Ключ заказчика.

Тайминги слов: ElevenLabs не отдаёт их в базовом API — оцениваем по длительности
(для кинетических субтитров достаточно).
"""
from pathlib import Path

import httpx

from app.providers.base import TTSProvider
from app.services.ffmpeg import probe_duration
from app.services.wordtimings import Word, estimate_word_timings


class ElevenLabsTTS(TTSProvider):
    BASE = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def synthesize(self, text: str, voice_id: str | None, lang: str, out_path: Path):
        voice = voice_id or "21m00Tcm4TlvDq8ikWAM"  # default: Rachel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE}/text-to-speech/{voice}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
            )
            resp.raise_for_status()
            out_path.write_bytes(resp.content)

        duration = probe_duration(out_path)
        words = estimate_word_timings(text, duration)
        return out_path, words
