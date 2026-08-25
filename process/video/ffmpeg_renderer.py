"""FFmpeg-based video renderer — fast batch rendering with GPU encoder.

Adapted from Tool (backend/core/video_editor.py).
"""

import os
import glob
import subprocess
import re
import time
from typing import Generator


_IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
_VIDEO_EXT = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.m4v'}

_VIDEO_ENCODER_CACHE = None


def detect_video_encoder() -> str:
    """Auto-detect the best available H.264 encoder (GPU > CPU)."""
    global _VIDEO_ENCODER_CACHE
    if _VIDEO_ENCODER_CACHE is not None:
        return _VIDEO_ENCODER_CACHE

    try:
        result = subprocess.run(
            ['ffmpeg', '-encoders'],
            capture_output=True, text=True, check=True, timeout=10,
        )
        output = result.stdout + result.stderr
        if 'h264_nvenc' in output:
            _VIDEO_ENCODER_CACHE = 'h264_nvenc'
        elif 'h264_amf' in output:
            _VIDEO_ENCODER_CACHE = 'h264_amf'
        elif 'h264_qsv' in output:
            _VIDEO_ENCODER_CACHE = 'h264_qsv'
        else:
            _VIDEO_ENCODER_CACHE = 'libx264'
    except Exception:
        _VIDEO_ENCODER_CACHE = 'libx264'

    return _VIDEO_ENCODER_CACHE


def _get_media_duration(path: str) -> float:
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _leading_number(path: str) -> int:
    m = re.match(r'(\d+)', os.path.basename(path))
    return int(m.group(1)) if m else 0


def _resolution_value(quality: str) -> str:
    return {
        '720p': '1280:720',
        '1080p': '1920:1080',
        '2K': '2560:1440',
        '4K': '3840:2160',
    }.get(quality, '1920:1080')


def render_video_batch(
    audio_folder: str,
    output_folder: str,
    batch_start: int,
    batch_end: int,
    bg_media_folder: str = '',
    transition: str = 'crossfade',
    fps: int = 30,
    quality: str = '1080p',
    duration_mode: str = 'chapters',
    max_hours: float = 0,
    intro_path: str = '',
    outro_path: str = '',
    watermark_text: str = '',
    speed: str = 'balanced',
    stop_event=None,
) -> Generator[str, None, None]:
    """Render a batch of chapters into a single video using FFmpeg.

    Yields progress messages.
    """
    os.makedirs(output_folder, exist_ok=True)
    resolution = _resolution_value(quality)
    size = resolution.replace(':', 'x')

    encoder = detect_video_encoder()
    encoder_names = {
        'libx264': 'CPU (libx264)',
        'h264_nvenc': 'GPU NVIDIA (NVENC)',
        'h264_amf': 'GPU AMD (AMF)',
        'h264_qsv': 'GPU Intel (QSV)',
    }
    yield f"Encoder: {encoder_names.get(encoder, encoder)}"

    # Scan audio
    all_files = sorted(glob.glob(os.path.join(audio_folder, '*.mp3')), key=_leading_number)
    audio_files = [f for f in all_files if batch_start <= _leading_number(f) <= batch_end]

    if not audio_files:
        yield f"[LỖI] Không tìm thấy audio từ chap {batch_start:03d} đến {batch_end:03d}"
        return
    yield f"Tìm thấy {len(audio_files)} file audio"

    if stop_event and stop_event.is_set():
        return

    # Calculate total duration
    total_dur = sum(_get_media_duration(f) for f in audio_files)
    yield f"Tổng thời lượng: {total_dur:.1f}s ({total_dur / 60:.1f} phút)"

    # Build audio concat file
    concat_path = os.path.join(output_folder, f'_concat_{batch_start:03d}.txt')
    with open(concat_path, 'w', encoding='utf-8') as f:
        for af in audio_files:
            f.write(f"file '{os.path.abspath(af).replace(os.sep, '/')}'\n")

    out_name = f"{batch_start:03d}-{batch_end:03d}.mp4"
    out_path = os.path.join(output_folder, out_name)

    # Build FFmpeg command
    cmd = ['ffmpeg', '-y']

    # Background media
    media_folder = bg_media_folder
    bg_files = []
    if media_folder and os.path.isdir(media_folder):
        bg_files = sorted([
            os.path.join(media_folder, f)
            for f in os.listdir(media_folder)
            if os.path.splitext(f)[1].lower() in _IMAGE_EXT | _VIDEO_EXT
        ])

    if bg_files:
        img_dur = total_dur / min(len(bg_files), 50) if total_dur > 0 else 8.0
        for img in bg_files[:50]:
            cmd += ['-loop', '1', '-t', str(img_dur), '-i', img]
        num_media = min(len(bg_files), 50)
    else:
        cmd += ['-f', 'lavfi', '-i', f'color=c=#1a1a2e:s={size}']
        num_media = 1

    # Audio
    if len(audio_files) == 1:
        cmd += ['-i', audio_files[0]]
    else:
        cmd += ['-f', 'concat', '-safe', '0', '-i', concat_path]

    audio_idx = num_media

    preset = 'ultrafast' if speed == 'fast' else 'medium'

    # Simple render: video + audio
    cmd += [
        '-map', '0:v' if num_media == 1 else f'0:v',
        '-map', f'{audio_idx}:a',
        '-c:v', encoder,
    ]

    if encoder == 'libx264':
        cmd += ['-preset', preset, '-crf', '23']
    elif encoder == 'h264_nvenc':
        cmd += ['-preset', 'p4' if preset == 'ultrafast' else 'p7', '-cq', '23']

    cmd += [
        '-r', str(fps),
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        out_path,
    ]

    yield f"Output: {out_name}"
    yield "Running ffmpeg..."

    if stop_event and stop_event.is_set():
        _cleanup(concat_path)
        return

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        while True:
            if stop_event and stop_event.is_set():
                process.terminate()
                yield "Render bị hủy"
                break
            line = process.stderr.readline()
            if not line:
                break
            match = re.search(r'time=(\d+):(\d+):(\d+)', line)
            if match and total_dur > 0:
                h, m, s = map(int, match.groups())
                curr = h * 3600 + m * 60 + s
                pct = min(int(curr / total_dur * 100), 100)
                yield f"[PROGRESS] {pct}"

        process.wait()
        if process.returncode == 0:
            yield "[PROGRESS] 100"
            yield f"Done: {out_name}"
        else:
            yield f"FFmpeg error: code {process.returncode}"
    finally:
        if process.poll() is None:
            process.kill()
        _cleanup(concat_path)


def _cleanup(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
