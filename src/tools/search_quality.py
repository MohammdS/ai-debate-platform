"""search_quality.py — Domain-tier scoring and debate-focused query building.

Used by WebSearchTool (and optionally TavilySearchTool) to:
  1. Build richer, targeted queries for different evidence needs.
  2. Score retrieved URLs by source credibility (1–3 tiers).
  3. Filter out known low-value domains (forums, social media, SEO spam).
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Domain quality tiers
# ---------------------------------------------------------------------------
_TIER3: frozenset[str] = frozenset({
    ".edu", ".gov", ".ac.uk", ".ac.au",  # Academic / government TLDs
    "nature.com", "science.org", "pubmed.ncbi.nlm.nih.gov",
    "who.int", "un.org", "worldbank.org", "oecd.org",
    "rand.org", "brookings.edu", "pewresearch.org",
    "hbr.org", "mit.edu", "stanford.edu", "harvard.edu",
})

_TIER2: frozenset[str] = frozenset({
    "reuters.com", "bbc.com", "apnews.com", "theguardian.com",
    "nytimes.com", "wsj.com", "economist.com", "ft.com",
    "theatlantic.com", "scientificamerican.com", "wired.com",
    "techcrunch.com", "ieee.org", "acm.org", "arxiv.org",
})

_BLOCKED: frozenset[str] = frozenset({
    "reddit.com", "quora.com", "pinterest.com", "youtube.com",
    "tiktok.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "tumblr.com", "medium.com",  # often low-quality
    "listverse.com", "buzzfeed.com", "thoughtcatalog.com",
    "answers.yahoo.com", "wikianswers.com",
})

_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Adult / explicit content
    re.compile(r"(porn|xxx|xvideos?|xhamster|redtube|onlyfans|hentai)", re.I),
    # Low-signal entertainment/aggregator patterns often returned for "who's better"
    re.compile(r"(athreascans|cloakunfurled|castbox|shazam|visitscotland)", re.I),
    # Generic "who's better" clickbait pages across unrelated topics
    re.compile(r"who['’]?s[-_\s]?better", re.I),
)

_TRUSTED_SPORTS: frozenset[str] = frozenset({
    "uefa.com", "fifa.com", "laliga.com", "premierleague.com",
    "espn.com", "skysports.com", "bbc.com/sport", "reuters.com",
    "theathletic.com", "nytimes.com/athletic", "transfermarkt.com",
    "fbref.com", "whoscored.com", "worldfootball.net",
})

_SPORT_HINTS: tuple[str, ...] = (
    "football", "soccer", "barcelona", "real madrid", "champions league",
    "la liga", "el clasico",
)


def score_domain(url: str) -> int:
    """Return 1 (generic), 2 (reputable news/org), or 3 (academic/government)."""
    url_lower = url.lower()
    if any(d in url_lower for d in _BLOCKED):
        return 0  # filtered out
    if any(d in url_lower for d in _TIER3):
        return 3
    if any(d in url_lower for d in _TIER2):
        return 2
    return 1


def is_blocked(url: str) -> bool:
    """Return True if the URL should be discarded entirely."""
    if score_domain(url) == 0:
        return True
    return any(p.search(url) for p in _BLOCKED_PATTERNS)


def is_allowed_for_topic(url: str, topic: str) -> bool:
    """Topic-aware URL gate.

    For football/soccer topics, only trusted sports/news domains are allowed.
    For other topics, keep existing blocking behavior.
    """
    if is_blocked(url):
        return False
    topic_l = topic.lower()
    if any(h in topic_l for h in _SPORT_HINTS):
        url_l = url.lower()
        return any(d in url_l for d in _TRUSTED_SPORTS)
    return True


# ---------------------------------------------------------------------------
# Query building
# ---------------------------------------------------------------------------
_CURRENT_YEAR = 2025  # update annually or derive from datetime


def build_queries(topic: str, stance: str, round_num: int) -> list[str]:
    """Generate 1–3 targeted queries based on round context.

    Round 1–2  → opening argument support (statistics + authority)
    Round 3–5  → rebuttal fodder (look for counter-evidence / nuanced data)
    Round 6+   → closing strength (expert consensus, meta-analysis)
    """
    base = f'"{_truncate(topic, 60)}" "{_truncate(stance, 50)}"'

    # Always include a primary evidence query
    queries: list[str] = [
        f"{base} evidence research study {_CURRENT_YEAR}",
    ]

    if round_num <= 2:
        queries.append(f"{base} statistics data percentage")
    elif round_num <= 5:
        # Mid-debate: find weaknesses in the opposing side
        queries.append(
            f'"{_truncate(topic, 60)}" limitations drawbacks criticism evidence'
        )
    else:
        # Late debate: expert consensus / meta-analysis
        queries.append(
            f'"{_truncate(topic, 60)}" expert consensus systematic review {_CURRENT_YEAR}'
        )

    return queries


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return text[:limit].rsplit(" ", 1)[0] if len(text) > limit else text
