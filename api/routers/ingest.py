"""Ingestion API endpoints (Admin/internal use; not for end users)."""
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.routers.skills import get_db
from collector.github_adapter import ingest_from_github
router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])
class IngestRequest(BaseModel):
    query: str = "SKILL.md"
    limit: int = 20
class IngestResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    warnings: list[str]
@router.post("/github", response_model=IngestResponse)
async def ingest_github_sources(request: IngestRequest, db: Session = Depends(get_db)):
    """Ingest GitHub repositories into source_records (Admin/internal use)."""
    report = await ingest_from_github(request.query, request.limit, db)
    return IngestResponse(created=report.created, updated=report.updated, skipped=report.skipped, warnings=report.warnings)