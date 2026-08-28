"""Recommendation generation API endpoints (V1A Task 29.4.6/29.4.7)."""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.schemas import (
    ProjectProfileCreate,
    ProjectProfileBase,
    RecommendationResponse,
    BundleRecommendationOut,
    RecommendedSkillOut,
    ErrorOut,
)
from api.routers.bundles import _tiered_bundles
from api.routers.profiles import _profiles
from api.routers.skills import get_skill_by_id

router = APIRouter(prefix="/api/v1/recommend", tags=["recommendation"])


# V1A Task 29.4.7: Recommendation history storage (in-memory, max 20 entries)
_history: list[dict] = []
MAX_HISTORY = 20


class HistoryResponse(BaseModel):
    """推荐历史响应。"""
    total: int
    items: list[dict]


def generate_recommendations(
    profile: ProjectProfileBase,
    profile_id: str | None = None,
    profile_name: str | None = None,
) -> RecommendationResponse:
    """Generate bundle recommendations based on project profile.
    
    Args:
        profile: Project profile (inline or from storage)
        profile_id: Optional profile ID for response
        profile_name: Optional profile name for response
        
    Returns:
        RecommendationResponse with ranked bundles and expanded skills
    """
    all_bundles = list(_tiered_bundles.values())
    
    # Step 1: Filter by security level
    security_req = profile.security_requirement.lower()
    if security_req == "strict":
        candidates = [b for b in all_bundles if b.tier == "enterprise"]
    elif security_req == "standard":
        candidates = [b for b in all_bundles if b.tier in ("enterprise", "standard")]
    else:  # lax
        candidates = all_bundles
    
    # Step 2 & 3: Score and generate match reasons
    scored_bundles = []
    for bundle in candidates:
        # Calculate score
        domain_overlap = set(profile.domains) & set(bundle.target_domains)
        language_overlap = set(profile.languages) & set(bundle.required_languages)
        score = len(domain_overlap) * 10 + len(language_overlap) * 5
        
        # Generate match reasons
        match_reasons = []
        
        # Security match
        match_reasons.append(f"满足 {profile.security_requirement} 安全要求")
        
        # Domain matches
        for domain in domain_overlap:
            match_reasons.append(f"覆盖领域：{domain}")
        
        # Language matches
        for lang in language_overlap:
            match_reasons.append(f"匹配语言：{lang}")
        
        # Step 4: Expand skills
        skills = []
        for skill_id in bundle.skill_ids:
            try:
                skill_detail = get_skill_by_id(skill_id)
                if skill_detail and "summary" in skill_detail:
                    summary = skill_detail["summary"]
                    # Extract metrics if available
                    metrics = {}
                    if "metrics" in skill_detail:
                        m = skill_detail["metrics"]
                        if isinstance(m, dict):
                            metrics = {
                                k: v for k, v in m.items()
                                if k in ("accuracy", "reliability", "security", "performance")
                            }
                    
                    skills.append(
                        RecommendedSkillOut(
                            skill_id=summary["skill_id"],
                            name=summary.get("canonical_name", "Unknown"),
                            grade=summary.get("grade"),
                            score_total=summary.get("score_total"),
                            metrics=metrics,
                        )
                    )
            except Exception:
                # Skip skills that fail to load (e.g., during index initialization)
                continue
        
        scored_bundles.append((bundle, score, match_reasons, skills))
    
    # Step 5: Sort by score descending, then by tier priority (starter first)
    tier_priority = {"starter": 1, "standard": 2, "enterprise": 3}
    scored_bundles.sort(
        key=lambda x: (-x[1], tier_priority.get(x[0].tier, 99))
    )
    
    # Step 6: Build response
    items = [
        BundleRecommendationOut(
            bundle_id=bundle.bundle_id,
            name=bundle.name,
            tier=bundle.tier,
            description=bundle.description,
            security_level=bundle.security_level,
            highlights=bundle.highlights,
            score=score,
            match_reasons=reasons,
            skills=skills,
        )
        for bundle, score, reasons, skills in scored_bundles
    ]
    
    return RecommendationResponse(
        profile_id=profile_id,
        profile_name=profile_name,
        total=len(items),
        items=items,
    )


@router.post("", response_model=RecommendationResponse)
def recommend_inline(profile: ProjectProfileCreate):
    """Generate recommendations from inline profile (no storage).
    
    Accepts a project profile directly in the request body and returns
    recommendations without storing the profile.
    """
    response = generate_recommendations(profile, profile_id=None, profile_name=None)
    
    # V1A Task 29.4.7: Record to history
    _record_history(
        profile_id=None,
        profile_name=profile.name,
        response=response,
    )
    
    return response


@router.post("/{profile_id}", response_model=RecommendationResponse, responses={404: {"model": ErrorOut}})
def recommend_by_profile_id(profile_id: str):
    """Generate recommendations from stored profile.
    
    Retrieves the profile by ID from storage and generates recommendations.
    Returns 404 if the profile does not exist.
    """
    profile = _profiles.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    response = generate_recommendations(
        profile,
        profile_id=profile.id,
        profile_name=profile.name,
    )
    
    # V1A Task 29.4.7: Record to history
    _record_history(
        profile_id=profile.id,
        profile_name=profile.name,
        response=response,
    )
    
    return response


def _record_history(profile_id: str | None, profile_name: str, response: RecommendationResponse):
    """Record a recommendation to history (internal helper)."""
    global _history
    
    # Create history entry
    entry = {
        "profile_id": profile_id,
        "profile_name": profile_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response": response.model_dump(),
    }
    
    # Append and trim to max size
    _history.append(entry)
    if len(_history) > MAX_HISTORY:
        _history.pop(0)


@router.get("/history", response_model=HistoryResponse)
def get_recommendation_history():
    """Get all recommendation history (most recent 20 entries)."""
    return HistoryResponse(total=len(_history), items=_history)


@router.get("/history/{profile_id}", response_model=HistoryResponse, responses={404: {"model": ErrorOut}})
def get_recommendation_history_by_profile(profile_id: str):
    """Get recommendation history for a specific profile.
    
    Returns all history entries for the given profile_id.
    Returns 404 if no history exists for this profile.
    """
    matching = [entry for entry in _history if entry["profile_id"] == profile_id]
    
    if not matching:
        raise HTTPException(status_code=404, detail="No recommendation history for profile")
    
    return HistoryResponse(total=len(matching), items=matching)
