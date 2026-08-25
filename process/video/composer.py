"""Video Composer — MoviePy-based scene composition.

Composes a video from scenes (images/clips + audio + subtitles + effects).
"""

import os
import subprocess
import logging
from typing import Generator

LOGGER = logging.getLogger(__name__)


def compose_story_video(
    scenes: list,
    audio_path: str,
    output_path: str,
    transition: str = "fade",
    overlay_effect: str = "",
    background_sound: str = "",
    remove_video_sounds: bool = False,
    resolution: str = "1080p",
    fps: int = 30,
    footages_dir: str = "",
    stop_event=None,
) -> Generator[str, None, None]:
    """Compose a story video from scenes using FFmpeg.

    Args:
        scenes: List of Scene objects with narration and media_path.
        audio_path: Path to the narration audio file.
        output_path: Output video path.
        transition: Transition type between scenes.
        overlay_effect: Optional overlay effect name.
        background_sound: Optional background music path.
        remove_video_sounds: Remove original audio from video clips.
        resolution: Video resolution (720p, 1080p, 2K, 4K).
        fps: Frames per second.
        footages_dir: Directory containing footage clips.
        stop_event: Threading event to stop.

    Yields:
        Progress messages.
    """
    res_map = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "2K": (2560, 1440),
        "4K": (3840, 2160),
    }
    width, height = res_map.get(resolution, (1920, 1080))
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Validate inputs
    valid_scenes = [s for s in scenes if s.media_path and os.path.isfile(s.media_path)]
    if not valid_scenes:
        yield "Không có scene nào có media file. Sẽ dùng nền đen."
        # Create black background video with audio
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x1a1a2e:s={width}x{height}",
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "medium",
            "-r", str(fps), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=600)
            yield f"Done: {output_path}"
        except Exception as e:
            yield f"Error: {e}"
        return

    yield f"Composing {len(valid_scenes)} scenes at {resolution}..."

    # Calculate duration per scene based on audio length
    audio_duration = _get_duration(audio_path)
    if audio_duration <= 0:
        yield "Không đọc được thời lượng audio"
        return

    scene_duration = audio_duration / len(valid_scenes)
    yield f"Audio: {audio_duration:.1f}s, mỗi scene: {scene_duration:.1f}s"

    if stop_event and stop_event.is_set():
        return

    # Build FFmpeg concat file
    import tempfile
    concat_path = os.path.join(tempfile.gettempdir(), "story_concat.txt")

    with open(concat_path, "w", encoding="utf-8") as f:
        for scene in valid_scenes:
            ext = os.path.splitext(scene.media_path)[1].lower()
            if ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                # Image: loop for scene_duration
                f.write(f"file '{scene.media_path.replace(os.sep, '/')}'\n")
                f.write(f"duration {scene_duration:.2f}\n")
            else:
                # Video clip
                f.write(f"file '{scene.media_path.replace(os.sep, '/')}'\n")

    # Build FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_path,
        "-i", audio_path,
    ]

    # Add background sound if specified
    filter_complex = []
    if background_sound and os.path.isfile(background_sound):
        cmd += ["-i", background_sound]
        filter_complex.append("[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=3[aout]")
        audio_map = "[aout]"
    else:
        audio_map = "1:a"

    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-r", str(fps), "-pix_fmt", "yuv420p",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v",
        "-map", audio_map,
        "-shortest",
        output_path,
    ]

    if filter_complex:
        cmd.insert(-7, "-filter_complex")
        cmd.insert(-7, ";".join(filter_complex))

    yield "Running FFmpeg..."
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if process.returncode == 0:
            yield f"Done: {output_path}"
        else:
            yield f"FFmpeg error: {process.stderr[:300]}"
    except Exception as e:
        yield f"Error: {e}"
    finally:
        try:
            os.remove(concat_path)
        except OSError:
            pass

    # Apply overlay effect if specified
    if overlay_effect and os.path.isfile(output_path):
        yield f"Applying overlay: {overlay_effect}..."
        from process.video.effects import apply_overlay_effect
        tmp_output = output_path.replace(".mp4", "_overlay.mp4")
        if apply_overlay_effect(output_path, tmp_output, overlay_effect, footages_dir):
            os.replace(tmp_output, output_path)
            yield f"Overlay applied: {overlay_effect}"
        else:
            yield f"Overlay failed, keeping original"


def _get_duration(path: str) -> float:
    """Get media file duration in seconds."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return 0.0
