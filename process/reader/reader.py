"""File reader — đọc TXT/EPUB/DOCX/PDF với auto-detect encoding.

Merged from ToolFinal (project/core/input/reader.py) + Tool (backend/core/story_splitter.py).
"""

import os
import re
import html as html_module
import chardet
from pathlib import Path


SUPPORTED_FORMATS = {".txt", ".epub", ".docx", ".pdf"}


def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, "rb") as f:
        raw = f.read()
    result = chardet.detect(raw)
    return result.get("encoding", "utf-8") or "utf-8"


def _clean_html(html_str: str) -> str:
    """Strip HTML tags and decode entities, preserving paragraph breaks."""
    # Replace block-level tags with newlines
    html_str = re.sub(
        r'</?(?:p|div|h[1-6]|li|tr|br\s*/?|blockquote|section|article)>',
        '\n',
        html_str,
        flags=re.IGNORECASE,
    )
    # Strip style/script
    html_str = re.sub(
        r'<(script|style).*?>.*?</\1>',
        '',
        html_str,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Strip all remaining tags
    text = re.sub(r'<.*?>', '', html_str)
    text = html_module.unescape(text)

    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(l for l in lines if l)


def read_txt(file_path: str) -> str:
    """Read a .txt file with auto-detect encoding, handling embedded HTML."""
    encoding = detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        content = f.read()
    # Detect if content is actually HTML
    if any(tag in content for tag in ('<html', '<body', '<p class=', '<div', '</html>')):
        content = _clean_html(content)
    return content


def read_epub(file_path: str) -> str:
    """Read an EPUB file, extracting text from all document items."""
    import ebooklib
    from ebooklib import epub
    import warnings

    texts = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        book = epub.read_epub(file_path, options={"ignore_ncx": True})

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_body_content()
            if content:
                html_str = content.decode("utf-8", errors="ignore")
                clean = _clean_html(html_str)
                if clean:
                    texts.append(clean)
    return "\n\n".join(texts)


def read_docx(file_path: str) -> str:
    """Read a DOCX file."""
    from docx import Document
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def read_pdf(file_path: str) -> str:
    """Read a PDF file using PyMuPDF."""
    import fitz
    doc = fitz.open(file_path)
    texts = [page.get_text().strip() for page in doc if page.get_text().strip()]
    doc.close()
    return "\n\n".join(texts)


def read_file(file_path: str) -> str:
    """Read a file in any supported format."""
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {ext}. Supported: {SUPPORTED_FORMATS}")
    readers = {
        ".txt": read_txt,
        ".epub": read_epub,
        ".docx": read_docx,
        ".pdf": read_pdf,
    }
    return readers[ext](file_path)


def get_file_info(file_path: str) -> dict:
    """Get metadata about a file."""
    ext = os.path.splitext(file_path)[1].lower()
    return {
        "name": os.path.basename(file_path),
        "path": file_path,
        "format": ext,
        "size": os.path.getsize(file_path),
        "encoding": detect_encoding(file_path) if ext == ".txt" else "N/A",
    }
