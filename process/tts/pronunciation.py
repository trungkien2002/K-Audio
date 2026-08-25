"""Pronunciation Dictionary — từ điển phát âm tùy chỉnh.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 876-887).
"""

import re
import logging

LOGGER = logging.getLogger(__name__)

# Global dictionary state
_dictionary_enabled = True
_dictionary_entries: list[dict] = []


def set_dictionary(entries: list[dict], enabled: bool = True):
    """Set the pronunciation dictionary.

    Args:
        entries: List of {"word": str, "pronunciation": str}.
        enabled: Whether to apply the dictionary.
    """
    global _dictionary_enabled, _dictionary_entries
    _dictionary_enabled = enabled
    # Clean entries
    _dictionary_entries = [
        {"word": e["word"].strip(), "pronunciation": e["pronunciation"].strip()}
        for e in entries
        if e.get("word", "").strip() and e.get("pronunciation", "").strip()
    ]


def get_dictionary() -> list[dict]:
    """Get the current dictionary entries."""
    return list(_dictionary_entries)


def apply_dictionary_to_text(text: str) -> str:
    """Apply pronunciation dictionary replacements to text.

    Replacements are sorted by word length (longest first) to avoid
    nested replacement issues.
    """
    if not _dictionary_enabled or not _dictionary_entries:
        return text

    # Sort by word length descending
    sorted_entries = sorted(_dictionary_entries, key=lambda e: -len(e["word"]))

    out = text
    for entry in sorted_entries:
        word = entry["word"]
        pronunciation = entry["pronunciation"]
        try:
            # Word boundary matching (supports Unicode)
            pattern = r"(?<!\w)" + re.escape(word) + r"(?!\w)"
            out = re.sub(pattern, pronunciation, out, flags=re.IGNORECASE)
        except Exception as e:
            LOGGER.warning(f"Dictionary replacement error for '{word}': {e}")

    return out
