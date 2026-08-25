"""TTS Engine coordinator for Edge-TTS, gTTS and OmniVoice."""

import os
from dataclasses import dataclass, field
from typing import Generator


ENGINE_IDS = [
    "edge-tts",
    "gtts",
    "omnivoice",
]


@dataclass
class TTSConfig:
    """Configuration for TTS conversion."""
    engine: str = "edge-tts"
    voice: str = "vi-VN-HoaiMyNeural"
    speed: float = 1.0
    pitch: int = 0
    volume: float = 1.0
    # OmniVoice specific
    guidance_scale: float = 3.0
    temperature: float = 0.7
    num_steps: int = 32


def _split_text(text: str, chunk_size: int = 1000) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    sentences = text.replace('\n', ' ').split('. ')
    chunks = []
    current = ''
    for s in sentences:
        if len(current) + len(s) < chunk_size:
            current += s + '. '
        else:
            if current:
                chunks.append(current.strip())
            current = s + '. '
    if current:
        chunks.append(current.strip())
    return chunks


def convert_tts(
    text: str,
    output_path: str,
    config: TTSConfig | None = None,
    stop_event=None,
    srt_path: str = None,
) -> Generator[str, None, None]:
    """Convert text to speech using the configured engine.

    Yields progress messages.
    """
    if config is None:
        config = TTSConfig()

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    yield f"Starting TTS: {config.engine}..."

    engine = config.engine

    if engine == "edge-tts":
        from process.tts.edge_tts_engine import tts_edge
        yield from tts_edge(text, output_path, config.voice, config.speed, stop_event, srt_path=srt_path)

    elif engine == "gtts":
        from process.tts.gtts_engine import tts_gtts
        yield from tts_gtts(text, output_path, config.voice, stop_event)

    elif engine == "omnivoice":
        from process.tts.omnivoice_engine import tts_omnivoice
        yield from tts_omnivoice(text, output_path, config, stop_event, srt_path=srt_path)

    else:
        yield f"Unknown engine: {engine}"
