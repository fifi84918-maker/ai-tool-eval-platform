"""Database models and session management tests (SQLite in-memory)."""

import os
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
from db.models import Skill, ArtifactReference


@pytest.fixture
def db_engine():
    """Create SQLite in-memory engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


class TestSkillModel:
    """Test Skill model CRUD operations."""

    def test_create_skill(self, db_session):
        """Create and persist a Skill entity."""
        skill = Skill(
            skill_id="test-skill-001",
            canonical_name="test-skill",
            source_kind="github",
            origin_url="https://github.com/test/test",
            description="A test skill",
            status="NEUTRAL_TESTED",
            evidence_grade="D",
            is_alive=True,
            author="test-author",
            license_spdx="MIT",
            declared_permissions={"permissions": ["file_read"]},
            category_tags={"tags": ["test"]},
            static_summary={"issues": 0},
            admission_reasons={"reasons": ["test"]},
            warnings={"warnings": []},
        )
        
        db_session.add(skill)
        db_session.commit()
        
        # Query back
        result = db_session.query(Skill).filter_by(skill_id="test-skill-001").first()
        assert result is not None
        assert result.canonical_name == "test-skill"
        assert result.evidence_grade == "D"

    def test_skill_unique_constraint(self, db_session):
        """skill_id must be unique."""
        skill1 = Skill(
            skill_id="duplicate-id",
            canonical_name="skill1",
            source_kind="github",
            origin_url="https://github.com/test/test1",
            status="NEUTRAL_TESTED",
            evidence_grade="D",
            is_alive=True,
        )
        skill2 = Skill(
            skill_id="duplicate-id",
            canonical_name="skill2",
            source_kind="github",
            origin_url="https://github.com/test/test2",
            status="NEUTRAL_TESTED",
            evidence_grade="U",
            is_alive=True,
        )
        
        db_session.add(skill1)
        db_session.commit()
        
        db_session.add(skill2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_skill_timestamps(self, db_session):
        """created_at and updated_at are set automatically."""
        skill = Skill(
            skill_id="timestamp-test",
            canonical_name="timestamp-skill",
            source_kind="github",
            origin_url="https://github.com/test/test",
            status="NEUTRAL_TESTED",
            evidence_grade="D",
            is_alive=True,
        )
        
        db_session.add(skill)
        db_session.commit()
        
        assert skill.created_at is not None
        assert skill.updated_at is not None
        assert isinstance(skill.created_at, datetime)


class TestArtifactReferenceModel:
    """Test ArtifactReference model CRUD operations."""

    def test_create_artifact_reference(self, db_session):
        """Create and persist an ArtifactReference entity."""
        ref = ArtifactReference(
            skill_id="test-skill-001",
            bucket="artifacts",
            key="test-skill-001/artifact.json",
            sha256="abc123" * 10 + "abcd",  # 64 chars
            size_bytes=1024,
            summary="Test artifact",
        )
        
        db_session.add(ref)
        db_session.commit()
        
        # Query back
        result = db_session.query(ArtifactReference).filter_by(skill_id="test-skill-001").first()
        assert result is not None
        assert result.bucket == "artifacts"
        assert result.size_bytes == 1024

    def test_artifact_reference_no_content_stored(self, db_session):
        """ArtifactReference stores only pointers, not content (PRD D-005)."""
        ref = ArtifactReference(
            skill_id="test-skill-002",
            bucket="evidence",
            key="test-skill-002/evidence.json",
            sha256="def456" * 10 + "efgh",
            size_bytes=2048,
            summary="Evidence reference",
        )
        
        db_session.add(ref)
        db_session.commit()
        
        # Verify no content column exists
        result = db_session.query(ArtifactReference).filter_by(skill_id="test-skill-002").first()
        assert not hasattr(result, 'content')
        assert result.summary == "Evidence reference"  # Summary only

    def test_query_artifacts_by_skill_id(self, db_session):
        """Query all artifacts for a given skill_id."""
        refs = [
            ArtifactReference(
                skill_id="skill-with-artifacts",
                bucket="artifacts",
                key=f"skill-with-artifacts/artifact{i}.json",
                sha256=f"hash{i}" * 13 + "h",  # 64 chars
                size_bytes=i * 100,
            )
            for i in range(3)
        ]
        
        for ref in refs:
            db_session.add(ref)
        db_session.commit()
        
        results = db_session.query(ArtifactReference).filter_by(skill_id="skill-with-artifacts").all()
        assert len(results) == 3
