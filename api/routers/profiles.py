"""Project Profile API endpoints."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from api.schemas import ProjectProfileCreate, ProjectProfileOut, ErrorOut

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])

# In-memory storage (no database table for now)
_profiles: dict[str, ProjectProfileOut] = {}


@router.post("", response_model=ProjectProfileOut, status_code=201)
def create_profile(profile: ProjectProfileCreate):
    """Create a new project profile.
    
    Returns 201 Created with the new profile including generated ID and timestamp.
    """
    profile_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    
    profile_out = ProjectProfileOut(
        id=profile_id,
        created_at=created_at,
        **profile.model_dump()
    )
    
    _profiles[profile_id] = profile_out
    return profile_out


@router.get("", response_model=list[ProjectProfileOut])
def list_profiles():
    """Get all project profiles.
    
    Returns a list of all stored profiles.
    """
    return list(_profiles.values())


@router.get("/{profile_id}", response_model=ProjectProfileOut, responses={404: {"model": ErrorOut}})
def get_profile(profile_id: str):
    """Get a single project profile by ID.
    
    Returns 404 if the profile does not exist.
    """
    profile = _profiles.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
