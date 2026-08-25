"""Style Subtitle Renderer — render styled subtitles onto video.

Uses FFmpeg drawtext filter to burn subtitles onto video.
"""

import os
import re
import subprocess
import logging
from process.style_subtitles.templates import SubtitleStyle, get_template

LOGGER = logging.getLogger(__name__)


def _hex_to_ffmpeg_color(hex_color: str) -> str:
    """Convert hex color (with optional alpha) to FFmpeg format."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 8:
        r, g, b, a = hex_color[:2], hex_color[2:4], hex_color[4:6], hex_color[6:8]
        return f"0x{a}{r}{g}{b}"
    elif len(hex_color) == 6:
        return f"0x00{hex_color}"
    return "0x00FFFFFF"


def _position_y(style: SubtitleStyle, video_height: int) -> str:
    """Calculate Y position expression for FFmpeg drawtext."""
    if style.position == "top":
        return "h*0.08"
    elif style.position == "center":
        return "(h-text_h)/2"
    else:  # bottom
        return "h*0.85-text_h"


def render_style_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    style: SubtitleStyle | None = None,
    template_name: str = "default",
    log_callback=None,
) -> bool:
    """Render styled subtitles onto a video using FFmpeg.

    Args:
        video_path: Input video path.
        subtitle_path: SRT/ASS subtitle file path.
        output_path: Output video path.
        style: Custom SubtitleStyle (overrides template).
        template_name: Template name if style is None.
        log_callback: Optional progress callback.

    Returns:
        True if successful.
    """
    if style is None:
        style = get_template(template_name)

    def _log(msg):
        if log_callback:
            log_callback(msg)
        LOGGER.info(msg)

    _log(f"Rendering subtitles with style: {style.name}")

    ext = os.path.splitext(subtitle_path)[1].lower()

    # For ASS files, use the subtitles filter directly (preserves styling)
    if ext == ".ass":
        filter_str = f"subtitles='{subtitle_path.replace(os.sep, '/')}'"
    else:
        # For SRT, build a styled subtitle filter
        force_style = _build_force_style(style)
        sub_path = subtitle_path.replace(os.sep, "/").replace(":", "\\:")
        filter_str = f"subtitles='{sub_path}':force_style='{force_style}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        output_path,
    ]

    _log(f"Running FFmpeg...")
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if process.returncode == 0:
            _log(f"Done: {output_path}")
            return True
        else:
            _log(f"FFmpeg error: {process.stderr[:500]}")
            return False
    except Exception as e:
        _log(f"Error: {e}")
        return False


def _build_force_style(style: SubtitleStyle) -> str:
    """Build the force_style string for FFmpeg subtitles filter."""
    parts = [
        f"FontName={style.font_family}",
        f"FontSize={style.font_size}",
        f"PrimaryColour={_hex_to_ffmpeg_color(style.primary_color)}",
        f"OutlineColour={_hex_to_ffmpeg_color(style.outline_color)}",
        f"BackColour={_hex_to_ffmpeg_color(style.background_color)}",
        f"Outline={style.outline_width}",
        f"Shadow={style.shadow}",
    ]
    if style.bold:
        parts.append("Bold=1")

    # Alignment (ASS numbering: 2=bottom-center, 5=center, 8=top-center)
    alignment = {"bottom": 2, "center": 5, "top": 8}.get(style.position, 2)
    parts.append(f"Alignment={alignment}")

    if style.opaque_background:
        parts.append("BorderStyle=4")

    return ",".join(parts)
