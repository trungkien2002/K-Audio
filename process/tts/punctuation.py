"""Punctuation Pauses — tự động ngắt sau dấu câu.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 1121-1167, 191-261).
"""

import re
from dataclasses import dataclass, field


@dataclass
class PunctuationConfig:
    """Configuration for punctuation pauses."""
    enabled: bool = False
    period: float = 0.0       # . 。
    comma: float = 0.0        # , ，
    semicolon: float = 0.0    # ; ；
    colon: float = 0.0        # : ：
    question: float = 0.0     # ? ？
    exclamation: float = 0.0  # ! ！
    newline: float = 0.0      # \n


# Global config
_config = PunctuationConfig()


def set_punctuation_config(config: PunctuationConfig):
    global _config
    _config = config


def get_punctuation_config() -> PunctuationConfig:
    return _config


# Mapping of punctuation characters to config field names
PUNCTUATION_MAP = {
    ".": "period",
    "。": "period",
    ",": "comma",
    "，": "comma",
    ";": "semicolon",
    "；": "semicolon",
    ":": "colon",
    "：": "colon",
    "?": "question",
    "？": "question",
    "!": "exclamation",
    "！": "exclamation",
    "\n": "newline",
}

# Build regex pattern
_PUNCT_PATTERN = re.compile(
    r'([.。,，;；:：?？!！]|\n)'
)


def add_text_with_punctuation(text: str, config: PunctuationConfig | None = None) -> list[dict]:
    """Split text at punctuation marks and insert silence segments.

    Returns:
        List of dicts:
        - {"type": "text", "content": str}
        - {"type": "silence", "seconds": float}
    """
    if config is None:
        config = _config

    if not config.enabled:
        return [{"type": "text", "content": text}]

    parts = _PUNCT_PATTERN.split(text)
    result = []
    current_text = ""

    for part in parts:
        if part in PUNCTUATION_MAP:
            # This is a punctuation mark
            current_text += part
            field_name = PUNCTUATION_MAP[part]
            pause_seconds = getattr(config, field_name, 0.0)

            if pause_seconds > 0:
                if current_text.strip():
                    result.append({"type": "text", "content": current_text.strip()})
                    current_text = ""
                result.append({"type": "silence", "seconds": pause_seconds})
            # If pause is 0, just keep accumulating text
        else:
            current_text += part

    if current_text.strip():
        result.append({"type": "text", "content": current_text.strip()})

    return result
