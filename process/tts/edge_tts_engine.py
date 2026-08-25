"""Edge-TTS engine — Microsoft Edge TTS (online).

From Tool (backend/core/tts_converter.py).
"""

import asyncio
import os
import shutil
import time
import random
from typing import Generator


def _split_text(text: str, chunk_size: int = 1000) -> list[str]:
    sentences = text.replace('\n', ' ').split('. ')
    chunks = []
    current = ''
    for s in sentences:
        if len(current) + len(s) < chunk_size:
            current += s + '. '
        else:
            if current:
                chunks.append(current.strip())
            current = s + '. '
    if current:
        chunks.append(current.strip())
    return chunks


def tts_edge(
    text: str,
    output_path: str,
    voice: str = "vi-VN-HoaiMyNeural",
    speed: float = 1.0,
    stop_event=None,
    srt_path: str = None,
) -> Generator[str, None, None]:
    """Generate audio using Microsoft Edge TTS, with optional SRT subtitle generation."""
    import edge_tts
    from process.tts.audio_merger import get_audio_duration
    from process.tts.srt_generator import write_srt

    if len(text) <= 15000:
        chunks = [text.strip()]
    else:
        raw_chunks = _split_text(text, chunk_size=10000)
        chunks = [c for c in raw_chunks if any(char.isalnum() for char in c)]

    if not chunks:
        yield f"Done: {output_path} (silence)"
        return

    rate_str = f"+{int((speed - 1) * 100)}%" if speed >= 1 else f"{int((speed - 1) * 100)}%"
    if rate_str.startswith("+0"):
        rate_str = rate_str[1:]

    generated_parts = []
    all_words = []
    cumulative_offset = 0.0

    try:
        for i, chunk in enumerate(chunks):
            if stop_event and stop_event.is_set():
                return
            base, _ = os.path.splitext(output_path)
            tmp_path = f"{base}_part{i:03d}.mp3"

            max_retries = 5
            success = False
            for attempt in range(max_retries):
                if stop_event and stop_event.is_set():
                    return
                try:
                    chunk_words = []

                    async def _run():
                        communicate = edge_tts.Communicate(chunk, voice, rate=rate_str)
                        with open(tmp_path, "wb") as fp:
                            async for chunk_item in communicate.stream():
                                if chunk_item["type"] == "audio":
                                    fp.write(chunk_item["data"])
                                elif chunk_item["type"] == "WordBoundary" and srt_path:
                                    offset_sec = chunk_item["offset"] * 1e-7
                                    duration_sec = chunk_item["duration"] * 1e-7
                                    chunk_words.append({
                                        "word": chunk_item["text"],
                                        "start": offset_sec,
                                        "end": offset_sec + duration_sec
                                    })

                    asyncio.run(_run())
                    success = True
                    break
                except Exception:
                    if attempt == max_retries - 1:
                        raise
                    delay = 5 * (attempt + 1) + random.uniform(0, 2)
                    time.sleep(delay)

            if success:
                generated_parts.append(tmp_path)
                
                # Cập nhật thời gian từ cho file phụ đề
                if srt_path and chunk_words:
                    for w in chunk_words:
                        w["start"] += cumulative_offset
                        w["end"] += cumulative_offset
                    all_words.extend(chunk_words)
                
                # Tính độ dài thực tế của chunk để cộng dồn offset
                chunk_duration = get_audio_duration(tmp_path)
                cumulative_offset += chunk_duration

                yield f"Chunk {i + 1}/{len(chunks)} done"
                if i < len(chunks) - 1:
                    time.sleep(1)
    except Exception as e:
        yield f"Error: {e}"
        return

    # Merge parts
    try:
        if len(generated_parts) == 1:
            shutil.copy2(generated_parts[0], output_path)
        else:
            with open(output_path, 'wb') as out:
                for part in generated_parts:
                    with open(part, 'rb') as f:
                        out.write(f.read())
                        
        # Sinh file phụ đề SRT từ danh sách từ thu được
        if srt_path and all_words:
            subtitles = []
            current_words = []
            for w_info in all_words:
                current_words.append(w_info)
                w_text = w_info["word"]
                ends_sentence = w_text[-1] in {'.', '?', '!', ':', ';'} or w_text.endswith('...')
                ends_clause = w_text[-1] == ','
                
                if len(current_words) >= 10:  # Tối đa 10 từ một dòng phụ đề
                    subtitles.append({
                        "start": current_words[0]["start"],
                        "end": current_words[-1]["end"],
                        "text": " ".join([x["word"] for x in current_words])
                    })
                    current_words = []
                elif ends_sentence:
                    subtitles.append({
                        "start": current_words[0]["start"],
                        "end": current_words[-1]["end"],
                        "text": " ".join([x["word"] for x in current_words])
                    })
                    current_words = []
                elif ends_clause and len(current_words) >= 6:
                    subtitles.append({
                        "start": current_words[0]["start"],
                        "end": current_words[-1]["end"],
                        "text": " ".join([x["word"] for x in current_words])
                    })
                    current_words = []
                    
            if current_words:
                subtitles.append({
                    "start": current_words[0]["start"],
                    "end": current_words[-1]["end"],
                    "text": " ".join([x["word"] for x in current_words])
                })
                
            write_srt(subtitles, srt_path)

        yield f"Done: {output_path}"
    except Exception as e:
        yield f"Merge error: {e}"
    finally:
        for part in generated_parts:
            try:
                os.remove(part)
            except OSError:
                pass
