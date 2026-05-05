"""Entrypoint for the multi-source scraping and trust scoring pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scraper.blog_scraper import scrape_blog
from scraper.pubmed_scraper import scrape_pubmed
from scraper.youtube_scraper import scrape_youtube
from scoring.trust_score import compute_trust_score
from utils.chunking import chunk_content
from utils.language import detect_language, detect_region
from utils.tagging import tag_topics


BASE_DIR = Path(__file__).resolve().parent
URLS_PATH = BASE_DIR / "data" / "urls.json"
OUTPUT_PATH = BASE_DIR / "output" / "scraped_data.json"


SCRAPERS = {
    "blog": scrape_blog,
    "youtube": scrape_youtube,
    "pubmed": scrape_pubmed,
}


def load_urls(path: Path = URLS_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        sources = []
        for source_type, urls in data.items():
            for url in urls:
                sources.append({"type": source_type, "url": url})
        return sources
    return data


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    content = (
        raw.get("content")
        or raw.get("abstract")
        or raw.get("description")
        or raw.get("meta_description")
        or ""
    )
    normalized = {
        "source_url": raw.get("source_url", ""),
        "source_type": raw.get("source_type", ""),
        "author": raw.get("author", ""),
        "published_date": raw.get("published_date") or raw.get("publication_year", ""),
        "language": detect_language(content),
        "region": detect_region(raw.get("source_url", "")),
        "topic_tags": tag_topics(content),
        "trust_score": 0.0,
        "content_chunks": chunk_content(content),
    }
    normalized["trust_score"] = compute_trust_score({**raw, **normalized})
    return normalized


def run_pipeline() -> list[dict[str, Any]]:
    results = []
    for source in load_urls():
        source_type = source.get("type", "").lower()
        url = source.get("url", "")
        scraper = SCRAPERS.get(source_type)
        if not scraper:
            results.append(
                {
                    "source_url": url,
                    "source_type": source_type,
                    "author": "",
                    "published_date": "",
                    "language": "unknown",
                    "region": detect_region(url),
                    "topic_tags": [],
                    "trust_score": 0.0,
                    "content_chunks": [],
                    "error": f"unsupported_source_type: {source_type}",
                }
            )
            continue

        raw = scraper(url)
        results.append(normalize_item(raw))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    items = run_pipeline()
    print(f"Saved {len(items)} scraped items to {OUTPUT_PATH}")
