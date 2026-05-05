"""Trust scoring logic for scraped sources."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import tldextract


TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())
KNOWN_ORGS = {
    "who",
    "world health organization",
    "nih",
    "national institutes of health",
    "cdc",
    "mayo clinic",
    "cleveland clinic",
    "harvard health",
    "johns hopkins",
    "pubmed",
    "ncbi",
}
FAKE_AUTHOR_PATTERNS = [
    r"\badmin\b",
    r"\bguest post\b",
    r"\bseo\b",
    r"\bcontent team\b",
    r"\bwebmaster\b",
    r"\bunknown\b",
]
DISCLAIMER_KEYWORDS = [
    "not medical advice",
    "consult your doctor",
    "consult a doctor",
    "consult a physician",
    "seek medical advice",
    "healthcare professional",
    "qualified medical professional",
]


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _is_known_org(author: str, url: str) -> bool:
    haystack = f"{author} {url}".lower()
    return any(org in haystack for org in KNOWN_ORGS)


def _looks_fake(author: str) -> bool:
    lowered = author.lower()
    return any(re.search(pattern, lowered) for pattern in FAKE_AUTHOR_PATTERNS)


def author_credibility(author: str, url: str = "") -> float:
    if not author:
        return 0.2
    if _is_known_org(author, url):
        return 0.95
    if _looks_fake(author):
        return 0.35

    names = [part.strip() for part in re.split(r",| and |&", author) if part.strip()]
    if len(names) > 1:
        scores = [author_credibility(name, url) for name in names]
        return sum(scores) / len(scores)

    if re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+\b", author):
        return 0.75
    return 0.55


def citation_score(source_type: str, citation_count: int = 0) -> float:
    if source_type == "pubmed":
        return 0.9
    if source_type == "youtube":
        return 0.4
    if source_type == "blog":
        if citation_count >= 20:
            return 0.8
        if citation_count >= 8:
            return 0.65
        if citation_count >= 3:
            return 0.5
        return 0.3
    return 0.3


def domain_authority(url: str, source_type: str = "") -> float:
    if source_type == "pubmed" or "pubmed.ncbi.nlm.nih.gov" in url:
        return 1.0
    if source_type == "youtube" or "youtube.com" in url or "youtu.be" in url:
        return 0.8

    extracted = TLD_EXTRACTOR(url)
    suffix = extracted.suffix.lower()
    domain = extracted.domain.lower()

    if suffix.endswith("gov") or suffix in {"gov.in", "gov.uk"}:
        return 0.95
    if suffix.endswith("edu") or suffix in {"ac.uk", "edu.in"}:
        return 0.9
    if domain in {"medium", "substack"}:
        return 0.65
    if domain in {"nih", "who", "cdc", "mayoclinic", "healthline"}:
        return 0.85
    if domain:
        return 0.45
    return 0.35


def _parse_year_or_date(value: str) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%b %d, %Y", "%Y"):
        try:
            parsed = datetime.strptime(value[:10] if fmt == "%Y-%m-%d" else value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    match = re.search(r"\b(19|20)\d{2}\b", value)
    if match:
        return datetime(int(match.group(0)), 1, 1, tzinfo=timezone.utc)
    return None


def recency_score(published_date: str) -> float:
    parsed = _parse_year_or_date(published_date)
    if not parsed:
        return 0.3
    age_days = (datetime.now(timezone.utc) - parsed).days
    if age_days < 365:
        return 1.0
    if age_days <= 365 * 3:
        return 0.7
    return 0.4


def disclaimer_score(content: str) -> float:
    lowered = content.lower()
    return 1.0 if any(keyword in lowered for keyword in DISCLAIMER_KEYWORDS) else 0.4


def compute_trust_score(item: dict[str, Any]) -> float:
    """Return weighted trust score in the required 0-1 range."""

    content = " ".join(
        str(item.get(key, ""))
        for key in ("content", "abstract", "description", "meta_description")
    )
    score = (
        0.25 * author_credibility(str(item.get("author", "")), str(item.get("source_url", "")))
        + 0.20 * citation_score(str(item.get("source_type", "")), int(item.get("citation_count") or 0))
        + 0.20 * domain_authority(str(item.get("source_url", "")), str(item.get("source_type", "")))
        + 0.20 * recency_score(str(item.get("published_date") or item.get("publication_year") or ""))
        + 0.15 * disclaimer_score(content)
    )
    return round(clamp(score), 3)
