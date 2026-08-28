"""Bundles API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.schemas import BundleSummaryOut, BundleOut, ErrorOut, BundleRecommendRequest
from mcp_server.index import InMemoryBundleIndex

router = APIRouter(prefix="/api/v1/bundles", tags=["bundles"])


# V1A Task 29.4.5: Tiered bundles storage (in-memory, no database)
# Skill IDs from mcp_server/index.py line 348-352
SKILL_ID_DOC = "219c93e5365609e6060c9afe1d88571324b4fff1a518f16f75353b0cab159733"  # S1-green (safe)
SKILL_ID_LOOSE = "0766e96cdeb4121ba7aeac64bcc1fe4a0ab46563a70805f0d2d0767b19eb8e31"  # S2-no-skillmd
SKILL_ID_CLEANER = "ebadf9efabceaa60a7a24e385ffed84b288ec017f62848b3485494beadfcbe96"  # S3-highrisk-perms (warning)
SKILL_ID_UNKNOWN = "b52777c216938ecaaf75d14393419ebb21d752d6f3bd2954e33bbf7a42485d88"  # S4-d008-rights
SKILL_ID_LEAKY = "c2025e6a6d0d23aa57da5beb1fd95ceb65cc6c52e4caaca6ed0a213508ea7dd7"  # S5-secrets (block)

_tiered_bundles: dict[str, BundleOut] = {
    "bundle-starter": BundleOut(
        bundle_id="bundle-starter",
        name="入门套装 (Starter)",
        description="快速上手，零配置，适合个人项目和学习",
        category="starter",
        tier="starter",
        skill_ids=[SKILL_ID_DOC, SKILL_ID_LOOSE],  # 2 safe skills
        tags=["documentation", "development", "beginner"],
        target_domains=["documentation", "development"],
        required_languages=["python"],
        security_level="lax",
        highlights=["快速上手", "零配置", "适合学习"],
        skill_count=2,
    ),
    "bundle-standard": BundleOut(
        bundle_id="bundle-standard",
        name="标准套装 (Standard)",
        description="平衡功能与安全，覆盖主要开发场景",
        category="standard",
        tier="standard",
        skill_ids=[SKILL_ID_DOC, SKILL_ID_LOOSE, SKILL_ID_CLEANER],  # 3 skills (1 with warning)
        tags=["documentation", "development", "productivity", "standard"],
        target_domains=["documentation", "development", "productivity"],
        required_languages=["python", "typescript"],
        security_level="standard",
        highlights=["平衡功能与安全", "覆盖主要场景", "企业可用"],
        skill_count=3,
    ),
    "bundle-enterprise": BundleOut(
        bundle_id="bundle-enterprise",
        name="企业套装 (Enterprise)",
        description="完整覆盖，含安全审计，适合严格安全要求",
        category="enterprise",
        tier="enterprise",
        skill_ids=[SKILL_ID_DOC, SKILL_ID_LOOSE, SKILL_ID_CLEANER, SKILL_ID_UNKNOWN, SKILL_ID_LEAKY],  # All 5
        tags=["documentation", "development", "productivity", "security", "enterprise"],
        target_domains=["documentation", "development", "productivity", "security"],
        required_languages=["python", "typescript", "go"],
        security_level="strict",
        highlights=["完整覆盖", "含安全审计", "严格权限管理"],
        skill_count=5,
    ),
}


def get_bundle_index():
    """Bundle index dependency."""
    return InMemoryBundleIndex()


class BundleListResponse(BaseModel):
    """Bundle list response."""
    items: list[BundleSummaryOut]
    total: int


@router.get("", response_model=BundleListResponse)
def list_bundles(
    q: str = Query("", description="Search query for bundle name/description"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    """List all tiered bundles or search by name/description.
    
    Returns tiered bundle summaries (starter/standard/enterprise).
    """
    # V1A 29.4.5: Return tiered bundles instead of old InMemoryBundleIndex
    all_bundles = list(_tiered_bundles.values())
    
    # Simple search filter
    if q:
        q_lower = q.lower()
        all_bundles = [
            b for b in all_bundles
            if q_lower in b.name.lower() or q_lower in b.description.lower()
        ]
    
    # Apply limit
    bundles = all_bundles[:limit]
    
    # Convert to summary format
    items = [
        BundleSummaryOut(
            bundle_id=b.bundle_id,
            name=b.name,
            description=b.description,
            category=b.category,
            tier=b.tier,
        )
        for b in bundles
    ]
    
    return BundleListResponse(items=items, total=len(items))


@router.get("/{bundle_id}", response_model=BundleOut, responses={404: {"model": ErrorOut}})
def get_bundle_detail(bundle_id: str):
    """Get full tiered bundle details including skill_ids."""
    bundle = _tiered_bundles.get(bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@router.get("/by-skill/{skill_id}", response_model=BundleListResponse)
def get_bundles_by_skill(skill_id: str):
    """Get all tiered bundles containing the specified skill.
    
    Returns a list of bundle summaries. If no bundles contain this skill,
    returns an empty list (not a 404).
    """
    all_bundles = list(_tiered_bundles.values())
    
    # Filter bundles that contain this skill_id
    matching_bundles = [
        b for b in all_bundles
        if skill_id in b.skill_ids
    ]
    
    # Convert to summary format
    items = [
        BundleSummaryOut(
            bundle_id=b.bundle_id,
            name=b.name,
            description=b.description,
            category=b.category,
            tier=b.tier,
        )
        for b in matching_bundles
    ]
    
    return BundleListResponse(items=items, total=len(items))


@router.post("/recommend", response_model=BundleListResponse)
def recommend_bundles(request: BundleRecommendRequest):
    """Recommend bundles based on project profile.
    
    Recommendation logic:
    1. Filter by security_requirement:
       - "strict" → only enterprise
       - "standard" → enterprise + standard
       - "lax" → all three tiers
    2. Score by domain/language overlap with request
    3. Sort by score (descending)
    
    Returns ranked list of matching bundles.
    """
    all_bundles = list(_tiered_bundles.values())
    
    # Step 1: Filter by security level
    security_req = request.security_requirement.lower()
    if security_req == "strict":
        candidates = [b for b in all_bundles if b.tier == "enterprise"]
    elif security_req == "standard":
        candidates = [b for b in all_bundles if b.tier in ("enterprise", "standard")]
    else:  # lax
        candidates = all_bundles
    
    # Step 2: Score by overlap
    def score_bundle(bundle: BundleOut) -> int:
        score = 0
        # Domain overlap
        domain_overlap = len(set(request.domains) & set(bundle.target_domains))
        score += domain_overlap * 10
        
        # Language overlap
        lang_overlap = len(set(request.languages) & set(bundle.required_languages))
        score += lang_overlap * 5
        
        return score
    
    # Step 3: Sort by score
    scored_bundles = [(bundle, score_bundle(bundle)) for bundle in candidates]
    scored_bundles.sort(key=lambda x: x[1], reverse=True)
    
    # Convert to summary format
    items = [
        BundleSummaryOut(
            bundle_id=b.bundle_id,
            name=b.name,
            description=b.description,
            category=b.category,
            tier=b.tier,
        )
        for b, score in scored_bundles
    ]
    
    return BundleListResponse(items=items, total=len(items))
