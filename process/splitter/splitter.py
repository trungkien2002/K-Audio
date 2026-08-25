"""Chapter splitter — tách truyện thành chương với 10 patterns.

Merged from ToolFinal (project/core/input/splitter.py) + Tool (backend/core/story_splitter.py).
"""

import re
from dataclasses import dataclass, field


DEFAULT_PATTERNS = [
    r"Chương\s+\d+",
    r"Chuong\s+\d+",
    r"Chapter\s+\d+",
    r"Hồi\s+\d+",
    r"Quyển\s+\d+",
    r"Phần\s+\d+",
    r"Part\s+\d+",
    r"Volume\s+\d+",
    r"Book\s+\d+",
    r"第.+章",
]


@dataclass
class Chapter:
    """A single chapter extracted from the text."""
    id: int
    title: str
    content: str
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.content.split())


@dataclass
class SplitResult:
    """Result of splitting a text into chapters."""
    chapters: list = field(default_factory=list)
    preamble: str = ""
    pattern_used: str = ""

    @property
    def total_words(self) -> int:
        return sum(ch.word_count for ch in self.chapters)

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)


def split_chapters(text: str, pattern: str | None = None, min_words: int = 50) -> SplitResult:
    """Split text into chapters using a regex pattern.

    Args:
        text: The full text to split.
        pattern: Regex pattern to detect chapter boundaries.
        min_words: Minimum word count per chapter (skip shorter ones).

    Returns:
        SplitResult with list of chapters and metadata.
    """
    if pattern is None:
        pattern = DEFAULT_PATTERNS[0]

    full_pattern = f"({pattern})"
    parts = re.split(full_pattern, text, flags=re.IGNORECASE)

    chapters = []
    preamble = ""

    # If the pattern didn't match, return the whole text as a single chapter
    if len(parts) < 3:
        preamble = text
        if preamble.strip():
            chapters.append(Chapter(id=1, title="Full Text", content=preamble.strip()))
        return SplitResult(chapters=chapters, preamble="", pattern_used=pattern)

    # First part before any chapter heading is preamble
    if parts[0].strip():
        preamble = parts[0].strip()

    chapter_id = 0
    i = 1
    while i < len(parts) - 1:
        title = parts[i].strip()
        content = parts[i + 1].strip()
        if content and len(content.split()) >= min_words:
            chapter_id += 1
            chapters.append(Chapter(id=chapter_id, title=title, content=content))
        i += 2

    # Fallback: if no chapters were found, return the whole text
    if not chapters and text.strip():
        chapters.append(Chapter(id=1, title="Full Text", content=text.strip()))

    return SplitResult(chapters=chapters, preamble=preamble, pattern_used=pattern)


def auto_detect_pattern(text: str) -> tuple[str, int]:
    """Auto-detect the best chapter pattern for the given text.

    Returns:
        Tuple of (pattern, match_count).
    """
    for pattern in DEFAULT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if len(matches) >= 3:
            return pattern, len(matches)
    return DEFAULT_PATTERNS[0], 0
