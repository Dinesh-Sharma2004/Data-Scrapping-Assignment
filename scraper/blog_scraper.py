"""Blog/article scraping utilities."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT_SECONDS = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TrustScoringScraper/1.0; "
        "+https://example.com/bot)"
    )
}


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _meta_content(soup: BeautifulSoup, *selectors: dict[str, str]) -> str:
    for attrs in selectors:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return _clean_text(tag["content"])
    return ""


def _extract_title(soup: BeautifulSoup) -> str:
    meta_title = _meta_content(
        soup,
        {"property": "og:title"},
        {"name": "twitter:title"},
    )
    if meta_title:
        return meta_title
    if soup.title and soup.title.string:
        return _clean_text(soup.title.string)
    heading = soup.find("h1")
    return _clean_text(heading.get_text(" ")) if heading else ""


def _extract_author(soup: BeautifulSoup) -> str:
    author = _meta_content(
        soup,
        {"name": "author"},
        {"property": "article:author"},
        {"name": "byl"},
    )
    if author:
        return author

    author_selectors = [
        "[rel='author']",
        ".author",
        ".byline",
        "[class*='author']",
        "[class*='byline']",
    ]
    for selector in author_selectors:
        node = soup.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" "))
            if text and len(text) <= 120:
                return text
    return ""


def _normalize_date(value: str) -> str:
    value = _clean_text(value)
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError:
        return value


def _extract_publish_date(soup: BeautifulSoup) -> str:
    date_value = _meta_content(
        soup,
        {"property": "article:published_time"},
        {"name": "pubdate"},
        {"name": "publishdate"},
        {"name": "date"},
        {"itemprop": "datePublished"},
    )
    if date_value:
        return _normalize_date(date_value)

    time_tag = soup.find("time")
    if time_tag:
        date_value = time_tag.get("datetime") or time_tag.get_text(" ")
        return _normalize_date(date_value)
    return ""


def _extract_main_content(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    container = (
        soup.find("article")
        or soup.find("main")
        or soup.select_one("[role='main']")
        or soup.select_one(".post-content, .entry-content, .article-content, .content")
        or soup.body
        or soup
    )

    paragraphs = [
        _clean_text(node.get_text(" "))
        for node in container.find_all(["p", "li"])
    ]
    paragraphs = [p for p in paragraphs if len(p.split()) >= 5]

    if not paragraphs:
        text = _clean_text(container.get_text(" "))
        return text
    return "\n\n".join(paragraphs)


def scrape_blog(url: str) -> dict[str, Any]:
    """Scrape one blog/article URL and return metadata plus content."""

    result: dict[str, Any] = {
        "source_url": url,
        "source_type": "blog",
        "title": "",
        "author": "",
        "published_date": "",
        "meta_description": "",
        "content": "",
        "citation_count": 0,
        "error": "",
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        result.update(
            {
                "title": _extract_title(soup),
                "author": _extract_author(soup),
                "published_date": _extract_publish_date(soup),
                "meta_description": _meta_content(
                    soup,
                    {"name": "description"},
                    {"property": "og:description"},
                    {"name": "twitter:description"},
                ),
                "content": _extract_main_content(soup),
                "citation_count": len(soup.find_all("a", href=True)),
            }
        )
    except requests.RequestException as exc:
        result["error"] = f"request_failed: {exc}"
    except Exception as exc:  # Keep batch jobs alive when one page is malformed.
        result["error"] = f"parse_failed: {exc}"

    return result
