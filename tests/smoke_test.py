"""Dependency-light smoke tests for the scraping project."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.youtube_scraper import extract_video_id
from scoring.trust_score import compute_trust_score
from utils.chunking import chunk_content
from utils.language import detect_language, detect_region
from utils.tagging import tag_topics


def test_core_utilities() -> None:
    assert extract_video_id("https://youtu.be/abc123XYZ") == "abc123XYZ"
    assert detect_language("This is an English healthcare article.") == "en"
    assert detect_region("https://example.co.uk/a") == "United Kingdom"
    assert len(chunk_content("word " * 650)) >= 3

    tags = tag_topics("AI machine learning healthcare medicine AI data science https://example.com")
    assert tags
    assert "com" not in tags


def test_trust_score_bounds() -> None:
    score = compute_trust_score(
        {
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/1/",
            "source_type": "pubmed",
            "author": "NIH",
            "published_date": "2025",
            "content": "This summary says to consult your doctor.",
            "citation_count": 1,
        }
    )
    assert 0.0 <= score <= 1.0


if __name__ == "__main__":
    test_core_utilities()
    test_trust_score_bounds()
    print("smoke_tests_passed")
