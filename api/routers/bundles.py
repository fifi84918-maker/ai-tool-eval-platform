"""Bundles API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.schemas import BundleSummaryOut, BundleOut, ErrorOut
from mcp_server.index import InMemoryBundleIndex

router = APIRouter(prefix="/api/v1/bundles", tags=["bundles"])


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
    index: InMemoryBundleIndex = Depends(get_bundle_index),
):
    """List all bundles or search by name/description.
    
    Returns bundle summaries (id, name, description, category) without expanding skill_ids.
    """
    bundles = index.search_bundles(q, limit=limit)
    
    # Convert to summary format
    items = [
        BundleSummaryOut(
            bundle_id=b["bundle_id"],
            name=b["name"],
            description=b["description"],
            category=b["category"],
        )
        for b in bundles
    ]
    
    return BundleListResponse(items=items, total=len(items))


@router.get("/{bundle_id}", response_model=BundleOut, responses={404: {"model": ErrorOut}})
def get_bundle_detail(
    bundle_id: str,
    index: InMemoryBundleIndex = Depends(get_bundle_index),
):
    """Get full bundle details including skill_ids."""
    bundle = index.get_bundle(bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Bundle not found: {bundle_id}")
    
    return BundleOut(
        bundle_id=bundle["bundle_id"],
        name=bundle["name"],
        description=bundle["description"],
        category=bundle["category"],
        skill_ids=list(bundle["skill_ids"]),
        tags=list(bundle["tags"]),
    )


@router.get("/by-skill/{skill_id}", response_model=BundleListResponse)
def get_bundles_by_skill(
    skill_id: str,
    index: InMemoryBundleIndex = Depends(get_bundle_index),
):
    """Get all bundles containing the specified skill.
    
    Returns a list of bundle summaries. If no bundles contain this skill,
    returns an empty list (not a 404).
    """
    all_bundles = index.bundles()
    
    # Filter bundles that contain this skill_id
    matching_bundles = [
        b for b in all_bundles
        if skill_id in b["skill_ids"]
    ]
    
    # Convert to summary format
    items = [
        BundleSummaryOut(
            bundle_id=b["bundle_id"],
            name=b["name"],
            description=b["description"],
            category=b["category"],
        )
        for b in matching_bundles
    ]
    
    return BundleListResponse(items=items, total=len(items))
