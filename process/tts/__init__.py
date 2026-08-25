"""TTS package — multi-engine Text-to-Speech conversion."""

from process.tts.engine import convert_tts, TTSConfig, ENGINE_IDS

__all__ = ["convert_tts", "TTSConfig", "ENGINE_IDS"]
