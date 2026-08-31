"""Project Profile API endpoints (SQLite-backed)."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from api.schemas import ProjectProfileCreate, ProjectProfileOut, ErrorOut
from api.db import put_profile, get_profile, list_profiles

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


def _dict_to_profile_out(d: dict) -> ProjectProfileOut:
    return ProjectProfileOut(
        id=d["id"],
        name=d["name"],
        security_requirement=d.get("security_requirement", "standard"),
        languages=d.get("languages", []),
        frameworks=d.get("frameworks", []),
        domains=d.get("domains", []),
        team_size=d.get("team_size"),
        description=d.get("description", ""),
        created_at=d.get("created_at", ""),
    )


@router.post("", response_model=ProjectProfileOut, status_code=201)
def create_profile(profile: ProjectProfileCreate):
    """Create a new project profile (persisted to SQLite)."""
    profile_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()

    data = {
        "id": profile_id,
        "created_at": created_at,
        **profile.model_dump(),
    }
    put_profile(profile_id, data)
    return _dict_to_profile_out(data)


@router.get("", response_model=list[ProjectProfileOut])
def list_profiles_endpoint():
    """Get all project profiles."""
    return [_dict_to_profile_out(d) for d in list_profiles()]


@router.get("/{profile_id}", response_model=ProjectProfileOut, responses={404: {"model": ErrorOut}})
def get_profile_endpoint(profile_id: str):
    """Get a single project profile by ID."""
    d = get_profile(profile_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _dict_to_profile_out(d)
