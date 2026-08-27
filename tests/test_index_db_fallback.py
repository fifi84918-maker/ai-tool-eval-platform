"""Database index and fallback mechanism tests."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
from db.repository import SkillRepository
from mcp_server.index import DatabaseSkillIndex, InMemorySkillIndex, get_index_with_fallback


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
def seeded_db_index(db_session):
    """Create DatabaseSkillIndex with seeded test data."""
    # Seed test data
    repo = SkillRepository(db_session)
    for i in range(3):
        repo.upsert_skill({
            "skill_id": f"db-skill-{i:03d}",
            "canonical_name": f"db-skill-{i:03d}" if i != 1 else "doc-skill-db",
            "source_kind": "github",
            "origin_url": f"https://github.com/test/skill{i}",
            "description": "Test skill from DB",
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
        })
    
    # Create session factory
    def session_factory():
        return db_session
    
    return DatabaseSkillIndex(session_factory=session_factory)


class TestDatabaseSkillIndex:
    """Test DatabaseSkillIndex functionality."""

    def test_database_index_search_returns_results(self, seeded_db_index):
        """DatabaseSkillIndex.search returns results from DB."""
        results = seeded_db_index.search("", limit=10)
        assert len(results) >= 3
        assert all(r["entity_type"] == "skill" for r in results)

    def test_database_index_get_returns_skill_with_jsonld(self, seeded_db_index):
        """DatabaseSkillIndex.get returns SkillDetail."""
        detail = seeded_db_index.get("db-skill-000")
        assert detail is not None
        assert detail["summary"]["skill_id"] == "db-skill-000"
        assert detail["summary"]["canonical_name"] == "db-skill-000"
        assert "author" in detail
        assert "declared_permissions" in detail

    def test_database_index_search_with_query(self, seeded_db_index):
        """DatabaseSkillIndex.search filters by query."""
        results = seeded_db_index.search("doc", limit=10)
        assert len(results) >= 1
        # At least one should match
        assert any("doc" in r["canonical_name"].lower() for r in results)


class TestIndexFallback:
    """Test fallback mechanism."""

    def test_fallback_to_memory_when_no_db_url(self, monkeypatch):
        """Falls back to InMemorySkillIndex when DATABASE_URL not set."""
        # Remove DATABASE_URL
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        with pytest.warns(RuntimeWarning, match="DATABASE_URL not set"):
            index = get_index_with_fallback()
        
        assert isinstance(index, InMemorySkillIndex)
        
        # Verify it works
        results = index.search("", limit=5)
        assert len(results) > 0
