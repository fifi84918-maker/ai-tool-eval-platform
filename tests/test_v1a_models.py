"""Tests for V1A source/artifact/license models (PRD 22.1)."""

from datetime import datetime
import uuid

import pytest

from db.models import SourceRecord, ArtifactVersion, LicenseAssessment
from db.repository import SourceRepository, ArtifactVersionRepository, LicenseRepository


@pytest.fixture
def source_repo(db_session):
    """Source repository fixture."""
    return SourceRepository(db_session)


@pytest.fixture
def artifact_repo(db_session):
    """Artifact version repository fixture."""
    return ArtifactVersionRepository(db_session)


@pytest.fixture
def license_repo(db_session):
    """License assessment repository fixture."""
    return LicenseRepository(db_session)


def test_source_record_upsert(source_repo, db_session):
    """Test source record upsert functionality."""
    # Create new source
    source = source_repo.upsert_by_platform(
        platform="github",
        platform_object_id="test/repo",
        skill_name="test-skill",
        raw_description="Test description",
        author="test-author",
        origin_url="https://github.com/test/repo",
    )
    
    assert source.id is not None
    assert source.platform == "github"
    assert source.platform_object_id == "test/repo"
    assert source.skill_name == "test-skill"
    
    # Update existing source
    updated = source_repo.upsert_by_platform(
        platform="github",
        platform_object_id="test/repo",
        skill_name="updated-skill",
    )
    
    assert updated.id == source.id
    assert updated.skill_name == "updated-skill"
    
    db_session.commit()


def test_artifact_version_add(artifact_repo, db_session):
    """Test artifact version add functionality."""
    artifact_id = str(uuid.uuid4())
    content_hash = "abc123def456"
    
    artifact = ArtifactVersion(
        id=artifact_id,
        version="v1.0.0",
        fetched_at=datetime.utcnow(),
        content_hash=content_hash,
        normalized=False,
        created_at=datetime.utcnow(),
    )
    
    added = artifact_repo.add(artifact)
    
    assert added.id == artifact_id
    assert added.content_hash == content_hash
    assert added.version == "v1.0.0"
    
    # Query by content hash
    found = artifact_repo.get_by_content_hash(content_hash)
    assert found is not None
    assert found.id == artifact_id
    
    db_session.commit()


def test_license_assessment_add(license_repo, artifact_repo, db_session):
    """Test license assessment add functionality."""
    # Create artifact first
    artifact_id = str(uuid.uuid4())
    artifact = ArtifactVersion(
        id=artifact_id,
        version="v1.0.0",
        fetched_at=datetime.utcnow(),
        content_hash="test123",
        normalized=False,
        created_at=datetime.utcnow(),
    )
    artifact_repo.add(artifact)
    
    # Create license assessment
    assessment_id = str(uuid.uuid4())
    assessment = LicenseAssessment(
        id=assessment_id,
        artifact_version_id=artifact_id,
        license="MIT",
        allows_archival=True,
        allows_public_display=True,
        allows_internal_test=True,
        allows_modification=True,
        confidence="high",
        needs_human_review=False,
        assessed_at=datetime.utcnow(),
    )
    
    added = license_repo.add(assessment)
    
    assert added.id == assessment_id
    assert added.license == "MIT"
    assert added.confidence == "high"
    
    # Query by artifact version
    found = license_repo.get_by_artifact_version(artifact_id)
    assert found is not None
    assert found.id == assessment_id
    
    db_session.commit()


def test_source_tables_exist(db_session):
    """Test that new tables exist in database."""
    from sqlalchemy import inspect
    
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    
    assert "source_records" in tables
    assert "artifact_versions" in tables
    assert "license_assessments" in tables
