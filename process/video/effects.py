"""Video Effects — 40+ transitions and 14 overlay effects.

Adapted from TTS_Voice_AndyLe-001 Story Maker video effects.
"""

import os
import subprocess
import logging

LOGGER = logging.getLogger(__name__)


# ─────────────────────────── Transitions ─────────────────────────

TRANSITIONS = [
    "fade", "dissolve", "smooth", "smoothLeft", "smoothRight", "smoothUp", "smoothDown",
    "wipe", "wipeLeft", "wipeRight", "wipeUp", "wipeDown",
    "cover", "coverLeft", "coverRight", "coverUp", "coverDown",
    "reveal", "revealLeft", "revealRight", "revealUp", "revealDown",
    "circle", "circleOpen", "circleClose", "circleCrop", "rectCrop",
    "distance", "fadeBW", "fadeGrays",
    "horzClose", "horzOpen", "vertClose", "vertOpen",
    "diagBL", "diagBR", "diagTL", "diagTR",
    "hlSlice", "hrSlice", "vuSlice", "vdSlice",
    "pixelize", "radial",
]

# ─────────────────────────── Overlay Effects ─────────────────────

OVERLAY_EFFECTS = {
    "rain_light": "rain/rain_light_loop.mp4",
    "rain_heavy": "rain/rain_heavy_loop.mp4",
    "snow_light": "snow/snow_light_loop.mp4",
    "snow_heavy": "snow/snow_heavy_loop.mp4",
    "leaves_autumn": "leaves/leaves_autumn_loop.mp4",
    "dust_particles": "dust/dust_particles_loop.mp4",
    "fog_light": "fog/fog_light_loop.mp4",
    "lightning_flash": "lightning/lightning_flash_01.mp4",
    "old_film_grain": "old_film/old_film_grain_light_loop.mp4",
    "old_film_scratches": "old_film/old_film_scratches_loop.mp4",
    "old_film_dust": "old_film/old_film_dust_loop.mp4",
    "old_film_flicker": "old_film/old_film_flicker_loop.mp4",
    "warm_light_leak": "light_leak/light_leak_warm_01.mp4",
    "golden_particles": "particles/golden_particles_loop.mp4",
}

# Ken Burns effects
KEN_BURNS_EFFECTS = [
    "zoom_in", "zoom_out",
    "pan_left", "pan_right",
    "pan_up", "pan_down",
]


def get_footage_path(effect_name: str, footages_dir: str = "") -> str | None:
    """Get the full path to a footage file."""
    if not footages_dir:
        footages_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "footages"
        )

    rel_path = OVERLAY_EFFECTS.get(effect_name, "")
    if not rel_path:
        return None

    full_path = os.path.join(footages_dir, rel_path)
    return full_path if os.path.isfile(full_path) else None


def build_transition_filter(
    transition: str,
    duration: float = 1.0,
    offset: float = 0.0,
) -> str:
    """Build FFmpeg xfade filter expression for a transition."""
    if transition not in TRANSITIONS:
        transition = "fade"
    return f"xfade=transition={transition}:duration={duration}:offset={offset}"


def build_ken_burns_filter(
    effect: str,
    duration: float,
    width: int = 1920,
    height: int = 1080,
) -> str:
    """Build FFmpeg filter for Ken Burns zoom/pan effect."""
    if effect == "zoom_in":
        return (
            f"scale=w={width*2}:h={height*2},"
            f"zoompan=z='min(zoom+0.001,1.5)':d={int(duration*30)}"
            f":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s={width}x{height}"
        )
    elif effect == "zoom_out":
        return (
            f"scale=w={width*2}:h={height*2},"
            f"zoompan=z='if(lte(zoom,1.0),1.5,max(zoom-0.001,1.0))':d={int(duration*30)}"
            f":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s={width}x{height}"
        )
    elif effect == "pan_left":
        return (
            f"scale=w={int(width*1.5)}:h={height}:force_original_aspect_ratio=increase,"
            f"crop=w={width}:h={height}:x='(iw-{width})*t/{duration}':y=0"
        )
    elif effect == "pan_right":
        return (
            f"scale=w={int(width*1.5)}:h={height}:force_original_aspect_ratio=increase,"
            f"crop=w={width}:h={height}:x='(iw-{width})*(1-t/{duration})':y=0"
        )
    elif effect == "pan_up":
        return (
            f"scale=w={width}:h={int(height*1.5)}:force_original_aspect_ratio=increase,"
            f"crop=w={width}:h={height}:x=0:y='(ih-{height})*t/{duration}'"
        )
    elif effect == "pan_down":
        return (
            f"scale=w={width}:h={int(height*1.5)}:force_original_aspect_ratio=increase,"
            f"crop=w={width}:h={height}:x=0:y='(ih-{height})*(1-t/{duration})'"
        )
    return ""


def apply_overlay_effect(
    video_path: str,
    output_path: str,
    effect_name: str,
    footages_dir: str = "",
    opacity: float = 0.5,
) -> bool:
    """Apply an overlay effect to a video using FFmpeg.

    Returns True if successful.
    """
    footage_path = get_footage_path(effect_name, footages_dir)
    if not footage_path:
        LOGGER.warning(f"Footage not found: {effect_name}")
        return False

    blend_mode = "overlay" if "old_film" in effect_name else "screen"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", footage_path,
        "-filter_complex",
        f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[ov];"
        f"[0:v][ov]overlay=0:0:shortest=1[out]",
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "copy", "-shortest",
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=600)
        return True
    except Exception as e:
        LOGGER.error(f"Overlay effect failed: {e}")
        return False
