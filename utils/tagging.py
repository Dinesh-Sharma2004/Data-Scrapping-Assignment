"""Topic tagging based on TF-IDF keywords."""

from __future__ import annotations

import re
from typing import Iterable

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


TOPIC_ALIASES = {
    "ai": "AI",
    "artificial intelligence": "AI",
    "machine learning": "machine learning",
    "health": "healthcare",
    "healthcare": "healthcare",
    "medical": "medicine",
    "medicine": "medicine",
    "clinical": "clinical research",
    "study": "research",
    "research": "research",
    "data": "data science",
}


def _fallback_keywords(text: str, limit: int) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z-]{2,}", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        if word in ENGLISH_STOP_WORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]]


def tag_topics(text: str, top_n: int = 5) -> list[str]:
    """Return normalized topic tags from one document."""

    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = text.strip()
    if not text:
        return []

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=80,
            token_pattern=r"(?u)\b[A-Za-z][A-Za-z-]{2,}\b",
        )
        matrix = vectorizer.fit_transform([text])
        features = vectorizer.get_feature_names_out()
        scores = matrix.toarray()[0]
        ranked = [
            features[index]
            for index in scores.argsort()[::-1]
            if scores[index] > 0
        ][:top_n]
    except Exception:
        ranked = _fallback_keywords(text, top_n)

    return _normalize_tags(ranked, top_n)


def _normalize_tags(tags: Iterable[str], top_n: int) -> list[str]:
    normalized = []
    for tag in tags:
        tag = tag.strip().lower()
        tag = TOPIC_ALIASES.get(tag, tag)
        if tag and tag not in normalized:
            normalized.append(tag)
        if len(normalized) == top_n:
            break
    return normalized
