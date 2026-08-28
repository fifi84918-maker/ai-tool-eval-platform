"""Skills API endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.deps import get_index
from api.schemas import SkillSummaryOut, SkillDetailOut, ErrorOut
from mcp_server.index import InMemorySkillIndex
from mcp_server.jsonld import to_json_ld
from mcp_server.policy import scrub
from db import SessionLocal
from db.repository import SkillRepository

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


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
):
    """Search skills with pagination and sorting.
    
    When query is empty, returns all skills (default list).
    When query is provided, filters by name/description.
    Supports sorting by score (default) or recent updates.
    """
    # Use database for real pagination and sorting
    with SessionLocal() as session:
        repo = SkillRepository(session)
        skills, total = repo.list_skills(
            query=q if q else None,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
        )
    
    # Add score/grade fields (None if not present) and convert to SkillSummaryOut
    results = []
    for skill in skills:
        if "score_total" not in skill:
            skill["score_total"] = None
        if "grade" not in skill:
            skill["grade"] = None
        results.append(SkillSummaryOut(**skill))
    
    return SkillListResponse(items=results, total=total)


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
