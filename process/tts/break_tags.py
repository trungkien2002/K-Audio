"""Break Tags & Audio Tags — xử lý thẻ tạm dừng và audio tags.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 891-1189).
"""

import re
import logging

LOGGER = logging.getLogger(__name__)


# ─────────────────────────── Break Tag Parsing ───────────────────

def parse_break_seconds(tag: str) -> float:
    """Parse a break tag like '<break time=500ms/>' → 0.5 seconds."""
    m = re.search(r'<break\s+time\s*=\s*["\']?(\d+(?:\.\d+)?)\s*(ms|s)["\']?\s*/?\s*>', tag, re.I)
    if m:
        value = float(m.group(1))
        unit = m.group(2).lower()
        return value / 1000.0 if unit == "ms" else value
    return 0.0


def format_break_seconds(seconds: float) -> str:
    """Format seconds as a break tag string."""
    if seconds < 1.0:
        ms = int(seconds * 1000)
        return f"<break time={ms}ms/>"
    else:
        return f"<break time={seconds:.2f}s/>"


# ─────────────────────────── Audio Tags (Gemini-style) ───────────

AUDIO_TAG_SILENCE_SECONDS = {
    # Timing
    "pause": 0.7,
    "short pause": 0.3,
    "long pause": 1.5,
    # Non-verbal
    "breath": 0.5,
    "breathes": 0.5,
    "inhales": 0.6,
    "exhales": 0.6,
    "sigh": 0.8,
    "sighs": 0.8,
    "cough": 0.5,
    "coughs": 0.5,
    "gasp": 0.4,
    "gasps": 0.4,
    "laugh": 0.6,
    "laughs": 0.6,
    "giggles": 0.5,
}

STYLE_AUDIO_TAGS = {
    "whisper", "whispers", "whispering",
    "sarcastic", "sarcastically",
    "serious", "seriously",
    "excited", "excitedly",
    "bored", "reluctantly",
    "slow", "very slow",
    "fast", "very fast",
    "shouting", "shout",
    "tired", "curious", "amazed", "crying",
    "mischievously", "panicked", "trembling",
}


def parse_audio_tag_seconds(tag_text: str) -> float | None:
    """Parse an audio tag like '[pause 1s]' → seconds, or None if not timing."""
    tag_lower = tag_text.lower().strip()

    # Check for explicit timing: [pause 1s], [silence 500ms], [break 2s]
    m = re.match(r'(pause|silence|break)\s+(\d+(?:\.\d+)?)\s*(ms|s)?', tag_lower)
    if m:
        value = float(m.group(2))
        unit = (m.group(3) or "s").lower()
        return value / 1000.0 if unit == "ms" else value

    # Check known non-verbal tags
    if tag_lower in AUDIO_TAG_SILENCE_SECONDS:
        return AUDIO_TAG_SILENCE_SECONDS[tag_lower]

    return None


def strip_or_convert_audio_tags(text: str) -> str:
    """Process Gemini-style audio tags in text.

    - Timing tags → <break time=Xms/>
    - Non-verbal sounds → <break time=Xms/>
    - Style tags → removed silently
    """
    def _replace_tag(match):
        tag_content = match.group(1).strip()
        tag_lower = tag_content.lower()

        # Check style tags (remove silently)
        if tag_lower in STYLE_AUDIO_TAGS:
            return ""

        # Check for timing/non-verbal
        seconds = parse_audio_tag_seconds(tag_content)
        if seconds is not None and seconds > 0:
            return format_break_seconds(seconds)

        # Unknown tag — keep as text
        return tag_content

    return re.sub(r'\[([^\]]+)\]', _replace_tag, text)


# ─────────────────────────── Generation Plan ─────────────────────

def build_generation_plan(text: str) -> list[dict]:
    """Build a generation plan: list of text chunks and silence breaks.

    Returns:
        List of dicts, each with:
        - {"type": "text", "content": str}
        - {"type": "silence", "seconds": float}
    """
    plan = []

    # Split at break tags
    parts = re.split(r'(<break\s+time\s*=\s*[^>]+>)', text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check if this is a break tag
        if re.match(r'<break\s+time', part, re.I):
            seconds = parse_break_seconds(part)
            if seconds > 0:
                plan.append({"type": "silence", "seconds": seconds})
        else:
            # Split long text into chunks
            from process.tts.omnivoice_engine import split_text
            chunks = split_text(part)
            for chunk in chunks:
                if chunk.strip():
                    plan.append({"type": "text", "content": chunk})

    return plan
