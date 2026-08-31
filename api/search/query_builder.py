"""GitHub search query builder.

Assembles a well-formed GitHub search/repositories ``q`` string from
keyword(s) and optional qualifiers, applying sensible defaults so that
results are recent and non-trivial.

Usage::

    from api.search.query_builder import build_github_query, SearchParams

    params = SearchParams(
        keywords=["pdf", "skill"],
        language="python",
        topics=["cli"],
        min_stars=100,
        sort="stars",
    )
    q, sort, order = build_github_query(params)
    # q → "pdf+skill+language:python+topic:cli+stars:>=100+pushed:>=2024-01-01"
    # sort → "stars"
    # order → "desc"
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Defaults (overridable via env for testing / tuning)
# ---------------------------------------------------------------------------

DEFAULT_MIN_STARS = 50
DEFAULT_PUSHED_SINCE = "2024-01-01"
DEFAULT_SORT: Literal["stars", "updated", "best_match"] = "stars"
DEFAULT_PER_PAGE = 30

VALID_SORT = {"stars", "updated", "best_match"}


# ---------------------------------------------------------------------------
# Params dataclass
# ---------------------------------------------------------------------------

@dataclass
class SearchParams:
    """Structured search parameters for the GitHub Repositories Search API."""

    # Required: at least one keyword expected
    keywords: list[str] = field(default_factory=list)

    # Optional qualifiers
    language: str | None = None            # → language:<lang>
    topics: list[str] = field(default_factory=list)   # → topic:<t> …
    min_stars: int | None = None           # → stars:>=N  (overrides default)
    pushed_since: str | None = None        # → pushed:>=YYYY-MM-DD (overrides default)

    # Result control
    sort: str = DEFAULT_SORT               # stars | updated | best_match
    per_page: int = DEFAULT_PER_PAGE       # 1-100


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_github_query(params: SearchParams) -> tuple[str, str, str]:
    """Return (q, sort, order) for the GitHub search/repositories API.

    The returned ``q`` is a ``+``-joined string ready to be URL-encoded:
    - keywords (space-joined → ``+`` separator in q)
    - language:<lang>  (if provided)
    - topic:<topic>    (one per topic, if provided)
    - stars:>=N        (params.min_stars or DEFAULT_MIN_STARS)
    - pushed:>=DATE    (params.pushed_since or DEFAULT_PUSHED_SINCE)

    Returns
    -------
    q : str
        The raw query string (NOT URL-encoded; caller encodes as needed).
    sort : str
        One of "stars", "updated", "best_match".
    order : str
        Always "desc".
    """
    parts: list[str] = []

    # Keywords
    for kw in params.keywords:
        kw = kw.strip()
        if kw:
            parts.append(kw)

    # Language qualifier
    if params.language:
        parts.append(f"language:{params.language.strip()}")

    # Topic qualifiers (one per topic)
    for topic in params.topics:
        topic = topic.strip()
        if topic:
            parts.append(f"topic:{topic}")

    # Stars qualifier — use provided value or default
    min_stars = params.min_stars if params.min_stars is not None else DEFAULT_MIN_STARS
    parts.append(f"stars:>={min_stars}")

    # Pushed qualifier — keep repos updated after date
    pushed_since = params.pushed_since or DEFAULT_PUSHED_SINCE
    parts.append(f"pushed:>={pushed_since}")

    q = "+".join(parts)

    # Sort
    sort = params.sort if params.sort in VALID_SORT else DEFAULT_SORT

    return q, sort, "desc"


def params_to_dict(params: SearchParams) -> dict:
    """Serialise SearchParams to a plain dict (for cache key / snapshot)."""
    return {
        "keywords": sorted(params.keywords),
        "language": params.language,
        "topics": sorted(params.topics),
        "min_stars": params.min_stars,
        "pushed_since": params.pushed_since,
        "sort": params.sort,
        "per_page": params.per_page,
    }
