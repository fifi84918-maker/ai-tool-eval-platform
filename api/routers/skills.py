"""Skills API endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_index
from api.schemas import SkillSummaryOut, SkillDetailOut, ErrorOut
from mcp_server.index import InMemorySkillIndex
from mcp_server.jsonld import to_json_ld
from mcp_server.policy import scrub

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.get("", response_model=list[SkillSummaryOut])
def search_skills(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip count"),
    index: InMemorySkillIndex = Depends(get_index),
):
    """Search skills with pagination."""
    all_results = index.search(q, limit=limit + offset)
    paginated = all_results[offset:offset + limit]
    return [scrub(s) for s in paginated]


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
    return {
        **scrubbed_detail,
        "json_ld": json_ld,
    }
