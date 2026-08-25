"""Style Subtitle Templates — 5 built-in templates.

Adapted from TTS_Voice_AndyLe-001 (index.html style subtitle templates).
"""

from dataclasses import dataclass


@dataclass
class SubtitleStyle:
    """Complete subtitle style configuration."""
    name: str = "default"
    font_family: str = "Noto Sans"
    font_size: int = 48
    max_words: int = 5
    bold: bool = True
    position: str = "bottom"  # bottom, center, top

    # Colors (hex)
    primary_color: str = "#FFFFFF"
    highlight_color: str = "#FFD700"
    outline_color: str = "#000000"
    background_color: str = "#00000080"

    # Effects
    outline_width: int = 3
    shadow: int = 2
    highlight_scale: float = 1.2

    # Background mode: words, line_native, none, shadow
    background_mode: str = "words"
    opaque_background: bool = False


# ─────────────────────────── Templates ───────────────────────────

TEMPLATES = {
    "classic": SubtitleStyle(
        name="classic",
        font_family="Noto Sans",
        font_size=48,
        max_words=6,
        bold=True,
        position="bottom",
        primary_color="#FFFFFF",
        highlight_color="#FFD700",
        outline_color="#000000",
        background_color="#00000080",
        outline_width=3,
        shadow=2,
        highlight_scale=1.0,
        background_mode="line_native",
    ),
    "default": SubtitleStyle(
        name="default",
        font_family="Be Vietnam Pro",
        font_size=52,
        max_words=5,
        bold=True,
        position="bottom",
        primary_color="#FFFFFF",
        highlight_color="#00E5FF",
        outline_color="#1A1A2E",
        background_color="#1A1A2E99",
        outline_width=2,
        shadow=3,
        highlight_scale=1.15,
        background_mode="words",
    ),
    "modern": SubtitleStyle(
        name="modern",
        font_family="Inter",
        font_size=56,
        max_words=4,
        bold=True,
        position="bottom",
        primary_color="#E0E0E0",
        highlight_color="#FF6B6B",
        outline_color="#000000",
        background_color="#000000B3",
        outline_width=0,
        shadow=4,
        highlight_scale=1.3,
        background_mode="words",
    ),
    "neo-minimal": SubtitleStyle(
        name="neo-minimal",
        font_family="Montserrat",
        font_size=44,
        max_words=6,
        bold=False,
        position="center",
        primary_color="#FFFFFF",
        highlight_color="#A8E6CF",
        outline_color="#333333",
        background_color="#00000000",
        outline_width=1,
        shadow=1,
        highlight_scale=1.0,
        background_mode="none",
    ),
    "tiktok3w": SubtitleStyle(
        name="tiktok3w",
        font_family="Be Vietnam Pro",
        font_size=64,
        max_words=3,
        bold=True,
        position="center",
        primary_color="#FFFFFF",
        highlight_color="#FF3366",
        outline_color="#000000",
        background_color="#00000000",
        outline_width=4,
        shadow=0,
        highlight_scale=1.5,
        background_mode="none",
    ),
}


def get_template(name: str) -> SubtitleStyle:
    """Get a template by name, or default."""
    return TEMPLATES.get(name, TEMPLATES["default"])


def list_templates() -> list[str]:
    """List available template names."""
    return list(TEMPLATES.keys())
