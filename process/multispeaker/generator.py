"""Multi-Speaker Generator — sinh audio cho từng speaker segment.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 1591-1683).
"""

import os
import logging
import numpy as np
from typing import Generator

LOGGER = logging.getLogger(__name__)


def generate_multispeaker_audio(
    segments: list,
    voice_map: dict[str, str],
    output_path: str,
    stop_event=None,
) -> Generator[str, None, None]:
    """Generate multi-speaker audio from segments.

    Args:
        segments: List of MultiSpeakerEntry objects.
        voice_map: Mapping of speaker_id → voice_id.
        output_path: Output audio file path.
        stop_event: Threading event to stop generation.

    Yields:
        Progress messages.
    """
    from process.tts.omnivoice_engine import (
        OmniVoiceConfig, tts_omnivoice, SAMPLE_RATE, concat_wavs, save_output_audio,
    )
    from process.tts.voice_manager import find_voice

    audio_parts = []
    total = len(segments)

    for i, seg in enumerate(segments):
        if stop_event and stop_event.is_set():
            yield "Đã hủy"
            return

        speaker = seg.speaker
        text = seg.text.strip()
        if not text:
            continue

        voice_id = voice_map.get(speaker, "")
        voice = find_voice(voice_id) if voice_id else None

        yield f"[{i + 1}/{total}] {speaker}: {text[:40]}..."

        # Generate audio for this segment
        config = OmniVoiceConfig(
            voice_id=voice_id,
            voice_path=voice.path if voice else "",
        )

        import tempfile
        tmp_path = os.path.join(tempfile.gettempdir(), f"ms_seg_{i:04d}.wav")
        msgs = list(tts_omnivoice(text, tmp_path, config, stop_event))

        if os.path.isfile(tmp_path):
            import soundfile as sf
            data, sr = sf.read(tmp_path)
            audio_parts.append(data.astype(np.float32))
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        # Add gap between segments
        if i < total - 1:
            next_seg = segments[i + 1]
            gap = next_seg.start - seg.end
            if gap > 0.05:
                silence = np.zeros(int(gap * SAMPLE_RATE), dtype=np.float32)
                audio_parts.append(silence)

    if not audio_parts:
        yield "Không sinh được audio"
        return

    yield "Ghép audio..."
    final_audio = concat_wavs(audio_parts)
    save_output_audio(final_audio, output_path)
    yield f"Done: {output_path} ({len(final_audio) / SAMPLE_RATE:.1f}s)"


def export_multispeaker_subtitle(
    segments: list,
    output_path: str,
    format: str = "srt",
):
    """Export multi-speaker segments as subtitle file."""
    def _fmt_time_srt(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _fmt_time_vtt(seconds):
        return _fmt_time_srt(seconds).replace(",", ".")

    lines = []
    if format == "srt":
        for i, seg in enumerate(segments, 1):
            lines.append(str(i))
            lines.append(f"{_fmt_time_srt(seg.start)} --> {_fmt_time_srt(seg.end)}")
            lines.append(f"[{seg.speaker}] {seg.text}")
            lines.append("")
    elif format == "vtt":
        lines.append("WEBVTT")
        lines.append("")
        for seg in segments:
            lines.append(f"{_fmt_time_vtt(seg.start)} --> {_fmt_time_vtt(seg.end)}")
            lines.append(f"[{seg.speaker}] {seg.text}")
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
