"""Model Manager — Download, cache, and manage OmniVoice model.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 120-444).
"""

import os
import sys
import zipfile
import logging
import threading
import hashlib
from pathlib import Path
from typing import Callable

LOGGER = logging.getLogger(__name__)

# ─────────────────────────── Constants ───────────────────────────

MODEL_REPO_ID = "k2-fsa/OmniVoice"
MODEL_DOWNLOAD_URL = "https://huggingface.co/laichaoyi/MixupModels/resolve/main/models--k2-fsa--OmniVoice.zip"
MODEL_ZIP_NAME = "models--k2-fsa--OmniVoice.zip"
MODEL_FOLDER_NAME = "models--k2-fsa--OmniVoice"
SAMPLE_RATE = 24000

# Project local models directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_MODEL_DIR = os.path.join(PROJECT_ROOT, "data", "models", MODEL_FOLDER_NAME)

# %APPDATA%/TTS_Voice_Clone_Andy/
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "TTS_Voice_Clone_Andy")
LOCAL_MODEL_ZIP = os.path.join(APPDATA_DIR, MODEL_ZIP_NAME)

# Use project local model dir if exists, else fall back to APPDATA
if os.path.isdir(PROJECT_MODEL_DIR) and (
    os.path.isfile(os.path.join(PROJECT_MODEL_DIR, "config.json")) or
    os.path.isfile(os.path.join(PROJECT_MODEL_DIR, "model.safetensors"))
):
    LOCAL_MODEL_DIR = PROJECT_MODEL_DIR
else:
    LOCAL_MODEL_DIR = os.path.join(APPDATA_DIR, MODEL_FOLDER_NAME)

# ─────────────────────────── Status ──────────────────────────────

_status_lock = threading.Lock()
MODEL_STATUS = {
    "phase": "idle",       # idle, downloading, extracting, loading, ready, error
    "progress": 0,         # 0-100
    "message": "",
    "model_path": "",
}


def set_model_status(phase: str, progress: int = 0, message: str = ""):
    with _status_lock:
        MODEL_STATUS["phase"] = phase
        MODEL_STATUS["progress"] = progress
        MODEL_STATUS["message"] = message


def get_model_status() -> dict:
    with _status_lock:
        return dict(MODEL_STATUS)


# ─────────────────────────── Path ────────────────────────────────

def _find_extracted_model_dir(base_dir: str) -> str | None:
    """Find the actual model directory (may be nested inside extracted zip)."""
    # Check direct: base_dir/config.json
    if os.path.isfile(os.path.join(base_dir, "config.json")):
        return base_dir

    # Check nested: base_dir/snapshots/*/config.json
    snapshots = os.path.join(base_dir, "snapshots")
    if os.path.isdir(snapshots):
        for d in os.listdir(snapshots):
            candidate = os.path.join(snapshots, d)
            if os.path.isfile(os.path.join(candidate, "config.json")):
                return candidate

    # Check one level deep
    for entry in os.listdir(base_dir):
        candidate = os.path.join(base_dir, entry)
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "config.json")):
            return candidate

    return None


def model_folder_ready() -> bool:
    """Check if model is already extracted and ready."""
    if not os.path.isdir(LOCAL_MODEL_DIR):
        return False
    model_dir = _find_extracted_model_dir(LOCAL_MODEL_DIR)
    if not model_dir:
        return False
    required = (
        os.path.join(model_dir, "config.json"),
        os.path.join(model_dir, "model.safetensors"),
        os.path.join(model_dir, "tokenizer.json"),
        os.path.join(model_dir, "audio_tokenizer", "config.json"),
        os.path.join(model_dir, "audio_tokenizer", "model.safetensors"),
    )
    return all(os.path.isfile(path) and os.path.getsize(path) > 0 for path in required)


def _safe_extract(zf: zipfile.ZipFile, target_dir: str, member: str):
    """Extract one ZIP member without allowing writes outside target_dir."""
    target_root = os.path.realpath(target_dir)
    destination = os.path.realpath(os.path.join(target_dir, member))
    if os.path.commonpath([target_root, destination]) != target_root:
        raise ValueError(f"Unsafe ZIP member: {member}")
    zf.extract(member, target_dir)


def resolve_local_model_path() -> str | None:
    """Return the resolved path to the model directory, or None."""
    if not os.path.isdir(LOCAL_MODEL_DIR):
        return None
    return _find_extracted_model_dir(LOCAL_MODEL_DIR)


# ─────────────────────────── Download ────────────────────────────

def ensure_model_downloaded(
    progress_callback: Callable[[str, int, str], None] | None = None,
) -> str | None:
    """Download and extract the OmniVoice model if not already present.

    Args:
        progress_callback: Optional callback(phase, progress, message).

    Returns:
        Path to the model directory, or None on failure.
    """
    def _report(phase, pct, msg):
        set_model_status(phase, pct, msg)
        if progress_callback:
            progress_callback(phase, pct, msg)

    # Check if already ready
    if model_folder_ready():
        path = resolve_local_model_path()
        MODEL_STATUS["model_path"] = path or ""
        _report("ready", 100, "Model đã sẵn sàng")
        return path

    offline = any(
        os.environ.get(key, "").strip().lower() in {"1", "true", "yes"}
        for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")
    )
    if offline:
        _report("error", 0, "Đang ở chế độ offline và model chưa có trên máy")
        return None

    os.makedirs(APPDATA_DIR, exist_ok=True)

    # Download if zip not present
    if not os.path.isfile(LOCAL_MODEL_ZIP):
        _report("downloading", 0, "Đang tải model OmniVoice (~2-3 GB)...")
        try:
            import requests
            resp = requests.get(MODEL_DOWNLOAD_URL, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(LOCAL_MODEL_ZIP, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = min(int(downloaded / total * 100), 99)
                        _report("downloading", pct, f"Đang tải... {downloaded // (1024*1024)} MB / {total // (1024*1024)} MB")
            _report("downloading", 100, "Tải xong!")
        except Exception as e:
            _report("error", 0, f"Lỗi tải model: {e}")
            LOGGER.error(f"Model download error: {e}")
            try:
                os.remove(LOCAL_MODEL_ZIP)
            except OSError:
                pass
            return None

    # Extract zip
    if not model_folder_ready():
        _report("extracting", 0, "Đang giải nén model...")
        try:
            os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
            with zipfile.ZipFile(LOCAL_MODEL_ZIP, "r") as zf:
                members = zf.namelist()
                total = len(members)
                for i, member in enumerate(members):
                    _safe_extract(zf, LOCAL_MODEL_DIR, member)
                    if i % 50 == 0 or i == total - 1:
                        pct = min(int((i + 1) / total * 100), 99)
                        _report("extracting", pct, f"Giải nén... {i + 1}/{total}")
            _report("extracting", 100, "Giải nén xong!")
        except Exception as e:
            _report("error", 0, f"Lỗi giải nén: {e}")
            LOGGER.error(f"Model extract error: {e}")
            return None

    path = resolve_local_model_path()
    if path:
        MODEL_STATUS["model_path"] = path
        _report("ready", 100, "Model đã sẵn sàng")
    else:
        _report("error", 0, "Không tìm thấy config.json trong model")
    return path


# ─────────────────────────── Offline Mode ────────────────────────

def set_offline_mode():
    """Set HuggingFace offline environment variables."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"


def hf_online_env_guard():
    """Temporarily disable offline mode (returns saved state)."""
    saved = {}
    for key in ["HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"]:
        saved[key] = os.environ.pop(key, None)
    return saved


def restore_env(saved: dict):
    """Restore environment variables from saved state."""
    for key, val in saved.items():
        if val is not None:
            os.environ[key] = val
        elif key in os.environ:
            del os.environ[key]
