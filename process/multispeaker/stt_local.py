"""Local STT — faster-whisper transcription.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 1457-1485).
"""

import logging

LOGGER = logging.getLogger(__name__)

SUPPORTED_MODELS = ["small", "medium", "large-v3-turbo", "large-v3"]


def _faster_whisper_device():
    """Detect best device for faster-whisper."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"


def _normalize_whisper_model_name(model_name: str) -> str:
    """Normalize model name for faster-whisper."""
    model_name = model_name.strip().lower()
    if model_name not in SUPPORTED_MODELS:
        return "small"
    return model_name


def transcribe_with_faster_whisper(
    audio_path: str,
    model_name: str = "small",
    language: str = "vi",
) -> list[dict]:
    """Transcribe audio using faster-whisper.

    Returns:
        List of {"start": float, "end": float, "text": str}.
    """
    model_name = _normalize_whisper_model_name(model_name)
    device, compute_type = _faster_whisper_device()

    try:
        from faster_whisper import WhisperModel

        LOGGER.info(f"Loading faster-whisper model: {model_name} on {device}")
        model = WhisperModel(model_name, device=device, compute_type=compute_type)

        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            word_timestamps=True,
        )

        results = []
        for segment in segments:
            results.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            })

        return results

    except ImportError:
        LOGGER.error("faster-whisper not installed. Run: pip install faster-whisper")
        raise
    except Exception as e:
        LOGGER.error(f"Transcription failed: {e}")
        raise
