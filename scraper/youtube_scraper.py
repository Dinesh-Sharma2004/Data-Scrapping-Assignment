"""YouTube metadata and transcript scraping."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)


REQUEST_TIMEOUT_SECONDS = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TrustScoringScraper/1.0; "
        "+https://example.com/bot)"
    )
}


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname and "youtu.be" in parsed.hostname:
        return parsed.path.strip("/")
    query_id = parse_qs(parsed.query).get("v", [""])[0]
    if query_id:
        return query_id
    match = re.search(r"/(?:embed|shorts)/([A-Za-z0-9_-]{6,})", parsed.path)
    return match.group(1) if match else ""


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _initial_player_response(html: str) -> dict[str, Any]:
    match = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\});", html)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def _fetch_page_metadata(url: str) -> dict[str, str]:
    metadata = {
        "title": "",
        "channel_name": "",
        "published_date": "",
        "description": "",
    }
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        return metadata

    soup = BeautifulSoup(response.text, "html.parser")
    player = _initial_player_response(response.text)
    details = player.get("videoDetails", {})
    microformat = (
        player.get("microformat", {})
        .get("playerMicroformatRenderer", {})
    )

    description = details.get("shortDescription") or ""
    if not description:
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag.get("content", "") if description_tag else ""

    page_title = details.get("title") or (soup.title.string if soup.title else "")
    metadata.update(
        {
            "title": _clean_text(page_title),
            "channel_name": _clean_text(details.get("author") or ""),
            "published_date": _clean_text(microformat.get("publishDate") or microformat.get("uploadDate") or ""),
            "description": _clean_text(description),
        }
    )
    return metadata


def _fetch_transcript(video_id: str) -> str:
    if not video_id:
        return ""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
    except (TranscriptsDisabled, NoTranscriptFound):
        return ""
    except Exception:
        return ""
    return " ".join(_clean_text(item.get("text", "")) for item in transcript if item.get("text"))


def scrape_youtube(url: str) -> dict[str, Any]:
    """Scrape one YouTube URL. Falls back to description when transcript is unavailable."""

    video_id = extract_video_id(url)
    metadata = _fetch_page_metadata(url)
    transcript = _fetch_transcript(video_id)
    fallback_used = not bool(transcript)

    return {
        "source_url": url,
        "source_type": "youtube",
        "video_id": video_id,
        "title": metadata["title"],
        "author": metadata["channel_name"],
        "channel_name": metadata["channel_name"],
        "published_date": metadata["published_date"],
        "description": metadata["description"],
        "content": transcript or metadata["description"],
        "transcript_available": bool(transcript),
        "transcript_fallback_used": fallback_used,
        "citation_count": 0,
        "error": "" if video_id else "missing_video_id",
    }
