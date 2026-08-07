"""TTS-провайдеры. edge-tts работает без ключей; ElevenLabs — с ключом заказчика."""
import asyncio
from pathlib import Path

from app.providers.base import TTSProvider

try:
    import edge_tts

    HAS_EDGE = True
except ImportError:
    HAS_EDGE = False


class EdgeTTS(TTSProvider):
    """Бесплатные нейроголоса Microsoft (без ключа). Нужен интернет."""

    VOICES = {
        "ru": "ru-RU-DmitryNeural",
        "en": "en-US-GuyNeural",
        "es": "es-ES-AlvaroNeural",
        "de": "de-DE-ConradNeural",
        "fr": "fr-FR-HenriNeural",
    }

    async def synthesize(self, text: str, voice_id: str | None, lang: str, out_path: Path) -> Path:
        voice = voice_id or self.VOICES.get(lang, "ru-RU-DmitryNeural")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not HAS_EDGE:
            raise RuntimeError("edge-tts не установлен")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_path))
        return out_path


class ElevenLabsTTS(TTSProvider):
    async def synthesize(self, text: str, voice_id: str | None, lang: str, out_path: Path) -> Path:
        raise NotImplementedError("ElevenLabs подключается на этапе 4 (аватар + клон голоса)")
