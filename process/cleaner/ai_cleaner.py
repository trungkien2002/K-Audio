"""AI Cleaner Backend — Kết nối Gemini API để tự động sinh luật Regex làm sạch."""

import os
import re
import json
import logging
import requests

LOGGER = logging.getLogger(__name__)


HIGH_RISK_KEYWORDS = [
    "truyenfull", "khotruyenchu", "ăn cắp", "reup", "đọc tại", "chuyển ngữ", 
    ".com", ".vn", "tải tại", "chấm cơm", "truyenyy", "bạn đang đọc"
]


def sample_chapter_paths(chapter_paths: list[str], count: int = 10) -> list[str]:
    """Lấy mẫu lai thông minh:
    1. Quét nhanh offline tìm các chương chứa từ khóa rủi ro cao (quảng cáo, watermark).
    2. Nếu tìm thấy, ưu tiên đưa các chương này vào danh sách mẫu gửi AI.
    3. Nếu không đủ, bổ sung các chương ở đầu truyện và phân bổ đều.
    """
    total = len(chapter_paths)
    if total <= count:
        return chapter_paths[:]

    # 1. Tìm các chương chứa từ khóa rủi ro
    candidate_indices = []
    for idx, path in enumerate(chapter_paths):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if any(word in content for word in HIGH_RISK_KEYWORDS):
                    candidate_indices.append(idx)
        except Exception:
            continue

    # 2. Xây dựng danh sách mẫu
    sampled_indices = []
    
    # Nếu tìm thấy các chương chứa rác rủi ro cao, lấy tối đa 6 chương làm mẫu
    if candidate_indices:
        cand_len = len(candidate_indices)
        take_count = min(6, cand_len)
        for i in range(take_count):
            c_idx = candidate_indices[int(i * (cand_len - 1) / (take_count - 1))] if take_count > 1 else candidate_indices[0]
            sampled_indices.append(c_idx)

    # 3. Bổ sung các chương đầu tiên (nơi thường có quảng cáo giới thiệu)
    head_take = min(3, total)
    for i in range(head_take):
        sampled_indices.append(i)

    # 4. Phân bổ thêm các chương rải rác để đảm bảo đủ số lượng mẫu (count)
    needed = count - len(set(sampled_indices))
    if needed > 0:
        for i in range(needed):
            idx = int(i * (total - 1) / (needed - 1)) if needed > 1 else total // 2
            sampled_indices.append(idx)

    # Đảm bảo duy nhất và sắp xếp theo thứ tự chương
    sampled_indices = sorted(list(set(sampled_indices)))
    
    # Giới hạn đúng số lượng count
    if len(sampled_indices) > count:
        final_indices = [sampled_indices[int(i * (len(sampled_indices) - 1) / (count - 1))] for i in range(count)]
        sampled_indices = sorted(list(set(final_indices)))

    return [chapter_paths[idx] for idx in sampled_indices]


def _read_sample_content(fpath: str) -> str:
    """Đọc và trích xuất thông minh:
    1. Quét tìm dòng chứa từ khóa rủi ro cao.
    2. Nếu thấy, lấy dòng đó cùng 2 dòng trước và 2 dòng sau để làm ngữ cảnh.
    3. Nếu không thấy, lấy 8 dòng đầu và 8 dòng cuối làm mặc định.
    """
    lines = []
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.read().split("\n") if l.strip()]
    except Exception:
        try:
            import chardet
            with open(fpath, "rb") as f:
                raw = f.read()
            detected = chardet.detect(raw)
            encoding = detected.get("encoding", "utf-8")
            content = raw.decode(encoding, errors="replace")
            lines = [l.strip() for l in content.split("\n") if l.strip()]
        except Exception:
            return ""

    if not lines:
        return ""

    # Tìm dòng chứa từ khóa rủi ro
    for idx, line in enumerate(lines):
        line_lower = line.lower()
        if any(word in line_lower for word in HIGH_RISK_KEYWORDS):
            # Lấy 2 dòng trước và 2 dòng sau làm ngữ cảnh
            start = max(0, idx - 2)
            end = min(len(lines), idx + 3)
            context = "\n".join(lines[start:end])
            return f"[Trích đoạn chứa từ khóa nghi vấn (dòng {idx+1})]:\n{context}"

    # Fallback mặc định: trích đầu và cuối
    first_part = "\n".join(lines[:8])
    last_part = "\n".join(lines[-8:])
    return f"[Đoạn Đầu]:\n{first_part}\n[Đoạn Cuối]:\n{last_part}"


def analyze_samples_with_ai(sample_paths: list[str], gemini_key: str) -> list[dict]:
    """Gửi mẫu thử của các chương cho AI để phân tích và tự sinh quy tắc Regex lọc rác."""
    if not gemini_key:
        raise ValueError("Chưa cấu hình Gemini API Key trong Settings!")

    # 1. Thu thập dữ liệu mẫu (sử dụng tối đa 500 ký tự mỗi đoạn đầu/cuối để tránh vượt quá giới hạn Tokens)
    samples_data = []
    for i, path in enumerate(sample_paths):
        filename = os.path.basename(path)
        part = _read_sample_content(path)
        if part:
            samples_data.append(f"=== Chương {i+1} ({filename}) ===\n{part}")

    combined_samples = "\n\n".join(samples_data)

    # 2. Xây dựng prompt
    prompt = f"""Dưới đây là một số đoạn trích đầu và cuối của nhiều chương truyện khác nhau.
Nhiệm vụ của bạn là hãy phân tích các đoạn trích này, phát hiện các đoạn văn bản rác chèn vào truyện (watermark, quảng cáo website, liên kết link website lậu, bình luận spam, kêu gọi đánh giá vote sao của website lậu) xuất hiện ở bất kỳ trích đoạn nào (kể cả chỉ xuất hiện ở một chương duy nhất trong các mẫu).

Hãy tạo ra các quy tắc biểu thức chính quy (Regex trong Python) tối ưu nhất để xóa sạch các đoạn rác này mà không làm ảnh hưởng đến câu chữ truyện gốc xung quanh.

Yêu cầu kỹ thuật cho các Regex:
1. Regex phải khớp đúng và đủ cụm từ rác, tránh viết quá chung chung làm xóa nhầm từ trong truyện (Ví dụ: thay vì dùng 'T.r.u.y.e.n.y.y' hãy đổi dấu '.' thành '\\.' và dùng khoảng trắng linh hoạt '\\s+').
2. Nếu watermark/quảng cáo là một dòng riêng biệt, hãy tạo regex khớp dòng đó.
3. Không lọc các từ ngữ thuộc diễn biến truyện.
4. Trả về kết quả dưới dạng danh sách đối tượng JSON có định dạng chính xác sau đây (không kèm text giải thích bên ngoài):
[
  {{
    "pattern": "regex_pattern_here",
    "name": "Tên loại rác (Ví dụ: Tên miền truyenfull)",
    "reason": "Giải thích ngắn gọn lý do chèn luật"
  }}
]

Dưới đây là dữ liệu mẫu của truyện:
{combined_samples}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json"
        }
    }

    # 3. Gọi Gemini API thử nghiệm xoay vòng các model để phòng ngừa lỗi Quota/429
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash"
    ]

    last_err = None
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            resp = requests.post(url, json=payload, timeout=90)
            if resp.status_code == 200:
                result_json = resp.json()
                text_out = result_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                rules = json.loads(text_out)
                if isinstance(rules, list):
                    return rules
            else:
                last_err = f"Model {model_name} trả về lỗi {resp.status_code}: {resp.text}"
                LOGGER.warning(last_err)
        except Exception as e:
            last_err = f"Model {model_name} lỗi: {e}"
            LOGGER.warning(last_err)

    raise RuntimeError(f"Tất cả các mô hình Gemini đều từ chối yêu cầu do quá hạn mức (Quota 429) hoặc sai API Key.\nChi tiết lỗi cuối: {last_err}")


def generate_rule_from_text(selected_text: str, gemini_key: str) -> dict:
    """Tự động sinh quy tắc Regex tối ưu từ một đoạn văn bản cụ thể do người dùng chọn."""
    if not gemini_key:
        raise ValueError("Chưa cấu hình Gemini API Key!")

    prompt = f"""Hãy sinh một quy tắc biểu thức chính quy Regex trong Python (case-insensitive) an toàn nhất để tìm và xóa hoàn toàn đoạn rác/watermark sau đây ra khỏi câu văn:
"{selected_text}"

Yêu cầu:
- Tự động thay thế các khoảng trắng bằng '\\s+' để đảm bảo khớp dù xuống dòng hoặc thừa dấu cách.
- Thêm dấu thoát '\\' cho các ký tự đặc biệt của regex như dấu chấm '.', ngoặc đơn, ngoặc vuông, dấu hỏi...
- Đảm bảo regex chỉ nhắm vào đoạn rác này, không làm ảnh hưởng đến từ ngữ khác.
- Trả về kết quả dưới dạng duy nhất một đối tượng JSON có định dạng chính xác sau:
{{
  "pattern": "regex_pattern_here",
  "name": "Tùy chỉnh",
  "reason": "Sinh tự động từ bôi đen văn bản"
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json"
        }
    }

    models_to_try = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash"
    ]

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                result_json = resp.json()
                text_out = result_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(text_out)
        except Exception as e:
            LOGGER.warning(f"Failed to generate rule with {model_name}: {e}")

    # Fallback dự phòng nếu toàn bộ AI lỗi
    return {
        "pattern": re.escape(selected_text).replace(r"\ ", r"\s+"),
        "name": "Tùy chỉnh",
        "reason": "Sinh tự động (Chế độ dự phòng offline do AI quá tải)"
    }
