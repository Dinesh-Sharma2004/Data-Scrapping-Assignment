# Multi-Source Scraping and Trust Scoring

Production-ready Python project for scraping structured content from blogs, YouTube videos, and PubMed articles, then normalizing, tagging, chunking, scoring, and saving the results as JSON.

## Project Structure

```text
project/
├── scraper/
│   ├── blog_scraper.py
│   ├── youtube_scraper.py
│   └── pubmed_scraper.py
├── scoring/
│   └── trust_score.py
├── utils/
│   ├── tagging.py
│   ├── chunking.py
│   └── language.py
├── data/
│   └── urls.json
├── output/
│   └── scraped_data.json
├── main.py
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.10+ is recommended.

## Run

```bash
python main.py
```

The pipeline reads `data/urls.json` and writes normalized results to `output/scraped_data.json`.

## Test

```bash
python tests/smoke_test.py
```

The smoke test validates URL parsing, language and region detection, chunking, topic tagging, and trust score bounds.

## Libraries Used

- `requests` for HTTP requests
- `beautifulsoup4` for HTML parsing
- `youtube-transcript-api` for YouTube transcripts
- `langdetect` for language detection
- `scikit-learn` for TF-IDF topic tagging
- `tldextract` for domain and region heuristics
- Standard `datetime`, `json`, and `re`

## Scraping Approach

The blog scraper removes scripts, styles, navigation, headers, footers, sidebars, and forms. It prefers `<article>`, then `<main>`, then common content containers, and extracts title, author, publish date, meta description, content, and link count.

The YouTube scraper extracts the video id, page metadata, channel name, publish date, description, and transcript. If a transcript is disabled or missing, it falls back to the description.

The PubMed scraper parses PubMed HTML for title, authors, journal, abstract, publication year, and citation text.

## Output Schema

Each source is saved as:

```json
{
  "source_url": "",
  "source_type": "",
  "author": "",
  "published_date": "",
  "language": "",
  "region": "",
  "topic_tags": [],
  "trust_score": 0.0,
  "content_chunks": []
}
```

## Processing

Language detection uses `langdetect` and returns `unknown` if detection fails. Region detection uses top-level domains such as `.in`, `.us`, and `.uk`, with `global` as the fallback.

Topic tagging uses TF-IDF over unigrams and bigrams, then normalizes common concepts such as AI, machine learning, healthcare, medicine, and clinical research.

Content chunking is paragraph-aware and produces chunks of roughly 200 to 300 words when enough text is available.

## Trust Score

The trust score is a weighted average:

```text
0.25 * author_credibility
+ 0.20 * citation_count
+ 0.20 * domain_authority
+ 0.20 * recency
+ 0.15 * medical_disclaimer_presence
```

Component rules:

- Author credibility: known organizations score highest; named individuals score medium-high; fake or generic authors are penalized; missing authors score low.
- Citation count: PubMed is high by default, blogs use link count as an estimate, and YouTube is lower.
- Domain authority: PubMed, `.gov`, and `.edu` score high; YouTube is strong; Medium/Substack are moderate; unknown domains are lower.
- Recency: under one year scores `1.0`; one to three years scores `0.7`; older content scores `0.4`; missing dates score `0.3`.
- Medical disclaimer: content with terms such as "not medical advice" or "consult a doctor" scores `1.0`; otherwise it scores `0.4`.

The final score is clamped between `0` and `1`.

## Abuse Prevention Logic

The system does not treat scraped content as trustworthy just because it was successfully collected. It applies several manipulation-resistant checks inside `scoring/trust_score.py`.

### Fake Authors

Author credibility is scored with conservative rules:

- Known medical or scientific organizations such as WHO, NIH, CDC, Mayo Clinic, and PubMed score high.
- Named individuals score medium-high.
- Generic or suspicious authors such as `admin`, `guest post`, `SEO`, `content team`, `webmaster`, and `unknown` are penalized.
- Missing authors receive a low score.
- Multiple authors are split and averaged instead of blindly giving full credit.

This prevents low-quality pages from gaining trust simply by using vague or fake bylines.

### SEO Spam Blogs

Domain authority is estimated with `tldextract` and source-specific heuristics:

- PubMed receives the highest authority.
- `.gov` and `.edu` domains score high.
- YouTube receives moderate-high authority because it is a known platform, but the video still depends on author, date, and disclaimer checks.
- Medium/Substack-style blogs are treated as moderate authority.
- Unknown domains receive low authority.

This reduces the score of SEO-driven blogs or unfamiliar domains even when they contain many keywords.

### Misleading Medical Content

Medical or health content is penalized if it does not include safety language such as:

- `not medical advice`
- `consult your doctor`
- `consult a physician`
- `seek medical advice`
- `healthcare professional`

Content with a disclaimer receives a higher disclaimer component. Content without one receives a penalty, which helps reduce trust in pages that make health claims without appropriate caution.

### Outdated Information

Recency is scored from the publish date:

- Less than 1 year old: `1.0`
- 1 to 3 years old: `0.7`
- More than 3 years old: `0.4`
- Missing date: `0.3`

This strongly penalizes old or undated information, which is especially important for healthcare, AI, and research topics where guidance changes quickly.

### Combined Protection

The final trust score uses a weighted average:

```text
0.25 * author_credibility
+ 0.20 * citation_count
+ 0.20 * domain_authority
+ 0.20 * recency
+ 0.15 * medical_disclaimer_presence
```

Because the score combines multiple signals, a page cannot easily manipulate the final result with only one strong signal. For example, a keyword-stuffed blog with a named author can still score poorly if it comes from a weak domain, lacks citations, has no medical disclaimer, or is outdated.

## Limitations

Scraping depends on public page structure and availability. Some sites block bots, change markup frequently, or require JavaScript. YouTube transcripts may be disabled. Link count is only an estimate for citations on blogs. The trust score is heuristic and should support review, not replace expert judgment.
