"""Speaker Diarizer — pyannote speaker diarization.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 1488-1518).
"""

import logging
import os

LOGGER = logging.getLogger(__name__)


def diarize_with_pyannote(
    audio_path: str,
    num_speakers: int = 0,
) -> list[dict]:
    """Perform speaker diarization using pyannote.

    Args:
        audio_path: Path to WAV audio file (16kHz mono).
        num_speakers: Expected number of speakers (0 = auto-detect).

    Returns:
        List of {"start": float, "end": float, "speaker": str}.
    """
    try:
        from pyannote.audio import Pipeline
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or None

        # Try the current pipeline first, then the legacy community pipeline.
        pipeline = None
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=token,
            )
        except Exception:
            LOGGER.info("Using community diarization model")
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization",
                use_auth_token=token,
            )

        pipeline = pipeline.to(torch.device(device))

        kwargs = {}
        if num_speakers > 0:
            kwargs["num_speakers"] = num_speakers

        diarization = pipeline(audio_path, **kwargs)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker,
            })

        return segments

    except ImportError:
        LOGGER.error("pyannote.audio not installed. Run: pip install pyannote.audio")
        raise
    except Exception as e:
        LOGGER.error(f"Diarization failed: {e}")
        raise
