"""Text filter/cleaner engine — loại bỏ spam, URL, zero-width chars, unicode normalization.

Merged from ToolFinal (project/core/cleaner/filter_engine.py) + TruyenCrawler (crawler/utils.py).
"""

import re
import unicodedata
from dataclasses import dataclass, field


# ─────────────────────────── Zero-Width Characters ───────────────────

ZERO_WIDTH_CHARS = [
    "\u200B", "\u200C", "\u200D", "\uFEFF", "\u200E", "\u200F",
    "\u2028", "\u2029", "\u00AD", "\u034F", "\u061C",
    "\u115F", "\u1160", "\u17B4", "\u17B5",
    "\u202A", "\u202B", "\u202C", "\u202D", "\u202E", "\u202F",
    "\u2060", "\u180E",
]


# ─────────────────────────── Default Filter Patterns ─────────────────

DEFAULT_PATTERNS = [
    # URLs
    (r"https?://\S+", "URL"),
    (r"www\.\S+", "URL"),
    (r"\S+\.com\S*", "URL"),
    (r"\S+\.net\S*", "URL"),
    (r"\S+\.org\S*", "URL"),
    # Source credits & Common Watermarks
    (r"Nguồn\s*:\s*\S+", "Source credit"),
    (r"Bạn\s+đang\s+đọc(?:\s+truyện)?(?:\s+được)?(?:\s+lấy)?(?:\s+tại|\s+từ)?", "Copyright"),
    (r"Truyện\s+được?\s+lấy\s+từ", "Copyright"),
    (r"Đọc\s+truyện\s+tại", "Copyright"),
    (r"Chapters?\s+được?\s+dịch\s+bởi", "Copyright"),
    (r"Truyện\s+FULL", "Copyright"),
    # Spam
    (r"Cầu\s+nguyệt\s+phiếu", "Spam vote"),
    (r"Vote\s+\d+\s+sao", "Spam vote"),
    (r"đánh\s+giá\s+(?:5\s+sao|nhiều\s+sao|truyện|hữu\s+ích|5\s+\*)", "Spam"),
    # Anti-piracy
    (r"Web\s+lậu", "Anti-piracy"),
    (r"chống\s+đạo\s+văn", "Anti-piracy"),
    (r"ăn\s+cắp\s+truyện", "Anti-piracy"),
    (r"copy\s+truyện", "Anti-piracy"),
    # Separators (anchored to prevent matching inside normal story lines)
    (r"^\s*-\s*\*\s*-\s*\*\s*-\s*\*\s*-+\s*$", "Separator"),
    (r"^\s*\*{3,}\s*$", "Separator"),
    (r"^\s*={3,}\s*$", "Separator"),
    (r"^\s*[-=\*_~#\.\s\+\/]{4,}\s*$", "Separator"),
    # Domain spam
    (r"khotruyenchu\.\S+", "Domain spam"),
    (r"truyenfull\.\S+", "Domain spam"),
    (r"t\s*[\.\s_]*r\s*[\.\s_]*u\s*[\.\s_]*y\s*[\.\s_]*e\s*[\.\s_]*n\s*[\.\s_]*y\s*[\.\s_]*y(?:\s*\.\s*c\s*\.\s*o\s*\.\s*m)?", "Domain spam"),
]


# ─────────────────────────── Data Classes ────────────────────────────

@dataclass
class FilterIssue:
    """A single issue found during filtering."""
    chapter_id: int
    line_num: int
    original_line: str
    pattern_name: str
    action: str = "remove"
    pattern_regex: str = ""


@dataclass
class CleanResult:
    """Result of cleaning text."""
    cleaned_text: str
    issues: list = field(default_factory=list)
    lines_removed: int = 0

    @property
    def issue_count(self) -> int:
        return len(self.issues)


# ─────────────────────────── Core Functions ──────────────────────────

def remove_zero_width(text: str) -> str:
    """Remove all zero-width and invisible characters."""
    for ch in ZERO_WIDTH_CHARS:
        text = text.replace(ch, "")
    return text


def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFC form."""
    return unicodedata.normalize("NFC", text)


def remove_patterns(
    text: str,
    custom_patterns: list[str] | None = None,
) -> tuple[str, list[FilterIssue]]:
    """Remove matching patterns from text, returning cleaned text and issues."""
    if custom_patterns is not None:
        patterns = []
        default_map = {p: name for p, name in DEFAULT_PATTERNS}
        for p in custom_patterns:
            if p.strip():
                name = default_map.get(p, "Tùy chỉnh")
                patterns.append((p, name))
    else:
        patterns = DEFAULT_PATTERNS[:]

    issues = []
    lines = text.split("\n")
    cleaned_lines = []

    for i, line in enumerate(lines):
        cleaned = line
        for pattern, name in patterns:
            if not pattern.strip():
                continue
            try:
                if re.search(pattern, cleaned, re.IGNORECASE):
                    issues.append(
                        FilterIssue(
                            chapter_id=0,
                            line_num=i + 1,
                            original_line=line.strip(),
                            pattern_name=name,
                            pattern_regex=pattern,
                        )
                    )
                    cleaned = re.sub(
                        pattern, "", cleaned, flags=re.IGNORECASE
                    ).strip()
            except Exception:
                # Skip invalid regex patterns
                continue
        cleaned_lines.append(cleaned)

    return "\n".join(cleaned_lines), issues


def clean_text(
    text: str,
    custom_patterns: list[str] | None = None,
    remove_zw: bool = True,
    norm_unicode: bool = True,
) -> tuple[str, list[FilterIssue]]:
    """Full text cleaning pipeline.

    Steps:
    1. Remove zero-width characters
    2. Normalize Unicode (NFC)
    3. Remove patterns (URL, spam, copyright, etc.)
    4. Collapse whitespace and blank lines

    Returns:
        Tuple of (cleaned_text, list_of_issues).
    """
    if remove_zw:
        text = remove_zero_width(text)
    if norm_unicode:
        text = normalize_unicode(text)
    text, issues = remove_patterns(text, custom_patterns)

    # Collapse horizontal whitespace
    lines = text.split("\n")
    cleaned_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]

    # Remove consecutive empty lines (keep max 1 blank line)
    result_lines = []
    prev_empty = False
    for line in cleaned_lines:
        # Strip lines that only contain a single punctuation or dash like "-", ".", ",", "_", "—"
        if re.match(r'^[-–—\.,_\s]+$', line):
            line = ""

        if not line:
            if not prev_empty:
                result_lines.append("")
                prev_empty = True
        else:
            result_lines.append(line)
            prev_empty = False

    cleaned_text = "\n".join(result_lines).strip()
    return cleaned_text, issues
