"""PubMed HTML scraping utilities."""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT_SECONDS = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TrustScoringScraper/1.0; "
        "+https://example.com/bot)"
    )
}


def _pmid_from_url(url: str) -> str:
    match = re.search(r"/(\d+)/?", url)
    return match.group(1) if match else ""


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _extract_authors(soup: BeautifulSoup) -> list[str]:
    authors = [
        _clean_text(tag.get_text(" "))
        for tag in soup.select(".authors-list .full-name, .authors-list .authors-list-item")
    ]
    cleaned = []
    for author in authors:
        author = re.sub(r"\s+\d+$", "", author).strip()
        if author and author not in cleaned:
            cleaned.append(author)
    return cleaned


def _extract_abstract(soup: BeautifulSoup) -> str:
    abstract_nodes = soup.select(".abstract-content.selected, .abstract-content, #enc-abstract")
    parts = []
    for node in abstract_nodes:
        text = _clean_text(node.get_text(" "))
        if text and text not in parts:
            parts.append(text)
    return "\n\n".join(parts)


def _text(node: ElementTree.Element | None, path: str) -> str:
    if node is None:
        return ""
    found = node.find(path)
    if found is None:
        return ""
    return _clean_text(" ".join(found.itertext()))


def _scrape_pubmed_xml(pmid: str, result: dict[str, Any]) -> dict[str, Any]:
    if not pmid:
        return result

    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={pmid}&retmode=xml"
    )
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    article = root.find(".//Article")
    journal = root.find(".//Journal")

    authors = []
    for author in root.findall(".//AuthorList/Author"):
        last = _text(author, "LastName")
        fore = _text(author, "ForeName")
        collective = _text(author, "CollectiveName")
        name = collective or " ".join(part for part in [fore, last] if part)
        if name:
            authors.append(name)

    abstract_parts = [
        _clean_text(" ".join(node.itertext()))
        for node in root.findall(".//Abstract/AbstractText")
    ]
    abstract = "\n\n".join(part for part in abstract_parts if part)
    year = (
        _text(root, ".//PubDate/Year")
        or _text(root, ".//ArticleDate/Year")
        or _text(root, ".//MedlineDate")
    )
    year_match = re.search(r"\b(19|20)\d{2}\b", year)
    publication_year = year_match.group(0) if year_match else ""

    result.update(
        {
            "title": _text(article, "ArticleTitle"),
            "author": ", ".join(authors),
            "authors": authors,
            "journal": _text(journal, "Title"),
            "published_date": publication_year,
            "publication_year": publication_year,
            "abstract": abstract,
            "content": abstract,
            "citation_count": 1,
            "error": "",
        }
    )
    return result


def scrape_pubmed(url: str) -> dict[str, Any]:
    """Scrape a PubMed article page."""

    result: dict[str, Any] = {
        "source_url": url,
        "source_type": "pubmed",
        "title": "",
        "author": "",
        "authors": [],
        "journal": "",
        "published_date": "",
        "publication_year": "",
        "abstract": "",
        "content": "",
        "citation_count": 1,
        "error": "",
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title_node = soup.select_one("h1.heading-title")
        journal_node = soup.select_one(".journal-actions-trigger")
        citation_node = soup.select_one(".cit")
        year_match = re.search(r"\b(19|20)\d{2}\b", citation_node.get_text(" ") if citation_node else "")
        authors = _extract_authors(soup)
        abstract = _extract_abstract(soup)

        result.update(
            {
                "title": _clean_text(title_node.get_text(" ")) if title_node else "",
                "author": ", ".join(authors),
                "authors": authors,
                "journal": _clean_text(journal_node.get_text(" ")) if journal_node else "",
                "published_date": _clean_text(citation_node.get_text(" ")) if citation_node else "",
                "publication_year": year_match.group(0) if year_match else "",
                "abstract": abstract,
                "content": abstract,
                "citation_count": 1,
            }
        )
    except requests.RequestException as exc:
        result["error"] = f"request_failed: {exc}"
        try:
            return _scrape_pubmed_xml(_pmid_from_url(url), result)
        except Exception as fallback_exc:
            result["error"] = f"{result['error']}; xml_fallback_failed: {fallback_exc}"
    except Exception as exc:
        result["error"] = f"parse_failed: {exc}"

    return result
