"""Language and region inference utilities."""

from __future__ import annotations

from langdetect import LangDetectException, detect
import tldextract


TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())
REGION_BY_SUFFIX = {
    "in": "India",
    "co.in": "India",
    "us": "United States",
    "uk": "United Kingdom",
    "co.uk": "United Kingdom",
    "ca": "Canada",
    "au": "Australia",
    "de": "Germany",
    "fr": "France",
    "jp": "Japan",
}


def detect_language(text: str) -> str:
    try:
        return detect(text) if text and text.strip() else "unknown"
    except LangDetectException:
        return "unknown"


def detect_region(url: str) -> str:
    extracted = TLD_EXTRACTOR(url)
    suffix = extracted.suffix.lower()
    return REGION_BY_SUFFIX.get(suffix, "global")
