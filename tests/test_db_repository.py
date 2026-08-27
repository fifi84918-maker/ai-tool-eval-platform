"""Repository pattern tests with SQLite in-memory."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
from db.repository import SkillRepository


@pytest.fixture
def db_session():
    """Create SQLite in-memory session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def repo(db_session):
    """Create SkillRepository instance."""
    return SkillRepository(db_session)


class TestSkillRepository:
    """Test SkillRepository CRUD operations."""

    def test_upsert_and_get_skill(self, repo):
        """Upsert skill and retrieve it."""
        skill_data = {
            "skill_id": "test-skill-001",
            "canonical_name": "test-skill",
            "source_kind": "github",
            "origin_url": "https://github.com/test/test",
            "description": "A test skill",
            "status": "NEUTRAL_TESTED",
            "evidence_grade": "D",
            "is_alive": True,
            "author": "test-author",
            "license_spdx": "MIT",
            "declared_permissions": ["file_read"],
            "category_tags": ["test"],
            "static_summary": {"issues": 0},
            "admission_reasons": ["test"],
            "warnings": [],
        }
        
        # Upsert
        result = repo.upsert_skill(skill_data)
        assert result["skill_id"] == "test-skill-001"
        assert result["evidence_grade"] == "D"
        
        # Get
        retrieved = repo.get_skill("test-skill-001")
        assert retrieved is not None
        assert retrieved["canonical_name"] == "test-skill"
        assert retrieved["evidence_grade"] == "D"

    def test_list_skills_with_query_filter(self, repo):
        """List skills with query filter."""
        # Insert test skills
        for i in range(3):
            repo.upsert_skill({
                "skill_id": f"skill-{i:03d}",
                "canonical_name": f"skill-{i:03d}" if i != 1 else "doc-skill",
                "source_kind": "github",
                "origin_url": f"https://github.com/test/skill{i}",
                "status": "NEUTRAL_TESTED",
                "evidence_grade": "D",
                "is_alive": True,
            })
        
        # Search for "doc"
        results, total = repo.list_skills(query="doc", limit=10, offset=0)
        assert len(results) == 1
        assert results[0]["canonical_name"] == "doc-skill"

    def test_list_skills_pagination(self, repo):
        """List skills with pagination."""
        # Insert 5 skills
        for i in range(5):
            repo.upsert_skill({
                "skill_id": f"skill-{i:03d}",
                "canonical_name": f"skill-{i:03d}",
                "source_kind": "github",
                "origin_url": f"https://github.com/test/skill{i}",
                "status": "NEUTRAL_TESTED",
                "evidence_grade": "D",
                "is_alive": True,
            })
        
        # Page 1 (limit 2, offset 0)
        page1, total = repo.list_skills(query=None, limit=2, offset=0)
        assert len(page1) == 2
        assert total == 5
        
        # Page 2 (limit 2, offset 2)
        page2, total = repo.list_skills(query=None, limit=2, offset=2)
        assert len(page2) == 2
        assert page1[0]["skill_id"] != page2[0]["skill_id"]

    def test_add_and_query_artifact_references(self, repo):
        """Add and query artifact references."""
        # Add skill first
        repo.upsert_skill({
            "skill_id": "skill-with-artifacts",
            "canonical_name": "skill-with-artifacts",
            "source_kind": "github",
            "origin_url": "https://github.com/test/test",
            "status": "NEUTRAL_TESTED",
            "evidence_grade": "D",
            "is_alive": True,
        })
        
        # Add artifact references
        for i in range(3):
            repo.add_artifact_reference(
                skill_id="skill-with-artifacts",
                bucket="artifacts",
                key=f"skill-with-artifacts/artifact{i}.json",
                sha256=f"hash{i}" * 16,
                size_bytes=i * 100,
                summary=f"Artifact {i}",
            )
        
        # Query
        refs = repo.get_artifact_references("skill-with-artifacts")
        assert len(refs) == 3
        assert refs[0]["bucket"] == "artifacts"

    def test_scrub_applied_on_read(self, repo):
        """Sensitive fields are scrubbed on read (PRD D-005)."""
        # Insert skill with potentially sensitive data
        skill_data = {
            "skill_id": "skill-with-sensitive",
            "canonical_name": "sensitive-skill",
            "source_kind": "github",
            "origin_url": "https://github.com/test/test",
            "status": "NEUTRAL_TESTED",
            "evidence_grade": "B",  # Will be clamped to D/U
            "is_alive": True,
            "description": "Contains api_key in description",  # Scrub will handle
        }
        
        repo.upsert_skill(skill_data)
        
        # Retrieve and verify scrubbing
        retrieved = repo.get_skill("skill-with-sensitive")
        assert retrieved is not None
        
        # Evidence grade should be clamped
        assert retrieved["evidence_grade"] in ("D", "U")
        
        # policy.scrub() is applied (no assertions/scoring_weights/etc)
        import json
        text = json.dumps(retrieved, ensure_ascii=False)
        assert "assertions" not in text
        assert "scoring_weights" not in text
