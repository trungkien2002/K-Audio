"""Online STT — Gemini, Universal 2/3 Pro, Scribe, Whisper API.

Adapted from TTS_Voice_AndyLe-001 (main.py multi-speaker online models).
"""

import os
import logging

LOGGER = logging.getLogger(__name__)

ONLINE_MODELS = [
    "online-gemini-flash-lite-3.1",
    "online-gemini-fast",
    "online-universal-2",
    "online-universal-3-pro",
    "online-scribe",
    "online-whisper",
    "online-diarization-gemini-flash-lite-3.1",
    "online-diarization-gemini-fast",
]


def transcribe_online(
    audio_path: str,
    model_name: str = "online-gemini-fast",
    api_key: str = "",
) -> list[dict]:
    """Transcribe audio using online STT services.

    Returns:
        List of {"start": float, "end": float, "text": str, "speaker": str (optional)}.
    """
    if not api_key:
        if "whisper" in model_name.lower():
            api_key = os.environ.get("OPENAI_API_KEY", "")
        elif "gemini" in model_name.lower():
            api_key = os.environ.get("GEMINI_API_KEY", "")
        else:
            api_key = os.environ.get("STT_API_KEY", "")
    if not api_key:
        LOGGER.error(f"Missing API key for {model_name}")
        return []

    if "gemini" in model_name.lower():
        return _transcribe_gemini(audio_path, model_name, api_key)
    elif "universal" in model_name.lower():
        return _transcribe_universal(audio_path, model_name, api_key)
    elif "scribe" in model_name.lower():
        return _transcribe_scribe(audio_path, api_key)
    elif "whisper" in model_name.lower():
        return _transcribe_whisper_api(audio_path, api_key)
    else:
        LOGGER.warning(f"Unknown online model: {model_name}")
        return []


def _transcribe_gemini(audio_path: str, model_name: str, api_key: str) -> list[dict]:
    """Transcribe using Gemini API."""
    try:
        import requests
        import base64
        import json

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()

        model = "gemini-2.0-flash-lite" if "lite" in model_name else "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [{
                "parts": [
                    {"text": "Transcribe this audio with timestamps. Return JSON array with objects {start, end, text, speaker}."},
                    {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
                ]
            }]
        }

        resp = requests.post(url, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Try to parse JSON from response
            try:
                segments = json.loads(text)
                if isinstance(segments, list):
                    return segments
            except json.JSONDecodeError:
                return [{"start": 0, "end": 0, "text": text}]

    except Exception as e:
        LOGGER.error(f"Gemini transcription failed: {e}")

    return []


def _transcribe_universal(audio_path: str, model_name: str, api_key: str) -> list[dict]:
    """Transcribe using AssemblyAI Universal model."""
    LOGGER.info(f"Universal STT not yet implemented: {model_name}")
    return []


def _transcribe_scribe(audio_path: str, api_key: str) -> list[dict]:
    """Transcribe using ElevenLabs Scribe."""
    LOGGER.info("Scribe STT not yet implemented")
    return []


def _transcribe_whisper_api(audio_path: str, api_key: str) -> list[dict]:
    """Transcribe using OpenAI Whisper API."""
    try:
        import requests

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}

        with open(audio_path, "rb") as f:
            resp = requests.post(
                url,
                headers=headers,
                files={"file": f},
                data={"model": "whisper-1", "response_format": "verbose_json", "language": "vi"},
                timeout=120,
            )

        if resp.status_code == 200:
            data = resp.json()
            segments = data.get("segments", [])
            return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in segments]

    except Exception as e:
        LOGGER.error(f"Whisper API failed: {e}")

    return []
