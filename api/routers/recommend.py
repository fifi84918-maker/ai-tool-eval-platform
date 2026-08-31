"""Recommendation generation API endpoints (SQLite-backed history)."""

import json
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
from api.routers.skills import get_skill_by_id
from api.rules import RuleEngine, BUILTIN_RULES
from api.db import (
    get_profile,
    append_recommend_history,
    list_recommend_history,
)

router = APIRouter(prefix="/api/v1/recommend", tags=["recommendation"])


class HistoryResponse(BaseModel):
    """推荐历史响应。"""
    total: int
    items: list[dict]


def generate_recommendations(
    profile: ProjectProfileBase,
    profile_id: str | None = None,
    profile_name: str | None = None,
) -> RecommendationResponse:
    """Generate bundle recommendations based on project profile."""
    all_bundles = list(_tiered_bundles.values())

    engine = RuleEngine(BUILTIN_RULES)

    scored_bundles = []
    for bundle in all_bundles:
        rule_result = engine.evaluate(profile, bundle)

        if rule_result.filtered:
            continue

        score = rule_result.score_adjustment

        match_reasons = [f"满足 {profile.security_requirement} 安全要求"]
        for violation in rule_result.violations:
            if violation.severity == "info":
                match_reasons.append(violation.message)

        skills = []
        for skill_id in bundle.skill_ids:
            try:
                skill_detail = get_skill_by_id(skill_id)
                if skill_detail and "summary" in skill_detail:
                    summary = skill_detail["summary"]
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
                continue

        rule_findings = [v.model_dump() for v in rule_result.violations]
        scored_bundles.append((bundle, score, match_reasons, skills, rule_findings))

    tier_priority = {"starter": 1, "standard": 2, "enterprise": 3}
    scored_bundles.sort(key=lambda x: (-x[1], tier_priority.get(x[0].tier, 99)))

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
            rule_findings=findings,
        )
        for bundle, score, reasons, skills, findings in scored_bundles
    ]

    return RecommendationResponse(
        profile_id=profile_id,
        profile_name=profile_name,
        total=len(items),
        items=items,
    )


def _record_history(
    profile_id: str | None,
    profile_name: str,
    response: RecommendationResponse,
) -> None:
    """Persist a recommendation response to the SQLite history table."""
    timestamp = datetime.now(timezone.utc).isoformat()
    append_recommend_history(
        profile_id=profile_id,
        profile_name=profile_name,
        timestamp=timestamp,
        response_json=json.dumps(response.model_dump()),
    )


@router.post("", response_model=RecommendationResponse)
def recommend_inline(profile: ProjectProfileCreate):
    """Generate recommendations from inline profile (no storage)."""
    response = generate_recommendations(profile, profile_id=None, profile_name=None)
    _record_history(profile_id=None, profile_name=profile.name, response=response)
    return response


@router.post("/{profile_id}", response_model=RecommendationResponse, responses={404: {"model": ErrorOut}})
def recommend_by_profile_id(profile_id: str):
    """Generate recommendations from stored profile."""
    d = get_profile(profile_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Reconstruct a ProjectProfileCreate from stored dict
    profile = ProjectProfileCreate(
        name=d["name"],
        security_requirement=d.get("security_requirement", "standard"),
        languages=d.get("languages", []),
        frameworks=d.get("frameworks", []),
        domains=d.get("domains", []),
        team_size=d.get("team_size"),
        description=d.get("description", ""),
    )

    response = generate_recommendations(
        profile,
        profile_id=profile_id,
        profile_name=d["name"],
    )
    _record_history(profile_id=profile_id, profile_name=d["name"], response=response)
    return response


@router.get("/history", response_model=HistoryResponse)
def get_recommendation_history():
    """Get all recommendation history (most recent 20 entries)."""
    items = list_recommend_history()
    return HistoryResponse(total=len(items), items=items)


@router.get("/history/{profile_id}", response_model=HistoryResponse, responses={404: {"model": ErrorOut}})
def get_recommendation_history_by_profile(profile_id: str):
    """Get recommendation history for a specific profile."""
    items = list_recommend_history(profile_id=profile_id)
    if not items:
        raise HTTPException(status_code=404, detail="No recommendation history for profile")
    return HistoryResponse(total=len(items), items=items)
