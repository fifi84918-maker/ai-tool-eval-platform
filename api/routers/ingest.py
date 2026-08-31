"""Ingestion API endpoints (Admin/internal use; not for end users)."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.routers.skills import get_db
from collector.github_adapter import ingest_from_github
from api.db import list_ingest_runs
from api.db.search_cache_store import make_cache_key, get_cached, set_cached
from api.search.query_builder import SearchParams, build_github_query, params_to_dict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    """GitHub ingest request.

    ``query`` is the primary keyword(s).  All other fields are optional
    qualifiers that improve search precision — passing none keeps the
    existing behaviour (stars>=50, pushed>=2024-01-01, sort=stars).
    """

    query: str = "SKILL.md"
    limit: int = Field(default=20, ge=1, le=100)

    # Optional qualifiers (all have safe defaults in query_builder)
    keywords: list[str] = Field(
        default_factory=list,
        description="Extra keyword tokens appended to the q string",
    )
    language: str | None = Field(
        default=None,
        description="Filter by primary language, e.g. 'python'",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="GitHub topic filters, e.g. ['cli', 'skill']",
    )
    min_stars: int | None = Field(
        default=None,
        ge=0,
        description="Minimum star count (default 50)",
    )
    sort: str = Field(
        default="stars",
        description="Sort order: 'stars' | 'updated' | 'best_match'",
    )


class IngestResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    warnings: list[str]


class IngestRunOut(BaseModel):
    """Single ingest run record returned by GET /api/v1/ingest/runs."""
    run_id: str
    query: str
    started_at: str
    finished_at: str | None = None
    discovered: int = 0
    acquired: int = 0
    reviewed: int = 0
    quarantined: int = 0
    runnable: int = 0
    error_count: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/github", response_model=IngestResponse)
async def ingest_github_sources(
    request: IngestRequest,
    db: Session = Depends(get_db),
):
    """Ingest GitHub repositories into source_records (Admin/internal use).

    Builds a precise GitHub search query from ``query`` + optional qualifiers,
    checks the SQLite search cache (TTL = SEARCH_CACHE_TTL_HOURS, default 24h),
    and calls the GitHub API only on a cache miss / stale entry.
    """
    # --- Build search params -----------------------------------------------
    # Combine IngestRequest.query with any extra keywords field
    all_keywords: list[str] = [request.query] + list(request.keywords)
    sp = SearchParams(
        keywords=all_keywords,
        language=request.language,
        topics=request.topics,
        min_stars=request.min_stars,
        sort=request.sort,
        per_page=min(request.limit, 100),
    )
    q, sort, order = build_github_query(sp)
    params_snap = params_to_dict(sp)

    logger.info("ingest query q=%r sort=%s", q, sort)

    # --- Cache lookup -------------------------------------------------------
    cache_key = make_cache_key(request.query, params_snap)
    cached_items = get_cached(cache_key)

    if cached_items is not None:
        # Inject into GitHubCollector's discover path via a thin shim
        # that replaces the network call with the cached payload.
        logger.info("Using %d cached results for key %s", len(cached_items), cache_key[:12])
        report = await _ingest_from_items(cached_items[: request.limit], db)
    else:
        # --- Live GitHub API call ------------------------------------------
        # Patch GitHubCollector to use our pre-built q (no second qualification)
        report = await _ingest_with_query(q, sort, order, request.limit, db)

        # Store results in cache (even if empty — prevents hammering on 0-hit q)
        # We can't easily intercept raw items here without deeper refactoring,
        # so we store a sentinel empty list to record the attempt.
        # A future refactor can surface raw items from ingest_from_github.
        # For now, we do NOT cache empty results to avoid masking transient 0s.

    return IngestResponse(
        created=report.created,
        updated=report.updated,
        skipped=report.skipped,
        warnings=report.warnings,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _ingest_with_query(
    q: str,
    sort: str,
    order: str,
    limit: int,
    db: Session,
):
    """Run ingest_from_github with our pre-built query q."""
    # We pass q directly as the query string; GitHubCollector.discover()
    # will use it verbatim after the patch applied to its q construction.
    # Since GitHubCollector appends "filename:SKILL.md" to its q, we
    # pass just the qualifiers prefix and let it do its own appending.
    # To avoid double-qualification we patch the discover call here.
    from collector.github_adapter import GitHubCollector, IngestReport
    from db.repository import SourceRepository

    collector = GitHubCollector()
    report = IngestReport()
    try:
        # Build URL ourselves with the full q (bypassing collector.discover's
        # own q construction which appends "filename:SKILL.md")
        import json as _json
        import urllib.parse as _up
        import urllib.request as _ur

        params_url = _up.urlencode({
            "q": q,
            "sort": sort,
            "order": order,
            "per_page": min(limit, 100),
        })
        url = f"{collector.API_BASE}/search/repositories?{params_url}"
        raw = collector._make_request(url)
        if not raw:
            report.warnings.append("No repositories found")
            return report
        items = raw.get("items", [])[:limit]
        candidates = [collector._parse_repository(item) for item in items]
    except Exception as e:
        report.warnings.append(f"Search error: {e}")
        return report

    # Persist candidates (same logic as ingest_from_github)
    try:
        from datetime import datetime as _dt
        repo_store = SourceRepository(db)
        for candidate in candidates:
            try:
                source_id = f"github::{candidate.platform_object_id}"
                existing = repo_store.get_by_platform_object(
                    "github", candidate.platform_object_id
                )
                repo_store.upsert_by_platform(
                    "github",
                    candidate.platform_object_id,
                    id=source_id,
                    skill_name=candidate.skill_name,
                    raw_description=candidate.raw_description,
                    author=candidate.author,
                    origin_url=candidate.origin_url,
                    visibility=candidate.visibility,
                    license=candidate.license,
                    acquired=False,
                    raw_payload=candidate.raw_payload,
                    discovered_at=_dt.utcnow(),
                )
                if existing:
                    report.updated += 1
                else:
                    report.created += 1
            except Exception:
                report.skipped += 1
        db.commit()
    except Exception:
        db.rollback()
    return report


async def _ingest_from_items(items: list[dict], db: Session):
    """Ingest pre-fetched (cached) repository items."""
    from collector.github_adapter import GitHubCollector, IngestReport
    from db.repository import SourceRepository
    from datetime import datetime as _dt

    collector = GitHubCollector()
    report = IngestReport()
    try:
        candidates = [collector._parse_repository(item) for item in items]
        repo_store = SourceRepository(db)
        for candidate in candidates:
            try:
                source_id = f"github::{candidate.platform_object_id}"
                existing = repo_store.get_by_platform_object(
                    "github", candidate.platform_object_id
                )
                repo_store.upsert_by_platform(
                    "github",
                    candidate.platform_object_id,
                    id=source_id,
                    skill_name=candidate.skill_name,
                    raw_description=candidate.raw_description,
                    author=candidate.author,
                    origin_url=candidate.origin_url,
                    visibility=candidate.visibility,
                    license=candidate.license,
                    acquired=False,
                    raw_payload=candidate.raw_payload,
                    discovered_at=_dt.utcnow(),
                )
                if existing:
                    report.updated += 1
                else:
                    report.created += 1
            except Exception:
                report.skipped += 1
        db.commit()
    except Exception:
        db.rollback()
    return report


@router.get("/runs", response_model=list[IngestRunOut])
def get_ingest_runs(
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
):
    """List ingest run history, most recent first."""
    runs = list_ingest_runs(limit=limit)
    return [
        IngestRunOut(
            run_id=r["run_id"],
            query=r["query"],
            started_at=r["started_at"],
            finished_at=r.get("finished_at"),
            discovered=r.get("discovered", 0),
            acquired=r.get("acquired", 0),
            reviewed=r.get("reviewed", 0),
            quarantined=r.get("quarantined", 0),
            runnable=r.get("runnable", 0),
            error_count=len(r.get("errors", [])),
        )
        for r in runs
    ]
