"""Content chunking utilities."""

from __future__ import annotations

import re


def chunk_content(text: str, min_words: int = 200, max_words: int = 300) -> list[str]:
    """Split text into paragraph-aware chunks of roughly 200-300 words."""

    text = text.strip()
    if not text:
        return []

    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current: list[str] = []
    current_count = 0

    for paragraph in paragraphs:
        words = paragraph.split()
        if len(words) > max_words:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_count = 0
            for start in range(0, len(words), max_words):
                chunks.append(" ".join(words[start : start + max_words]))
            continue

        if current and current_count + len(words) > max_words:
            chunks.append(" ".join(current))
            current = []
            current_count = 0

        current.append(paragraph)
        current_count += len(words)

        if current_count >= min_words:
            chunks.append(" ".join(current))
            current = []
            current_count = 0

    if current:
        chunks.append(" ".join(current))

    return chunks
