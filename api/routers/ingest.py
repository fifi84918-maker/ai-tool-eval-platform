"""Ingestion API endpoints (Admin/internal use; not for end users)."""
import asyncio
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.routers.skills import get_db
from collector.github_adapter import ingest_from_github
from api.db import list_ingest_runs

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    query: str = "SKILL.md"
    limit: int = 20


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


@router.post("/github", response_model=IngestResponse)
async def ingest_github_sources(request: IngestRequest, db: Session = Depends(get_db)):
    """Ingest GitHub repositories into source_records (Admin/internal use)."""
    report = await ingest_from_github(request.query, request.limit, db)
    return IngestResponse(
        created=report.created,
        updated=report.updated,
        skipped=report.skipped,
        warnings=report.warnings,
    )


@router.get("/runs", response_model=list[IngestRunOut])
def get_ingest_runs(
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
):
    """List ingest run history, most recent first.

    Returns up to `limit` records from the ingest_runs table ordered by
    started_at descending. Each record includes a derived error_count field
    (number of per-source errors collected during that run).
    """
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
