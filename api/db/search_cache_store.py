"""SQLite-backed search result cache for GitHub API queries.

Cache strategy
--------------
- Key: sha256 of normalised (query, qualifiers) — order-independent.
- TTL: SEARCH_CACHE_TTL_HOURS env var (default 24).
- Hit: same key exists and fetched_at is within TTL → return cached items.
- Miss/stale: fetch from API, upsert row.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta

from api.db.database import get_conn, _json_loads_safe

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL
# ---------------------------------------------------------------------------

def _ttl_hours() -> float:
    """Return cache TTL in hours from env (default 24)."""
    try:
        return float(os.environ.get("SEARCH_CACHE_TTL_HOURS", "24"))
    except (ValueError, TypeError):
        return 24.0


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------

def make_cache_key(query: str, params: dict) -> str:
    """Produce a stable sha256 hex key from query + sorted params snapshot.

    Params dict is normalised: keys sorted, list values sorted so that
    keywords=['pdf','skill'] and keywords=['skill','pdf'] produce the same key.
    """
    normalised = {"query": query.strip().lower()}
    for k, v in sorted(params.items()):
        if isinstance(v, list):
            normalised[k] = sorted(str(x) for x in v)
        elif v is not None:
            normalised[k] = str(v)
    payload = json.dumps(normalised, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_cached(cache_key: str) -> list[dict] | None:
    """Return cached items if the entry exists and is within TTL, else None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT results_json, fetched_at FROM search_cache WHERE cache_key = ?",
        (cache_key,),
    ).fetchone()

    if row is None:
        logger.debug("search_cache miss: %s", cache_key[:12])
        return None

    fetched_at_str = dict(row)["fetched_at"]
    try:
        fetched_at = datetime.fromisoformat(fetched_at_str)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    except ValueError:
        logger.debug("search_cache bad timestamp, treating as miss")
        return None

    age = datetime.now(timezone.utc) - fetched_at
    ttl = timedelta(hours=_ttl_hours())

    if age > ttl:
        logger.info(
            "search_cache stale (age=%.1fh, ttl=%.1fh): %s",
            age.total_seconds() / 3600,
            _ttl_hours(),
            cache_key[:12],
        )
        return None

    logger.info(
        "search_cache hit (age=%.1fh): %s",
        age.total_seconds() / 3600,
        cache_key[:12],
    )
    return _json_loads_safe(dict(row)["results_json"], [])


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def set_cached(
    cache_key: str,
    query: str,
    params: dict,
    items: list[dict],
    total_count: int | None = None,
    incomplete_results: bool = False,
) -> None:
    """Upsert a cache entry."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO search_cache
            (cache_key, query, params_json, results_json,
             total_count, incomplete_results, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            query              = excluded.query,
            params_json        = excluded.params_json,
            results_json       = excluded.results_json,
            total_count        = excluded.total_count,
            incomplete_results = excluded.incomplete_results,
            fetched_at         = excluded.fetched_at
        """,
        (
            cache_key,
            query,
            json.dumps(params, sort_keys=True),
            json.dumps(items),
            total_count,
            int(incomplete_results),
            now,
        ),
    )
    conn.commit()
    logger.info("search_cache stored %d items: %s", len(items), cache_key[:12])


# ---------------------------------------------------------------------------
# Test helper
# ---------------------------------------------------------------------------

def clear_search_cache() -> None:
    """Delete all cache rows (used in tests)."""
    conn = get_conn()
    conn.execute("DELETE FROM search_cache")
    conn.commit()
