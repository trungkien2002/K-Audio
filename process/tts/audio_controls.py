"""Audio Controls — post-processing: pitch shift, volume adjust.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 1192-1219).
"""

import math
import logging
import numpy as np

LOGGER = logging.getLogger(__name__)


def clamp_audio_value(value: float, default: float, min_val: float, max_val: float) -> float:
    """Clamp a value within range, returning default if invalid."""
    try:
        v = float(value)
        return max(min_val, min(max_val, v))
    except (TypeError, ValueError):
        return default


def apply_audio_controls(
    audio: np.ndarray,
    sample_rate: int,
    pitch: float = 1.0,
    volume: float = 1.0,
) -> np.ndarray:
    """Apply pitch shift and volume adjustment to audio.

    Args:
        audio: numpy array of audio samples (float32).
        sample_rate: Audio sample rate.
        pitch: Pitch multiplier (0.5 to 2.0). 1.0 = no change.
        volume: Volume multiplier (0.1 to 2.0). 1.0 = no change.

    Returns:
        Processed audio array.
    """
    pitch = clamp_audio_value(pitch, 1.0, 0.5, 2.0)
    volume = clamp_audio_value(volume, 1.0, 0.1, 2.0)

    result = audio.copy()

    # Apply pitch shift
    if pitch != 1.0:
        try:
            import torch
            import torchaudio
            n_steps = 12 * math.log2(pitch)
            wav_tensor = torch.FloatTensor(result).unsqueeze(0)
            shifted = torchaudio.functional.pitch_shift(
                wav_tensor, sample_rate, n_steps
            )
            result = shifted.squeeze(0).numpy()
        except ImportError:
            LOGGER.warning("torchaudio not available for pitch shift, skipping")
        except Exception as e:
            LOGGER.warning(f"Pitch shift failed: {e}")

    # Apply volume
    if volume != 1.0:
        result = result * volume
        result = np.clip(result, -0.98, 0.98)

    return result.astype(np.float32)
