"""Skills API endpoints."""

import os
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_index
from api.schemas import SkillSummaryOut, SkillDetailOut, ErrorOut
from mcp_server.index import InMemorySkillIndex
from mcp_server.jsonld import to_json_ld
from mcp_server.policy import scrub
from db import SessionLocal
from db.repository import SkillRepository

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


def get_db():
    """Database session dependency (same as eval.py for consistency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SkillListResponse(BaseModel):
    """Paginated skill list response."""
    items: list[SkillSummaryOut]
    total: int


@router.get("", response_model=SkillListResponse)
def search_skills(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip count"),
    sort_by: str = Query("score", description="Sort by: 'score' or 'recent'"),
    index: InMemorySkillIndex = Depends(get_index),
    db: Session = Depends(get_db),
):
    """Search skills with pagination and sorting.
    
    When query is empty, returns all skills (default list).
    When query is provided, filters by name/description.
    Supports sorting by score (default) or recent updates.
    
    Uses InMemorySkillIndex for now (database integration in progress).
    """
    # Use InMemorySkillIndex for compatibility with tests
    # TODO: Migrate to database when skills are persisted
    all_results = index.search(q or "", limit=limit + offset + 100)
    
    # Manual pagination and sorting
    results_list = list(all_results)
    
    # Sort
    if sort_by == "recent":
        # Sort by skill_id as proxy (no updated_at in memory index)
        results_list.sort(key=lambda x: x.get("skill_id", ""), reverse=True)
    else:  # score
        results_list.sort(key=lambda x: x.get("score_total") or 0, reverse=True)
    
    # Paginate
    total = len(results_list)
    paginated = results_list[offset:offset + limit]
    
    # Add score/grade fields and convert to SkillSummaryOut
    items = []
    for skill in paginated:
        scrubbed = scrub(skill)
        if "score_total" not in scrubbed:
            scrubbed["score_total"] = None
        if "grade" not in scrubbed:
            scrubbed["grade"] = None
        items.append(SkillSummaryOut(**scrubbed))
    
    return SkillListResponse(items=items, total=total)


@router.get("/{skill_id}", response_model=SkillDetailOut, responses={404: {"model": ErrorOut}})
def get_skill_detail(
    skill_id: str,
    index: InMemorySkillIndex = Depends(get_index),
):
    """Get skill detail with JSON-LD card."""
    detail = index.get(skill_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    # Generate JSON-LD card
    json_ld = None
    try:
        json_ld = to_json_ld(detail)
    except Exception:
        # Graceful fallback if JSON-LD generation fails
        pass
    
    scrubbed_detail = scrub(detail)
    
    # Ensure summary has score/grade fields
    if "summary" in scrubbed_detail:
        if "score_total" not in scrubbed_detail["summary"]:
            scrubbed_detail["summary"]["score_total"] = None
        if "grade" not in scrubbed_detail["summary"]:
            scrubbed_detail["summary"]["grade"] = None
    
    return {
        **scrubbed_detail,
        "json_ld": json_ld,
    }
