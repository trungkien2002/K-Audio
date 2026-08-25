"""Multi-Speaker Analyzer — pipeline phân tích media → speakers → segments.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 1406-1566).
"""

import os
import subprocess
import logging
import tempfile
from dataclasses import dataclass, field

LOGGER = logging.getLogger(__name__)

MULTISPEAKER_TMP_DIR = os.path.join(tempfile.gettempdir(), "k_audio_multispeaker")


@dataclass
class MultiSpeakerEntry:
    """A single segment from multi-speaker analysis."""
    start: float
    end: float
    speaker: str
    text: str
    voice_id: str = ""

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "speaker": self.speaker,
            "text": self.text,
            "voice_id": self.voice_id,
        }


def extract_audio_for_diarization(media_path: str, output_dir: str | None = None) -> str:
    """Extract audio from media file using ffmpeg for STT/diarization."""
    if output_dir is None:
        output_dir = MULTISPEAKER_TMP_DIR
    os.makedirs(output_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(media_path))[0]
    output_path = os.path.join(output_dir, f"{base}_audio.wav")

    cmd = [
        "ffmpeg", "-y", "-i", media_path,
        "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
        output_path,
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
    except Exception as e:
        LOGGER.error(f"Audio extraction failed: {e}")
        raise

    return output_path


def merge_transcript_and_diarization(
    transcript_segments: list[dict],
    diarization_segments: list[dict],
) -> list[MultiSpeakerEntry]:
    """Merge transcription segments with diarization speaker labels."""
    entries = []

    for t_seg in transcript_segments:
        t_start = t_seg["start"]
        t_end = t_seg["end"]
        t_text = t_seg["text"]

        # Find the best matching diarization segment
        best_speaker = "SPEAKER_00"
        best_overlap = 0

        for d_seg in diarization_segments:
            d_start = d_seg["start"]
            d_end = d_seg["end"]
            overlap = max(0, min(t_end, d_end) - max(t_start, d_start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d_seg.get("speaker", "SPEAKER_00")

        entries.append(MultiSpeakerEntry(
            start=t_start,
            end=t_end,
            speaker=best_speaker,
            text=t_text,
        ))

    return entries


def analyze_multispeaker_media(
    media_path: str,
    stt_model: str = "small",
    num_speakers: int = 0,
    speech_enhance: str = "off",
    log_callback=None,
) -> list[MultiSpeakerEntry]:
    """Full pipeline: media → extract audio → transcribe → diarize → merge.

    Args:
        media_path: Path to media file (video or audio).
        stt_model: STT model name (small, medium, large-v3-turbo, large-v3, or online).
        num_speakers: Expected number of speakers (0 = auto-detect).
        speech_enhance: Enhancement mode (off, demucs_vocals, fast_clean).
        log_callback: Optional callback for progress messages.

    Returns:
        List of MultiSpeakerEntry with speaker labels.
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)
        LOGGER.info(msg)

    _log("[1/4] Extracting audio...")
    audio_path = extract_audio_for_diarization(media_path)

    # Apply speech enhancement if requested
    if speech_enhance != "off":
        _log(f"[1.5/4] Applying speech enhancement: {speech_enhance}")
        try:
            from process.multispeaker.speech_enhance import enhance_speech
            audio_path = enhance_speech(audio_path, mode=speech_enhance)
        except Exception as e:
            _log(f"Enhancement failed, using original: {e}")

    # Transcription
    _log(f"[2/4] Transcribing with {stt_model}...")
    transcript_segments = []
    if stt_model.startswith("online"):
        from process.multispeaker.stt_online import transcribe_online
        transcript_segments = transcribe_online(audio_path, stt_model)
    else:
        from process.multispeaker.stt_local import transcribe_with_faster_whisper
        transcript_segments = transcribe_with_faster_whisper(audio_path, stt_model)

    if not transcript_segments:
        _log("Không tìm thấy lời nói trong audio")
        return []

    _log(f"   Tìm thấy {len(transcript_segments)} segments")

    # Diarization
    _log("[3/4] Speaker diarization...")
    diarization_segments = []
    try:
        from process.multispeaker.diarizer import diarize_with_pyannote
        diarization_segments = diarize_with_pyannote(audio_path, num_speakers)
    except Exception as e:
        _log(f"Diarization failed: {e}, assigning all to SPEAKER_00")

    # Merge
    _log("[4/4] Merging results...")
    entries = merge_transcript_and_diarization(transcript_segments, diarization_segments)
    speakers = set(e.speaker for e in entries)
    _log(f"   Kết quả: {len(entries)} segments, {len(speakers)} speakers")

    return entries
