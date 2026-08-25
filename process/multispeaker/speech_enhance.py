"""Speech Enhancement — demucs vocals separation and fast clean.

Adapted from TTS_Voice_AndyLe-001 multi-speaker speech enhance options.
"""

import os
import subprocess
import tempfile
import logging

LOGGER = logging.getLogger(__name__)


def enhance_speech(audio_path: str, mode: str = "fast_clean") -> str:
    """Apply speech enhancement to audio.

    Args:
        audio_path: Path to input audio WAV file.
        mode: Enhancement mode — "demucs_vocals" or "fast_clean".

    Returns:
        Path to enhanced audio file.
    """
    if mode == "demucs_vocals":
        return _demucs_vocals(audio_path)
    elif mode == "fast_clean":
        return _fast_clean(audio_path)
    else:
        return audio_path


def _demucs_vocals(audio_path: str) -> str:
    """Separate vocals from music using demucs."""
    try:
        import demucs.separate
        import torch

        output_dir = os.path.join(tempfile.gettempdir(), "k_audio_demucs")
        os.makedirs(output_dir, exist_ok=True)

        demucs.separate.main([
            "--two-stems", "vocals",
            "-n", "htdemucs",
            "-o", output_dir,
            audio_path,
        ])

        base = os.path.splitext(os.path.basename(audio_path))[0]
        vocals_path = os.path.join(output_dir, "htdemucs", base, "vocals.wav")

        if os.path.isfile(vocals_path):
            return vocals_path
        LOGGER.warning("Demucs vocals output not found, using original")
        return audio_path

    except ImportError:
        LOGGER.error("demucs not installed. Run: pip install demucs")
        return audio_path
    except Exception as e:
        LOGGER.error(f"Demucs failed: {e}")
        return audio_path


def _fast_clean(audio_path: str) -> str:
    """Quick noise reduction using ffmpeg."""
    output_path = audio_path.replace(".wav", "_clean.wav")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-af", "highpass=f=80,lowpass=f=8000,afftdn=nf=-25",
            "-ar", "16000", "-ac", "1",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=60)
        return output_path
    except Exception as e:
        LOGGER.warning(f"Fast clean failed: {e}")
        return audio_path
