"""TTS-провайдеры: edge-tts (бесплатно, без ключа) и ElevenLabs (Pro+)."""
from app.providers.tts.edge import EdgeTTS
from app.providers.tts.elevenlabs import ElevenLabsTTS

__all__ = ["EdgeTTS", "ElevenLabsTTS"]
