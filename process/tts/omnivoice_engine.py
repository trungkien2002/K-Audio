"""OmniVoice TTS engine — nhúng model OmniVoice trực tiếp.

Adapted from TTS_Voice_AndyLe-001 (main.py lines 596-780, 1111-1397, 1685-1770).
Model: k2-fsa/OmniVoice (Xiaomi Corp), 24kHz, GPU/CPU.
"""

import os
import re
import time
import logging
import threading
import numpy as np
from typing import Any, Generator
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 24000
MAX_CHUNK_CHARS = 420
SUPPORTED_OUTPUT_FORMATS = {"wav", "mp3", "flac", "ogg"}

_runtime_lock = threading.Lock()
_runtime = None  # Lazy singleton


@dataclass
class OmniVoiceConfig:
    """Configuration for OmniVoice generation."""
    voice_id: str = ""
    voice_path: str = ""
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    num_steps: int = 32
    guidance_scale: float = 3.0
    temperature: float = 0.1
    postprocess: bool = True
    output_format: str = "wav"  # wav, mp3, flac, ogg
    device: str = "auto"  # auto, cpu, cuda


class TTSRuntime:
    """Runtime wrapper for the OmniVoice model."""

    def __init__(self):
        self.model = None
        self.device = None
        self._loaded = False

    def resolve_device(self, preferred: str = "auto"):
        """Resolve the requested device, falling back safely when needed."""
        try:
            import torch
            if preferred == "cpu":
                self.device = "cpu"
            elif preferred == "cuda" and torch.cuda.is_available():
                self.device = "cuda"
            elif preferred == "cuda":
                self.device = "cpu"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        except ImportError:
            self.device = "cpu"
        return self.device

    def load_model(self, model_path: str, preferred_device: str = "auto"):
        """Load the OmniVoice model from local path."""
        if self._loaded and self.model is not None:
            return

        self.resolve_device(preferred_device)
        LOGGER.info(f"Loading OmniVoice on {self.device}...")

        # Auto-discover omnivoice package from TTS_Voice_AndyLe-001
        self._ensure_omnivoice_importable()

        try:
            import torch
            from omnivoice import OmniVoice as OmniVoiceModel

            # Determine dtype based on device
            dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
            device_map = "cuda:0" if self.device == "cuda" else "cpu"

            self.model = OmniVoiceModel.from_pretrained(
                str(model_path),
                device_map=device_map,
                dtype=dtype,
            )
            self._loaded = True
            LOGGER.info("OmniVoice model loaded successfully")
        except ImportError as e:
            LOGGER.error(f"OmniVoice package not found: {e}")
            raise RuntimeError(
                "OmniVoice package không tìm thấy.\n"
                "Đảm bảo thư mục TTS_Voice_AndyLe-001 nằm cạnh project,\n"
                "hoặc cài đặt omnivoice: pip install omnivoice"
            ) from e
        except Exception as e:
            LOGGER.error(f"Failed to load model: {e}")
            raise

    @staticmethod
    def _ensure_omnivoice_importable():
        """Add local omnivoice package to sys.path if not already importable."""
        import sys

        # Search in local project directory first
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        local_omnivoice = os.path.join(project_root, "omnivoice")
        if os.path.isdir(local_omnivoice):
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
                LOGGER.info(f"Added local project path for omnivoice: {project_root}")
            return

        # Check if already importable globally
        try:
            import omnivoice  # noqa: F401
            return
        except ImportError:
            pass

        LOGGER.error("Could not find omnivoice package locally in the project directory")

    def get_voice_prompt(self, voice_path: str, transcript: str = "") -> Any:
        """Load a voice sample as conditioning prompt using model API."""
        if not voice_path or not os.path.isfile(voice_path):
            return None
        if self.model is None:
            return None
        try:
            LOGGER.info(f"Creating voice clone prompt for: {voice_path}")
            # Ensure path is absolute string
            prompt = self.model.create_voice_clone_prompt(
                ref_audio=str(voice_path),
                ref_text=transcript,
                preprocess_prompt=False,
            )
            return prompt
        except Exception as e:
            LOGGER.warning(f"Failed to create voice clone prompt: {e}")
            return None

    def generate_chunk(
        self,
        text: str,
        voice_prompt=None,
        speed: float = 1.0,
        num_step: int = 32,
        guidance_scale: float = 3.0,
        class_temperature: float = 0.1,
        postprocess_output: bool = True,
    ):
        """Generate audio for a single text chunk."""
        if self.model is None:
            raise RuntimeError("Model not loaded")

        import torch
        with torch.no_grad():
            kwargs = {
                "text": text,
                "speed": float(speed),
                "num_step": int(num_step),
                "guidance_scale": float(guidance_scale),
                "class_temperature": float(class_temperature),
                "postprocess_output": bool(postprocess_output),
            }
            if voice_prompt is not None:
                kwargs["voice_clone_prompt"] = voice_prompt

            output = self.model.generate(**kwargs)

        return output

    def get_voice_prompt_legacy(self, voice_path: str) -> "torch.Tensor | None":
        """Fallback for loading a voice sample as raw tensor if needed."""
        if not voice_path or not os.path.isfile(voice_path):
            return None
        try:
            import torch
            import soundfile as sf
            audio, sr = sf.read(voice_path)
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            audio = torch.FloatTensor(audio).unsqueeze(0).to(self.device)
            return audio
        except Exception as e:
            LOGGER.warning(f"Failed to load voice prompt: {e}")
            return None


def _get_runtime() -> TTSRuntime:
    """Get or create the singleton runtime."""
    global _runtime
    if _runtime is None:
        _runtime = TTSRuntime()
    return _runtime


# ─────────────────────────── Text Splitting ──────────────────────

def split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split text into chunks at sentence/comma boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = ""

    # Split at sentence boundaries first
    sentences = re.split(r'(?<=[.!?。！？])\s+', text)

    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = (current + " " + sent).strip()
        else:
            if current:
                chunks.append(current)
            # If single sentence is too long, split at commas
            if len(sent) > max_chars:
                parts = re.split(r'(?<=[,，;；])\s*', sent)
                sub_current = ""
                for part in parts:
                    if len(sub_current) + len(part) + 1 <= max_chars:
                        sub_current = (sub_current + " " + part).strip()
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = part
                current = sub_current
            else:
                current = sent

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


# ─────────────────────────── Audio Processing ────────────────────

def normalize_generated_audio(audio_tensor) -> np.ndarray:
    """Normalize the output tensor to numpy array."""
    import torch
    if isinstance(audio_tensor, torch.Tensor):
        audio = audio_tensor.cpu().numpy()
    elif isinstance(audio_tensor, np.ndarray):
        audio = audio_tensor
    else:
        audio = np.array(audio_tensor)

    if audio.ndim > 1:
        audio = audio.squeeze()
    if audio.ndim > 1:
        audio = audio[0]

    # Normalize to [-1, 1]
    max_val = np.abs(audio).max()
    if max_val > 0:
        audio = audio / max_val * 0.95

    return audio.astype(np.float32)


def trim_silence(audio: np.ndarray, rate: int = SAMPLE_RATE, threshold_db: float = -35.0) -> np.ndarray:
    """Cắt bỏ phần im lặng ở đầu và cuối của mảng audio để khớp phụ đề."""
    if audio.size == 0:
        return audio
        
    # Chuyển đổi dB sang biên độ amplitude
    threshold = 10 ** (threshold_db / 20.0)
    abs_audio = np.abs(audio)
    indices = np.where(abs_audio > threshold)[0]
    
    if indices.size == 0:
        return np.zeros(int(0.1 * rate), dtype=np.float32)
        
    start_idx = indices[0]
    end_idx = indices[-1]
    
    # Đệm thêm 50ms ở đầu và cuối
    pad = int(0.05 * rate)
    start_idx = max(0, start_idx - pad)
    end_idx = min(audio.size, end_idx + pad)
    
    return audio[start_idx:end_idx]


def concat_wavs(audio_parts: list[np.ndarray], silence_between: float = 0.0) -> np.ndarray:
    """Concatenate multiple audio arrays with optional silence between."""
    if not audio_parts:
        return np.array([], dtype=np.float32)
    if len(audio_parts) == 1:
        return audio_parts[0]

    result = []
    silence_samples = int(silence_between * SAMPLE_RATE) if silence_between > 0 else 0
    silence = np.zeros(silence_samples, dtype=np.float32) if silence_samples > 0 else None

    for i, part in enumerate(audio_parts):
        result.append(part)
        if silence is not None and i < len(audio_parts) - 1:
            result.append(silence)

    return np.concatenate(result)


def save_output_audio(
    audio: np.ndarray,
    output_path: str,
    output_format: str = "wav",
    sample_rate: int = SAMPLE_RATE,
):
    """Save audio to file in the specified format."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if output_format == "wav":
        import soundfile as sf
        sf.write(output_path, audio, sample_rate, subtype="PCM_16")

    elif output_format == "mp3":
        # Save temp WAV then convert with ffmpeg
        import tempfile
        import soundfile as sf
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            sf.write(tmp_path, audio, sample_rate, subtype="PCM_16")
            subprocess.run([
                "ffmpeg", "-y", "-i", tmp_path,
                "-codec:a", "libmp3lame", "-b:a", "192k",
                output_path,
            ], capture_output=True, check=True, timeout=60)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    elif output_format in ("flac", "ogg"):
        import soundfile as sf
        fmt_map = {"flac": "FLAC", "ogg": "OGG"}
        subtype_map = {"flac": "PCM_16", "ogg": "VORBIS"}
        sf.write(output_path, audio, sample_rate,
                 format=fmt_map[output_format],
                 subtype=subtype_map[output_format])
    else:
        raise ValueError(f"Unsupported format: {output_format}")


# ─────────────────────────── Main TTS Function ───────────────────

def tts_omnivoice(
    text: str,
    output_path: str,
    config: OmniVoiceConfig | None = None,
    stop_event=None,
    srt_path: str = None,
) -> Generator[str, None, None]:
    """Generate audio using embedded OmniVoice model, with optional SRT subtitle generation.

    Yields progress messages.
    """
    if config is None:
        config = OmniVoiceConfig()

    # Step 1: Ensure model is downloaded and loaded
    yield "[OmniVoice] Kiểm tra model..."
    from process.tts.model_manager import ensure_model_downloaded, get_model_status, set_model_status

    model_path = ensure_model_downloaded(
        progress_callback=lambda phase, pct, msg: None
    )
    if not model_path:
        status = get_model_status()
        yield f"[OmniVoice] Lỗi: {status.get('message', 'Không tìm thấy model')}"
        return

    yield "[OmniVoice] Đang tải model..."
    runtime = _get_runtime()
    try:
        set_model_status("loading", 100, "Đang nạp model vào bộ nhớ...")
        with _runtime_lock:
            runtime.load_model(model_path, config.device)
        set_model_status("ready", 100, f"Model đã sẵn sàng trên {runtime.device}")
    except Exception as e:
        set_model_status("error", 0, f"Lỗi nạp model: {e}")
        yield f"[OmniVoice] Lỗi load model: {e}"
        return

    yield f"[OmniVoice] Model loaded on {runtime.device}"

    if stop_event and stop_event.is_set():
        return

    # Step 2: Load voice prompt if specified
    voice_prompt = None
    if config.voice_path and os.path.isfile(config.voice_path):
        yield f"[OmniVoice] Loading voice: {os.path.basename(config.voice_path)}"
        from process.tts.voice_manager import _read_voice_metadata
        meta = _read_voice_metadata(config.voice_path)
        transcript = meta.get("transcript", "")
        voice_prompt = runtime.get_voice_prompt(config.voice_path, transcript)
    elif config.voice_id:
        from process.tts.voice_manager import find_voice
        voice = find_voice(config.voice_id)
        if voice:
            yield f"[OmniVoice] Loading voice: {voice.name}"
            voice_prompt = runtime.get_voice_prompt(voice.path, voice.transcript)

    # Step 3: Apply text preprocessing
    # Clean garbage line separators like ===, ---, -o0o-
    try:
        import re
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            s_line = line.strip()
            # Skip if only symbols (at least 2 chars)
            if re.match(r'^[-=\*_~#\.\s\+\/]{2,}$', s_line):
                continue
            # Skip common -o0o-, -O0O-, -oo- separators
            if re.match(r'^[-–—]*\s*[oO0o]*\s*[-–—]+$', s_line):
                continue
            cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
    except Exception:
        pass

    from process.tts.pronunciation import apply_dictionary_to_text
    from process.tts.break_tags import strip_or_convert_audio_tags, build_generation_plan
    from process.tts.punctuation import add_text_with_punctuation

    try:
        text = apply_dictionary_to_text(text)
    except Exception:
        pass

    try:
        text = strip_or_convert_audio_tags(text)
    except Exception:
        pass

    # Step 4: Build generation plan (chunks + breaks)
    try:
        plan = build_generation_plan(text)
    except Exception:
        plan = [{"type": "text", "content": chunk} for chunk in split_text(text)]

    if not plan:
        yield "[OmniVoice] Không có nội dung để sinh audio"
        return

    # Step 5: Generate audio chunks
    audio_parts = []
    total_items = len(plan)

    subtitles = []
    current_time = 0.0

    for i, item in enumerate(plan):
        if stop_event and stop_event.is_set():
            yield "[OmniVoice] Đã hủy"
            return

        if item.get("type") == "silence":
            seconds = item.get("seconds", 0.5)
            silence = np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)
            audio_parts.append(silence)
            yield f"[OmniVoice] Break: {seconds}s"
            
            # Cộng dồn timeline cho phụ đề tiếp theo
            current_time += seconds
            continue

        chunk_text = item.get("content", "").strip()
        if not chunk_text:
            continue

        yield f"[OmniVoice] Chunk {i + 1}/{total_items}: {chunk_text[:50]}..."

        max_retries = 3
        success = False
        for attempt in range(max_retries):
            if stop_event and stop_event.is_set():
                return
            try:
                raw_audio = runtime.generate_chunk(
                    text=chunk_text,
                    voice_prompt=voice_prompt,
                    speed=config.speed,
                    num_step=config.num_steps,
                    guidance_scale=config.guidance_scale,
                    class_temperature=config.temperature,
                    postprocess_output=config.postprocess,
                )
                audio = normalize_generated_audio(raw_audio)
                audio = trim_silence(audio, SAMPLE_RATE)

                # Apply audio controls (pitch + volume)
                if config.pitch != 1.0 or config.volume != 1.0:
                    from process.tts.audio_controls import apply_audio_controls
                    audio = apply_audio_controls(audio, SAMPLE_RATE, config.pitch, config.volume)

                audio_parts.append(audio)
                success = True
                
                # Tính phụ đề cho chunk chữ này
                if srt_path:
                    from process.tts.srt_generator import split_into_subtitles
                    duration = len(audio) / SAMPLE_RATE
                    sub_phrases = split_into_subtitles(chunk_text, max_words=10)
                    if sub_phrases:
                        total_chars = sum(len(p) for p in sub_phrases)
                        p_offset = 0.0
                        for p in sub_phrases:
                            p_len = len(p)
                            p_dur = duration * (p_len / total_chars)
                            subtitles.append({
                                "start": current_time + p_offset,
                                "end": current_time + p_offset + p_dur,
                                "text": p
                            })
                            p_offset += p_dur
                    current_time += duration
                    
                break
            except Exception as e:
                yield f"[OmniVoice] Retry {attempt + 1}/{max_retries}: {e}"
                time.sleep(2 * (attempt + 1))

        if not success:
            yield f"[OmniVoice] Bỏ qua chunk {i + 1} sau {max_retries} lần thử"
            # Cố gắng duy trì timeline
            if srt_path:
                from process.tts.srt_generator import split_into_subtitles
                sub_phrases = split_into_subtitles(chunk_text, max_words=10)
                if sub_phrases:
                    for p in sub_phrases:
                        subtitles.append({
                            "start": current_time,
                            "end": current_time + 1.0, # Giả lập 1 giây
                            "text": p
                        })
                        current_time += 1.0

    if not audio_parts:
        yield "[OmniVoice] Không sinh được audio nào"
        return

    # Step 6: Concat and save
    yield "[OmniVoice] Ghép audio..."
    final_audio = concat_wavs(audio_parts)

    output_format = config.output_format
    if not output_path.endswith(f".{output_format}"):
        base = os.path.splitext(output_path)[0]
        output_path = f"{base}.{output_format}"

    try:
        save_output_audio(final_audio, output_path, output_format)
        
        # Lưu file phụ đề SRT
        if srt_path and subtitles:
            from process.tts.srt_generator import write_srt
            write_srt(subtitles, srt_path)
            
        yield f"[OmniVoice] Done: {output_path} ({len(final_audio) / SAMPLE_RATE:.1f}s)"
    except Exception as e:
        yield f"[OmniVoice] Lỗi lưu file: {e}"
