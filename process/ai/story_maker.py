"""AI Story Maker — tạo truyện tự động bằng AI.

Adapted from TTS_Voice_AndyLe-001 (Story Maker feature).
Supports 10 AI models, 14 languages, text + video modes.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Generator

LOGGER = logging.getLogger(__name__)

# ─────────────────────────── Constants ───────────────────────────

AI_MODELS = [
    "mistral-4", "mistral", "free-mistral",
    "gemini-fast", "gemini-flash-lite-3.1",
    "qwen-safety", "nova-fast",
    "llama", "llama-scout",
    "openai",
]

SUPPORTED_LANGUAGES = [
    "Vietnamese", "English", "Chinese", "Japanese", "Korean",
    "Thai", "Indonesian", "French", "Spanish", "German",
    "Portuguese", "Italian", "Hindi", "Arabic",
]

STORY_TOPICS = [
    "Phiêu lưu", "Tình yêu", "Kinh dị", "Hài hước", "Trinh thám",
    "Khoa học viễn tưởng", "Tiên hiệp", "Võ hiệp", "Lịch sử",
    "Đời thường", "Fantasy", "Truyện cổ tích",
]


@dataclass
class StoryCharacter:
    """A character in the story."""
    name: str
    role: str = ""
    description: str = ""
    voice_id: str = ""


@dataclass
class StoryScene:
    """A single scene in the story."""
    id: int
    narration: str
    media_path: str = ""
    duration: float = 0.0
    transition: str = "fade"
    ken_burns: str = ""  # zoom_in, zoom_out, pan_left, pan_right


@dataclass
class StoryConfig:
    """Configuration for story generation."""
    title: str = ""
    topic: str = "Phiêu lưu"
    model: str = "mistral-4"
    language: str = "Vietnamese"
    num_chapters: int = 1
    length: str = "medium"  # short, medium, long
    characters: list = field(default_factory=list)
    voice_id: str = ""


@dataclass
class StoryResult:
    """Result of story generation."""
    title: str = ""
    text: str = ""
    scenes: list = field(default_factory=list)
    model_used: str = ""


# ─────────────────────────── Generation ──────────────────────────

def generate_text_story(
    config: StoryConfig,
    api_key: str = "",
    stop_event=None,
) -> Generator[str, None, StoryResult]:
    """Generate a text story using AI.

    Yields progress messages. Returns StoryResult.
    """
    yield f"[Story] Using model: {config.model}"
    yield f"[Story] Topic: {config.topic}, Language: {config.language}"

    # Build prompt
    characters_desc = ""
    if config.characters:
        chars = [f"- {c.name}: {c.role} ({c.description})" for c in config.characters]
        characters_desc = "\nNhân vật:\n" + "\n".join(chars)

    length_map = {"short": "500 từ", "medium": "1500 từ", "long": "3000 từ"}
    target_length = length_map.get(config.length, "1500 từ")

    prompt = f"""Viết một câu chuyện bằng {config.language} với các yêu cầu:
- Chủ đề: {config.topic}
- Tiêu đề: {config.title or 'Tự đặt'}
- Độ dài: khoảng {target_length}
- Số chương: {config.num_chapters}
{characters_desc}

Chia truyện thành các scene, mỗi scene bắt đầu bằng [SCENE X]:
Viết sinh động, hấp dẫn, có miêu tả cảnh vật và cảm xúc nhân vật."""

    yield "[Story] Đang sinh truyện..."

    try:
        text = _call_ai_model(config.model, prompt, api_key)
    except Exception as e:
        yield f"[Story] Lỗi: {e}"
        return StoryResult(model_used=config.model)

    if stop_event and stop_event.is_set():
        yield "[Story] Đã hủy"
        return StoryResult(model_used=config.model)

    yield f"[Story] Sinh xong! ({len(text)} ký tự)"

    # Split into scenes
    from process.ai.scene_splitter import split_into_scenes
    scenes = split_into_scenes(text)
    yield f"[Story] Tìm thấy {len(scenes)} scenes"

    result = StoryResult(
        title=config.title or "Untitled Story",
        text=text,
        scenes=scenes,
        model_used=config.model,
    )
    return result


# ─────────────────────────── AI Model Calls ──────────────────────

def _call_ai_model(model: str, prompt: str, api_key: str = "") -> str:
    """Call an AI model to generate text."""
    import requests

    if not api_key:
        api_key = os.environ.get("AI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(f"Chưa cấu hình API key cho model {model}")

    if "gemini" in model.lower():
        return _call_gemini(prompt, api_key, model)
    elif "mistral" in model.lower():
        return _call_mistral(prompt, api_key, model)
    elif "openai" in model.lower():
        return _call_openai(prompt, api_key)
    elif "llama" in model.lower():
        return _call_llama(prompt, api_key, model)
    else:
        raise ValueError(f"Unsupported model: {model}")


def _call_gemini(prompt: str, api_key: str, model: str = "gemini-fast") -> str:
    """Call Google Gemini API."""
    import requests

    model_name = "gemini-2.0-flash" if "fast" in model else "gemini-2.0-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    resp = requests.post(url, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 8192},
    }, timeout=120)

    if resp.status_code == 200:
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError(f"Gemini API error: {resp.status_code}")


def _call_mistral(prompt: str, api_key: str, model: str = "mistral-4") -> str:
    """Call Mistral API."""
    import requests

    model_map = {
        "mistral-4": "mistral-large-latest",
        "mistral": "mistral-medium-latest",
        "free-mistral": "mistral-small-latest",
    }
    model_id = model_map.get(model, "mistral-large-latest")

    resp = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8192,
        },
        timeout=120,
    )

    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    raise RuntimeError(f"Mistral API error: {resp.status_code}")


def _call_openai(prompt: str, api_key: str) -> str:
    """Call OpenAI API."""
    import requests

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8192,
        },
        timeout=120,
    )

    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    raise RuntimeError(f"OpenAI API error: {resp.status_code}")


def _call_llama(prompt: str, api_key: str, model: str = "llama") -> str:
    """Call Meta Llama API (via Together.ai or similar)."""
    import requests

    model_map = {
        "llama": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "llama-scout": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
    }
    model_id = model_map.get(model, model_map["llama"])

    resp = requests.post(
        "https://api.together.xyz/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8192,
        },
        timeout=120,
    )

    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    raise RuntimeError(f"Llama API error: {resp.status_code}")
