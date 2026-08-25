"""Voice Manager — scanning, cloning, and managing voice samples.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 447-576, 1221-1274, 1897-1945).
"""

import os
import re
import json
import subprocess
import logging
from dataclasses import dataclass, field
from pathlib import Path

LOGGER = logging.getLogger(__name__)

SUPPORTED_VOICE_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".webm"}

# Default voices directory
_DEFAULT_VOICES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "voices")


@dataclass
class VoiceInfo:
    """Information about a single voice sample."""
    id: str
    name: str
    path: str
    gender: str = ""
    language: str = ""
    location: str = ""
    style: str = ""
    duration: float = 0.0
    transcript: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "language": self.language,
            "location": self.location,
            "style": self.style,
            "duration": self.duration,
        }


def _audio_duration(path: str) -> float:
    """Get audio file duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _read_voice_metadata(audio_path: str) -> dict:
    """Read voice metadata from JSON or TXT sidecar file."""
    base = os.path.splitext(audio_path)[0]

    # Try JSON sidecar
    json_path = base + ".json"
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "items" in data and data["items"]:
                item = data["items"][0]
                return {
                    "name": item.get("Voice_name", ""),
                    "transcript": item.get("Transcript", ""),
                    "gender": item.get("Gender", ""),
                    "language": item.get("Language", ""),
                    "location": item.get("Location", ""),
                    "style": item.get("Style", ""),
                }
        except Exception:
            pass

    # Try TXT sidecar
    txt_path = base + ".txt"
    if os.path.isfile(txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                return {"transcript": f.read().strip()}
        except Exception:
            pass

    return {}


def voice_search_dirs(extra_dirs: list[str] | None = None) -> list[str]:
    """Return list of directories to scan for voices."""
    dirs = [_DEFAULT_VOICES_DIR]

    # Also scan APPDATA voices
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        appdata_voices = os.path.join(appdata, "TTS_Voice_Clone_Andy", "voices")
        if os.path.isdir(appdata_voices) and appdata_voices not in dirs:
            dirs.append(appdata_voices)

    if extra_dirs:
        dirs.extend(extra_dirs)

    return [d for d in dirs if os.path.isdir(d)]


def scan_voices(extra_dirs: list[str] | None = None) -> list[VoiceInfo]:
    """Scan all voice directories and return voice info list."""
    voices = []
    seen_ids = set()

    for dir_path in voice_search_dirs(extra_dirs):
        for entry in os.listdir(dir_path):
            ext = os.path.splitext(entry)[1].lower()
            if ext not in SUPPORTED_VOICE_EXTS:
                continue

            full_path = os.path.join(dir_path, entry)
            stem = os.path.splitext(entry)[0]
            voice_id = stem.lower().replace(" ", "_")

            if voice_id in seen_ids:
                continue
            seen_ids.add(voice_id)

            meta = _read_voice_metadata(full_path)
            name = meta.get("name", "") or stem.replace("_", " ").title()

            voices.append(VoiceInfo(
                id=voice_id,
                name=name,
                path=full_path,
                gender=meta.get("gender", ""),
                language=meta.get("language", ""),
                location=meta.get("location", ""),
                style=meta.get("style", ""),
                duration=_audio_duration(full_path),
                transcript=meta.get("transcript", ""),
            ))

    voices.sort(key=lambda v: v.name)
    return voices


def find_voice(voice_id: str, extra_dirs: list[str] | None = None) -> VoiceInfo | None:
    """Find a voice by its ID."""
    for v in scan_voices(extra_dirs):
        if v.id == voice_id or v.name == voice_id:
            return v
    return None


# ─────────────────────────── Voice Cloning ───────────────────────

def sanitize_stem(name: str) -> str:
    """Clean a string for use as a filename stem."""
    clean = re.sub(r'[\\/:*?"<>|]', '_', name)
    clean = re.sub(r'\s+', '_', clean).strip('_')
    return clean[:80] if clean else "voice"


def _ffmpeg_path() -> str:
    """Find ffmpeg in the system."""
    import shutil
    path = shutil.which("ffmpeg")
    return path or "ffmpeg"


def convert_or_copy_voice_audio(source_path: str, dest_dir: str, stem: str) -> str:
    """Convert audio to WAV or copy if already WAV."""
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(source_path)[1].lower()
    dest_path = os.path.join(dest_dir, f"{stem}.wav")

    if ext == ".wav":
        import shutil
        shutil.copy2(source_path, dest_path)
    else:
        try:
            subprocess.run([
                _ffmpeg_path(), "-y", "-i", source_path,
                "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
                dest_path,
            ], capture_output=True, check=True, timeout=60)
        except Exception as e:
            LOGGER.error(f"FFmpeg convert error: {e}")
            raise RuntimeError(f"Không thể chuyển audio mẫu sang WAV: {e}") from e

    return dest_path


def write_voice_json(dest_dir: str, stem: str, metadata: dict):
    """Write voice metadata JSON sidecar file."""
    json_path = os.path.join(dest_dir, f"{stem}.json")
    data = {
        "items": [{
            "Voice_name": metadata.get("name", stem),
            "Transcript": metadata.get("transcript", ""),
            "Gender": metadata.get("gender", ""),
            "Language": metadata.get("language", "Vietnamese"),
            "Location": metadata.get("location", ""),
            "Style": metadata.get("style", ""),
        }]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clone_voice(
    source_audio_path: str,
    name: str,
    transcript: str,
    gender: str = "",
    language: str = "Vietnamese",
    location: str = "",
    style: str = "",
    dest_dir: str | None = None,
) -> VoiceInfo:
    """Clone a voice: convert audio + save metadata.

    Returns:
        VoiceInfo for the new voice.
    """
    if dest_dir is None:
        dest_dir = _DEFAULT_VOICES_DIR

    stem = sanitize_stem(name)
    wav_path = convert_or_copy_voice_audio(source_audio_path, dest_dir, stem)
    write_voice_json(dest_dir, stem, {
        "name": name,
        "transcript": transcript,
        "gender": gender,
        "language": language,
        "location": location,
        "style": style,
    })

    return VoiceInfo(
        id=stem.lower(),
        name=name,
        path=wav_path,
        gender=gender,
        language=language,
        location=location,
        style=style,
        duration=_audio_duration(wav_path),
        transcript=transcript,
    )
