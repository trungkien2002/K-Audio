"""Audio Merger — Hỗ trợ gộp nhiều file âm thanh và dịch chuyển phụ đề SRT tương ứng.
"""

import os
import subprocess
import soundfile as sf
import numpy as np

def get_audio_duration(file_path: str) -> float:
    """Trả về độ dài (giây) của file audio.
    """
    if not os.path.exists(file_path):
        return 0.0
    try:
        info = sf.info(file_path)
        return info.duration
    except Exception:
        # Fallback dùng ffprobe nếu soundfile lỗi
        try:
            import json
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 0.0

def merge_audio_files(file_paths: list[str], output_path: str) -> bool:
    """Nối nhiều file audio thành một file duy nhất.
    """
    if not file_paths:
        return False
        
    ext = os.path.splitext(output_path)[1].lower().replace('.', '')
    is_mp3 = ext == "mp3" or any(f.lower().endswith(".mp3") for f in file_paths)
    
    # Thử gộp bằng soundfile trước (nếu là WAV, FLAC, OGG cùng rate)
    if not is_mp3:
        try:
            audio_data = []
            samplerate = None
            for p in file_paths:
                data, sr = sf.read(p)
                if samplerate is None:
                    samplerate = sr
                elif samplerate != sr:
                    raise ValueError("Samplerate mismatch")
                audio_data.append(data)
                
            if audio_data:
                combined = np.concatenate(audio_data, axis=0)
                sf.write(output_path, combined, samplerate)
                return True
        except Exception:
            pass
            
    # Fallback gộp bằng FFmpeg concat demuxer
    try:
        temp_list_path = output_path + ".list.txt"
        with open(temp_list_path, "w", encoding="utf-8") as f:
            for p in file_paths:
                abs_path = os.path.abspath(p).replace('\\', '/')
                f.write(f"file '{abs_path}'\n")
                
        if is_mp3:
            # Re-encode sang MP3 192k để đảm bảo tương thích
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", temp_list_path, "-c:a", "libmp3lame", "-b:a", "192k",
                output_path
            ]
        else:
            # Copy trực tiếp không re-encode
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", temp_list_path, "-c", "copy",
                output_path
            ]
            
        res = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(temp_list_path):
            os.remove(temp_list_path)
            
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"Error merging audio with FFmpeg: {e}")
        return False

def merge_chapters_pipeline(chapters_data: list[dict], merged_audio_path: str, merged_srt_path: str, export_srt: bool) -> bool:
    """Nối cả file Audio và dịch chuyển cộng dồn timeline SRT của danh sách chương.
    chapters_data: list of dict {"audio_path": str, "srt_path": str}
    """
    audio_files = [c["audio_path"] for c in chapters_data if os.path.exists(c["audio_path"])]
    if not audio_files:
        return False
        
    # 1. Gộp Audio trước
    success = merge_audio_files(audio_files, merged_audio_path)
    if not success:
        return False
        
    # 2. Gộp SRT
    if export_srt and merged_srt_path:
        from process.tts.srt_generator import shift_srt
        
        if os.path.exists(merged_srt_path):
            try:
                os.remove(merged_srt_path)
            except OSError:
                pass
                
        temp_merged_lines = []
        index = 1
        offset = 0.0
        
        for idx, chap in enumerate(chapters_data):
            srt_path = chap.get("srt_path")
            audio_path = chap.get("audio_path")
            
            if srt_path and os.path.exists(srt_path):
                temp_shifted_srt = srt_path + ".shifted.tmp"
                shift_srt(srt_path, temp_shifted_srt, offset)
                
                if os.path.exists(temp_shifted_srt):
                    with open(temp_shifted_srt, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    i = 0
                    while i < len(lines):
                        line = lines[i]
                        # Sửa lại số thứ tự index của phụ đề để chạy tuần tự liên tục
                        if line.strip().isdigit():
                            if i + 1 < len(lines) and "-->" in lines[i + 1]:
                                temp_merged_lines.append(f"{index}\n")
                                index += 1
                                i += 1
                                continue
                        temp_merged_lines.append(line)
                        i += 1
                        
                    try:
                        os.remove(temp_shifted_srt)
                    except OSError:
                        pass
            
            # Cộng dồn độ dài file âm thanh này cho chương kế tiếp
            duration = get_audio_duration(audio_path)
            offset += duration
            
        if temp_merged_lines:
            os.makedirs(os.path.dirname(merged_srt_path) or ".", exist_ok=True)
            with open(merged_srt_path, "w", encoding="utf-8") as f:
                f.writelines(temp_merged_lines)
                
    return True
