"""Google TTS engine (gTTS) — free, online.

From Tool (backend/core/tts_converter.py).
"""

import os
import time
from typing import Generator


def _split_text(text: str, chunk_size: int = 1000) -> list[str]:
    sentences = text.replace('\n', ' ').split('. ')
    chunks, current = [], ''
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


def tts_gtts(
    text: str,
    output_path: str,
    voice: str = "vi",
    stop_event=None,
) -> Generator[str, None, None]:
    """Generate audio using Google TTS."""
    from gtts import gTTS

    actual_lang = "vi"
    tld = "com"
    client = "t"
    if voice == "vi-vn-alt":
        client = "tw-ob"

    def _save(text_part, path):
        tts = gTTS(text_part, lang=actual_lang, tld=tld)
        if client != "t":
            tts.client = client
        tts.save(path)

    raw_chunks = _split_text(text)
    chunks = [c for c in raw_chunks if any(ch.isalnum() for ch in c)]

    if not chunks:
        try:
            _save(" ", output_path)
            yield f"Done: {output_path} (silence)"
        except Exception as e:
            yield f"Error: {e}"
        return

    if len(chunks) == 1:
        if stop_event and stop_event.is_set():
            return
        try:
            _save(chunks[0], output_path)
            yield f"Done: {output_path}"
        except Exception as e:
            yield f"Error: {e}"
        return

    generated_parts = []
    success = True
    for i, chunk in enumerate(chunks):
        if stop_event and stop_event.is_set():
            success = False
            break
        tmp_path = output_path.replace(".mp3", f"_part{i:03d}.mp3")
        try:
            _save(chunk, tmp_path)
            generated_parts.append(tmp_path)
            yield f"Chunk {i + 1}/{len(chunks)} done"
            time.sleep(0.2)
        except Exception as e:
            yield f"Chunk {i + 1} error: {e}"
            success = False
            break

    if success:
        try:
            with open(output_path, "wb") as out:
                for part in generated_parts:
                    with open(part, "rb") as f:
                        out.write(f.read())
            yield f"Done: {output_path}"
        except Exception as e:
            yield f"Merge error: {e}"

    for part in generated_parts:
        try:
            os.remove(part)
        except OSError:
            pass
