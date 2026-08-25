"""SRT Generator — Hỗ trợ chia dòng phụ đề ngắn và sinh file phụ đề SRT cho CapCut.
"""

import os
import re

def split_into_subtitles(text: str, max_words: int = 10) -> list[str]:
    """Chia nhỏ một đoạn văn bản dài thành các cụm từ ngắn (5-12 từ) để làm phụ đề.
    Ưu tiên ngắt dòng tại các dấu câu tự nhiên.
    """
    words = text.strip().split()
    if not words:
        return []
    
    sub_lines = []
    current = []
    for w in words:
        current.append(w)
        # Điều kiện ngắt dòng phụ đề:
        # 1. Vượt quá số từ tối đa cho phép
        # 2. Kết thúc câu bằng dấu chấm, hỏi, cảm thán
        # 3. Kết thúc mệnh đề bằng dấu phẩy và đã có tối thiểu 6 từ
        if len(current) >= max_words:
            sub_lines.append(" ".join(current))
            current = []
        elif w[-1] in {'.', '?', '!', ':', ';'} or w.endswith('...'):
            sub_lines.append(" ".join(current))
            current = []
        elif w[-1] == ',' and len(current) >= 6:
            sub_lines.append(" ".join(current))
            current = []
            
    if current:
        sub_lines.append(" ".join(current))
        
    return sub_lines

def format_timestamp(seconds: float) -> str:
    """Chuyển đổi số giây thành định dạng SRT timestamp (HH:MM:SS,mmm).
    """
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    
    if millis >= 1000:
        millis = 0
        secs += 1
        if secs >= 60:
            secs = 0
            minutes += 1
            if minutes >= 60:
                minutes = 0
                hours += 1
                
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def parse_timestamp(ts_str: str) -> float:
    """Chuyển đổi định dạng SRT timestamp (HH:MM:SS,mmm) thành số giây.
    """
    ts_str = ts_str.strip().replace(',', '.')
    parts = ts_str.split(':')
    hours = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds

def write_srt(subtitles: list[dict], output_path: str):
    """Ghi danh sách phụ đề vào file .srt.
    Mỗi phần tử trong subtitles là dict: {"start": float, "end": float, "text": str}
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, sub in enumerate(subtitles, 1):
            f.write(f"{idx}\n")
            f.write(f"{format_timestamp(sub['start'])} --> {format_timestamp(sub['end'])}\n")
            f.write(f"{sub['text']}\n\n")

def shift_srt(input_path: str, output_path: str, offset_seconds: float):
    """Đọc file SRT cũ, cộng thêm offset_seconds vào toàn bộ timeline và lưu vào file mới.
    """
    if not os.path.exists(input_path):
        return
        
    pattern = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")
    
    shifted_lines = []
    index = 1
    
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Nếu là dòng chỉ số thứ tự, cập nhật lại chỉ số tuần tự cho file gộp
        if line.isdigit():
            # Kiểm tra xem dòng tiếp theo có phải là timeline không
            if i + 1 < len(lines) and pattern.match(lines[i + 1].strip()):
                shifted_lines.append(f"{index}\n")
                index += 1
                i += 1
                continue
                
        match = pattern.match(line)
        if match:
            start_str, end_str = match.groups()
            start_sec = parse_timestamp(start_str) + offset_seconds
            end_sec = parse_timestamp(end_str) + offset_seconds
            shifted_lines.append(f"{format_timestamp(start_sec)} --> {format_timestamp(end_sec)}\n")
        else:
            shifted_lines.append(lines[i])
        i += 1
        
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(shifted_lines)
