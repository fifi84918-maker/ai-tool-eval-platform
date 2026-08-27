"""Tests for seed_samples script and default skill listing."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, Skill, ArtifactReference
from db.repository import SkillRepository
from scripts.samples import SAMPLES


def _trial_sample_to_skill_dict(sample) -> dict:
    """Convert TrialSample to skill dict for repository."""
    # Generate skill_id from sample_id
    skill_id = f"sample-{sample.sample_id}"
    
    # Extract metadata from raw_item
    raw = sample.raw_item
    origin_url = raw.get("html_url", raw.get("id", ""))
    description = raw.get("description", sample.label)
    
    # Build canonical skill dict
    return {
        "skill_id": skill_id,
        "canonical_name": sample.manifest_fields.get("name", sample.sample_id) if sample.manifest_fields else sample.sample_id,
        "source_kind": sample.source_kind.value,
        "origin_url": origin_url,
        "description": description,
        "status": sample.expected_final_status.value,
        "evidence_grade": "D",
        "is_alive": True,
        "author": raw.get("owner", {}).get("login") if "owner" in raw else raw.get("author"),
        "license_spdx": None,
        "declared_permissions": list(sample.declared_permissions) if sample.declared_permissions else [],
        "category_tags": [],
        "static_summary": sample.label,
        "admission_reasons": [],
        "warnings": list(sample.notes) if sample.notes else [],
    }


@pytest.fixture
def in_memory_session():
    """Create in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_seed_script_inserts_skills(in_memory_session):
    """Seed script logic inserts all sample skills."""
    repo = SkillRepository(in_memory_session)
    
    # Simulate seed_samples.py logic
    for sample in SAMPLES:
        skill_dict = _trial_sample_to_skill_dict(sample)
        repo.upsert_skill(skill_dict)
    
    # Verify all skills inserted
    skills, total = repo.list_skills(query=None, limit=100, offset=0)
    assert total >= 5
    assert len(skills) >= 5
    
    # Verify skill IDs match (with sample- prefix)
    skill_ids = {s["skill_id"] for s in skills}
    expected_ids = {f"sample-{s.sample_id}" for s in SAMPLES}
    assert expected_ids.issubset(skill_ids)


def test_list_skills_default_returns_results(in_memory_session):
    """list_skills with no query returns all skills."""
    repo = SkillRepository(in_memory_session)
    
    # Seed samples
    for sample in SAMPLES:
        skill_dict = _trial_sample_to_skill_dict(sample)
        repo.upsert_skill(skill_dict)
    
    # List with no query
    skills, total = repo.list_skills(query=None, limit=20, offset=0)
    
    assert len(skills) > 0
    assert total >= 5
    assert skills[0]["canonical_name"] is not None


def test_list_skills_query_filters(in_memory_session):
    """list_skills with query filters by name/description."""
    repo = SkillRepository(in_memory_session)
    
    # Seed samples
    for sample in SAMPLES:
        skill_dict = _trial_sample_to_skill_dict(sample)
        repo.upsert_skill(skill_dict)
    
    # Search with query matching a sample name
    # Use "doc" which should match S1-green's "doc-skill"
    skills, total = repo.list_skills(query="doc", limit=20, offset=0)
    
    # Should find at least one result
    assert len(skills) >= 1
    
    # Verify search worked - at least one result matches
    found = any(
        "doc" in s["canonical_name"].lower()
        for s in skills
    )
    assert found


def test_artifact_references_created(in_memory_session):
    """Seed creates artifact references for skills."""
    repo = SkillRepository(in_memory_session)
    
    # Seed first sample
    sample = SAMPLES[0]
    skill_dict = _trial_sample_to_skill_dict(sample)
    repo.upsert_skill(skill_dict)
    
    # Add artifact reference (simulating seed_samples.py)
    repo.add_artifact_reference(
        skill_id=skill_dict["skill_id"],
        bucket="evidence",
        key=f"{skill_dict['skill_id']}/placeholder",
        sha256="0" * 64,
        size_bytes=0,
        summary=f"Placeholder artifact for {sample.sample_id}",
    )
    
    # Verify artifact references exist
    refs = repo.get_artifact_references(skill_dict["skill_id"])
    
    assert len(refs) > 0
    assert refs[0]["bucket"] == "evidence"
    assert refs[0]["sha256"] == "0" * 64
