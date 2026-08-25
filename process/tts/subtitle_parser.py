"""Subtitle Parser — Import SRT/VTT/ASS and convert to break tags.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 919-1026).
"""

import re
import logging

LOGGER = logging.getLogger(__name__)


def parse_subtitle_time(time_str: str) -> float:
    """Parse a subtitle timecode string → seconds.

    Supports formats:
    - HH:MM:SS,mmm (SRT)
    - HH:MM:SS.mmm (VTT)
    - H:MM:SS.mm (ASS)
    """
    time_str = time_str.strip().replace(",", ".")

    # HH:MM:SS.mmm
    m = re.match(r'(\d+):(\d+):(\d+)(?:\.(\d+))?', time_str)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ms_str = m.group(4) or "0"
        # Normalize to 3 digits
        ms_str = ms_str.ljust(3, "0")[:3]
        ms = int(ms_str)
        return h * 3600 + mi * 60 + s + ms / 1000.0

    return 0.0


def clean_subtitle_text_line(line: str) -> str:
    """Clean a subtitle text line: remove HTML tags and ASS override codes."""
    # Remove HTML tags
    line = re.sub(r'<[^>]+>', '', line)
    # Remove ASS override codes like {\pos(x,y)}
    line = re.sub(r'\{[^}]*\}', '', line)
    return line.strip()


def subtitle_cues_to_text(cues: list[dict]) -> str:
    """Convert subtitle cues to text with break tags for gaps.

    Args:
        cues: List of {"start": float, "end": float, "text": str}.

    Returns:
        Text with <break time=Xms/> inserted between cues.
    """
    if not cues:
        return ""

    parts = []
    for i, cue in enumerate(cues):
        text = cue["text"].strip()
        if not text:
            continue
        parts.append(text)

        # Calculate gap to next cue
        if i < len(cues) - 1:
            gap = cues[i + 1]["start"] - cue["end"]
            if gap > 0.02:  # Only add break if gap > 20ms
                ms = int(gap * 1000)
                parts.append(f"<break time={ms}ms/>")

    return " ".join(parts)


def parse_srt_or_vtt_to_text(content: str) -> str:
    """Parse SRT or VTT subtitle content to text with break tags."""
    # Remove VTT header
    content = re.sub(r'^WEBVTT\s*\n', '', content, flags=re.IGNORECASE)

    cues = []
    # Match timecodes: 00:00:01,000 --> 00:00:04,000 or 00:00:01.000 --> 00:00:04.000
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        timecode_line = None
        text_lines = []

        for line in lines:
            if '-->' in line:
                timecode_line = line
            elif timecode_line is not None:
                cleaned = clean_subtitle_text_line(line)
                if cleaned:
                    text_lines.append(cleaned)

        if timecode_line and text_lines:
            parts = timecode_line.split('-->')
            if len(parts) == 2:
                start = parse_subtitle_time(parts[0])
                end = parse_subtitle_time(parts[1])
                cues.append({
                    "start": start,
                    "end": end,
                    "text": " ".join(text_lines),
                })

    return subtitle_cues_to_text(cues)


def parse_ass_to_text(content: str) -> str:
    """Parse ASS subtitle content to text with break tags."""
    cues = []

    # Find the Format line to know field positions
    format_line = None
    for line in content.split('\n'):
        if line.strip().startswith('Format:') and 'Text' in line:
            format_line = line
            break

    text_index = 9  # Default ASS text field index
    if format_line:
        fields = [f.strip().lower() for f in format_line.split(':',1)[1].split(',')]
        try:
            text_index = fields.index('text')
        except ValueError:
            text_index = len(fields) - 1

    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('Dialogue:'):
            continue

        # Split but keep everything after text_index as one field
        parts = line.split(',', text_index)
        if len(parts) <= text_index:
            continue

        # Extract timing
        try:
            start = parse_subtitle_time(parts[1].strip())
            end = parse_subtitle_time(parts[2].strip())
        except (IndexError, ValueError):
            continue

        text = parts[text_index] if len(parts) > text_index else ""
        text = clean_subtitle_text_line(text)
        # Replace ASS line break
        text = text.replace('\\N', ' ').replace('\\n', ' ')

        if text:
            cues.append({"start": start, "end": end, "text": text})

    return subtitle_cues_to_text(cues)


def maybe_convert_subtitle_text(text: str) -> str:
    """Auto-detect subtitle format and convert to text with break tags.

    If the text looks like SRT/VTT/ASS, parse it.
    Otherwise return as-is.
    """
    stripped = text.strip()

    # Detect VTT
    if stripped.upper().startswith("WEBVTT"):
        return parse_srt_or_vtt_to_text(text)

    # Detect SRT (starts with number, then timecode)
    if re.match(r'^\d+\s*\n\d{2}:\d{2}:\d{2}', stripped):
        return parse_srt_or_vtt_to_text(text)

    # Detect ASS
    if "[Script Info]" in stripped or "Dialogue:" in stripped:
        return parse_ass_to_text(text)

    return text
