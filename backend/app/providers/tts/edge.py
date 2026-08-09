"""TTS-провайдеры. edge-tts работает без ключей и отдаёт тайминги слов
(нужны для кинетических субтитров); ElevenLabs — с ключом заказчика (Pro+)."""
from pathlib import Path

from app.services.wordtimings import Word
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

    async def synthesize(self, text: str, voice_id: str | None, lang: str, out_path: Path) -> tuple[Path, list[Word]]:
        """Озвучка + тайминги слов (WordBoundary). Возвращает (путь, слова)."""
        voice = voice_id or self.VOICES.get(lang, "ru-RU-DmitryNeural")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not HAS_EDGE:
            raise RuntimeError("edge-tts не установлен (pip install edge-tts)")

        communicate = edge_tts.Communicate(text, voice)
        words: list[Word] = []
        with open(out_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # offset/duration в 100-наносекундных единицах
                    words.append(
                        Word(
                            text=chunk.get("text", ""),
                            start=chunk["offset"] / 1e7,
                            end=(chunk["offset"] + chunk["duration"]) / 1e7,
                        )
                    )
        if not words:
            raise RuntimeError("edge-tts не вернул тайминги слов")
        return out_path, words


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs: качественные голоса + клон голоса. Подключается на этапе 4."""

    async def synthesize(self, text: str, voice_id: str | None, lang: str, out_path: Path):
        raise NotImplementedError(
            "ElevenLabs появится на этапе 4 (Pro-тариф): заполните api_key и voice_id в Подключениях"
        )
