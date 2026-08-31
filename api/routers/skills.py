"""Skills API endpoints."""

import os
import socket
from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
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


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class SkillListResponse(BaseModel):
    """Paginated skill list response."""
    items: list[SkillSummaryOut]
    total: int


class DimensionScores(BaseModel):
    """Eight-dimension score values (null = data not yet available)."""
    task_effect:        float | None = None
    stability:          float | None = None
    trigger_quality:    float | None = None
    permission_privacy: float | None = None
    cost_efficiency:    float | None = None
    platform_compat:    float | None = None
    maintainability:    float | None = None
    doc_explainability: float | None = None


class ScoreEnv(BaseModel):
    """Runtime environment snapshot for the scoring run."""
    host:           str
    model:          str
    client_version: str
    test_date:      str


class SkillScoreOut(BaseModel):
    """GET /api/v1/skills/{id}/scores response (PRD §6.2)."""
    skill_id:       str
    dimensions:     dict[str, float | None] = Field(default_factory=dict)
    composite:      float | None = None
    evidence_level: str = "U"
    sample_size:    int = 0
    uplift:         float | None = None
    env:            ScoreEnv
    status:         str = "UNKNOWN"
    valid_until:    str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

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


def get_skill_by_id(skill_id: str, index: InMemorySkillIndex | None = None) -> dict | None:
    """Get skill detail by ID (reusable helper for other routers).
    
    Args:
        skill_id: Skill identifier
        index: Optional skill index, creates new if None
        
    Returns:
        Scrubbed skill detail dict or None if not found
    """
    if index is None:
        index = get_index()
    
    detail = index.get(skill_id)
    if detail is None:
        return None
    
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
    
    # V1A Task 29.4.3: Add extended fields with defaults
    extended_fields = {
        "evidence_grade_detail": scrubbed_detail.get("summary", {}).get("evidence_grade", "C"),
        "applicable_scenarios": scrubbed_detail.get("applicable_scenarios", []),
        "not_applicable_scenarios": scrubbed_detail.get("not_applicable_scenarios", []),
        "compatibility_status": scrubbed_detail.get("compatibility_status", "Unverified"),
        "compatibility_notes": scrubbed_detail.get("compatibility_notes", ""),
        "static_findings": scrubbed_detail.get("static_findings", []),
        "failure_cases": scrubbed_detail.get("failure_cases", []),
        "test_env": scrubbed_detail.get("test_env", None),
        "source_platforms": scrubbed_detail.get("source_platforms", [scrubbed_detail.get("summary", {}).get("source_kind", "")]),
        # V1E: static detection + dynamic scoring
        "risk_flags": scrubbed_detail.get("risk_flags", []),
        "dynamic_score": scrubbed_detail.get("dynamic_score", None),
    }
    
    return {
        **scrubbed_detail,
        "json_ld": json_ld,
        **extended_fields,
    }


@router.get("/{skill_id}", response_model=SkillDetailOut, responses={404: {"model": ErrorOut}})
def get_skill_detail(
    skill_id: str,
    index: InMemorySkillIndex = Depends(get_index),
):
    """Get skill detail with JSON-LD card."""
    detail = get_skill_by_id(skill_id, index)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    return detail


@router.get("/{skill_id}/scores", response_model=SkillScoreOut,
            responses={404: {"model": ErrorOut}})
def get_skill_scores(skill_id: str):
    """Get 8-dimension composite score for a skill (PRD §6.2).

    Returns the persisted score record if it exists.
    If the skill has never been scored, attempts an on-demand static score.
    """
    from api.db.score_store import get_score
    from api.store.skill_store import get_skill

    env = ScoreEnv(
        host=socket.gethostname(),
        model="static-only",
        client_version="v1f-phase1",
        test_date=datetime.now(timezone.utc).isoformat(),
    )

    # Try stored score first
    stored = get_score(skill_id)

    if stored is None:
        # Try on-demand static scoring
        skill_obj = get_skill(skill_id)
        if skill_obj is None:
            raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

        # Build a minimal static result from skill fields
        from api.scoring.scorer import SkillScorer, get_evidence_level
        from api.scoring.static_check import StaticChecker

        skill_md = ""
        score_result = SkillScorer().score(
            {"skill_id": skill_id, "skill_md": skill_md},
            static_result=None,
            dynamic_result=None,
        )

        # evidence_level U → still return data (not 404) per PRD
        evidence = score_result.evidence_level
        return SkillScoreOut(
            skill_id=skill_id,
            dimensions=score_result.dimensions,
            composite=score_result.composite,
            evidence_level=evidence,
            sample_size=score_result.sample_size,
            uplift=score_result.uplift,
            env=env,
            status=getattr(skill_obj, "status", "UNKNOWN"),
            valid_until=score_result.valid_until,
        )

    evidence = stored.get("evidence_level", "U")
    dimensions = stored.get("dimensions", {})

    # D-level: hide dynamic-dependent dimensions (§6.2)
    if evidence == "D":
        for key in ("task_effect", "stability", "trigger_quality"):
            dimensions[key] = None

    # U-level composite → None already; return the record
    skill_status = "UNKNOWN"
    skill_obj = get_skill(skill_id)
    if skill_obj is not None:
        skill_status = getattr(skill_obj, "status", "UNKNOWN")

    return SkillScoreOut(
        skill_id=skill_id,
        dimensions=dimensions,
        composite=stored.get("composite"),
        evidence_level=evidence,
        sample_size=stored.get("sample_size", 0),
        uplift=stored.get("uplift"),
        env=env,
        status=skill_status,
        valid_until=stored.get("valid_until"),
    )

