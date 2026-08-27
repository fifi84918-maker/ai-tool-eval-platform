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
    """Search skills with pagination.
    
    When query is empty, returns all skills (default list).
    When query is provided, filters by name/description.
    """
    # Empty query: return default list (all skills)
    # Non-empty query: filter results
    all_results = index.search(q or "", limit=limit + offset)
    paginated = all_results[offset:offset + limit]
    
    # Add score/grade fields (None if not present)
    results = []
    for skill in paginated:
        scrubbed = scrub(skill)
        if "score_total" not in scrubbed:
            scrubbed["score_total"] = None
        if "grade" not in scrubbed:
            scrubbed["grade"] = None
        results.append(scrubbed)
    
    return results


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
