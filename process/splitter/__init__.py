"""Splitter package — tách truyện thành chương."""

from process.splitter.splitter import (
    split_chapters,
    auto_detect_pattern,
    Chapter,
    SplitResult,
    DEFAULT_PATTERNS,
)

__all__ = [
    "split_chapters",
    "auto_detect_pattern",
    "Chapter",
    "SplitResult",
    "DEFAULT_PATTERNS",
]
