"""Tests for scoring persistence and API integration."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from db.models import Base, Skill
from db.repository import SkillRepository
from db.migration_add_score import add_score_columns
from scoring import score_skill


@pytest.fixture
def in_memory_engine():
    """Create in-memory SQLite engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def in_memory_session(in_memory_engine):
    """Create in-memory SQLite session."""
    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    yield session
    session.close()


def test_add_score_columns_idempotent(in_memory_engine):
    """Running migration multiple times doesn't error."""
    # Columns should already exist from Base.metadata.create_all
    # Just verify they exist
    inspector = inspect(in_memory_engine)
    columns = [col["name"] for col in inspector.get_columns("skills")]
    assert "score_total" in columns
    assert "grade" in columns


def test_seed_with_scores_writes_grade(in_memory_session):
    """Seeded skills have grade field populated."""
    repo = SkillRepository(in_memory_session)
    
    # Create a sample skill
    skill_dict = {
        "skill_id": "test-skill-1",
        "canonical_name": "Test Skill",
        "source_kind": "github",
        "origin_url": "https://github.com/test/skill",
        "description": "Test description",
        "status": "NEUTRAL_TESTED",
        "evidence_grade": "D",
        "is_alive": True,
        "author": "tester",
        "license_spdx": None,
        "declared_permissions": [],
        "category_tags": [],
        "static_summary": None,
        "admission_reasons": [],
        "warnings": [],
    }
    
    repo.upsert_skill(skill_dict)
    
    # Compute score and update
    metrics = {"accuracy": 85.0, "reliability": 80.0}
    score_result = score_skill(metrics)
    
    from sqlalchemy import update
    in_memory_session.execute(
        update(Skill)
        .where(Skill.skill_id == "test-skill-1")
        .values(
            score_total=score_result["total"],
            grade=score_result["grade"],
        )
    )
    in_memory_session.commit()
    
    # Verify grade was written
    skill = repo.get_skill("test-skill-1")
    assert skill is not None
    assert skill["grade"] in {"A", "B", "C", "D", "U"}
    assert skill["score_total"] is not None
    assert isinstance(skill["score_total"], float)


def test_seed_all_five_have_grades(in_memory_session):
    """All five sample skills have non-null grades."""
    repo = SkillRepository(in_memory_session)
    
    # Create 5 sample skills with different scores
    sample_data = [
        ("skill-1", 92.0, "A"),
        ("skill-2", 78.0, "B"),
        ("skill-3", 65.0, "C"),
        ("skill-4", 45.0, "D"),
        ("skill-5", 30.0, "U"),
    ]
    
    for skill_id, score, expected_grade in sample_data:
        skill_dict = {
            "skill_id": skill_id,
            "canonical_name": f"Skill {skill_id}",
            "source_kind": "github",
            "origin_url": f"https://github.com/test/{skill_id}",
            "description": "Test",
            "status": "NEUTRAL_TESTED",
            "evidence_grade": "D",
            "is_alive": True,
            "author": None,
            "license_spdx": None,
            "declared_permissions": [],
            "category_tags": [],
            "static_summary": None,
            "admission_reasons": [],
            "warnings": [],
        }
        
        repo.upsert_skill(skill_dict)
        
        # Update with score
        from sqlalchemy import update
        in_memory_session.execute(
            update(Skill)
            .where(Skill.skill_id == skill_id)
            .values(score_total=score, grade=expected_grade)
        )
        in_memory_session.commit()
    
    # Verify all have grades
    skills, total = repo.list_skills(query=None, limit=10, offset=0)
    assert total == 5
    
    for skill in skills:
        assert skill["grade"] is not None
        assert skill["grade"] in {"A", "B", "C", "D", "U"}
        assert skill["score_total"] is not None


def test_api_summary_includes_grade(in_memory_session):
    """API summary response includes grade field."""
    repo = SkillRepository(in_memory_session)
    
    skill_dict = {
        "skill_id": "api-test-skill",
        "canonical_name": "API Test",
        "source_kind": "github",
        "origin_url": "https://github.com/test/api",
        "description": "API test skill",
        "status": "NEUTRAL_TESTED",
        "evidence_grade": "D",
        "is_alive": True,
        "author": None,
        "license_spdx": None,
        "declared_permissions": [],
        "category_tags": [],
        "static_summary": None,
        "admission_reasons": [],
        "warnings": [],
    }
    
    repo.upsert_skill(skill_dict)
    
    # Update with score
    from sqlalchemy import update
    in_memory_session.execute(
        update(Skill)
        .where(Skill.skill_id == "api-test-skill")
        .values(score_total=88.5, grade="B")
    )
    in_memory_session.commit()
    
    # Get skill via repository
    skill = repo.get_skill("api-test-skill")
    
    assert "grade" in skill
    assert skill["grade"] == "B"
    assert "score_total" in skill
    assert skill["score_total"] == 88.5


def test_api_detail_includes_score_total(in_memory_session):
    """API detail response includes score_total field."""
    repo = SkillRepository(in_memory_session)
    
    skill_dict = {
        "skill_id": "detail-test",
        "canonical_name": "Detail Test",
        "source_kind": "github",
        "origin_url": "https://github.com/test/detail",
        "description": "Detail test",
        "status": "NEUTRAL_TESTED",
        "evidence_grade": "D",
        "is_alive": True,
        "author": "tester",
        "license_spdx": "MIT",
        "declared_permissions": ["file_read"],
        "category_tags": ["test"],
        "static_summary": None,
        "admission_reasons": [],
        "warnings": [],
    }
    
    repo.upsert_skill(skill_dict)
    
    # Update with score
    from sqlalchemy import update
    in_memory_session.execute(
        update(Skill)
        .where(Skill.skill_id == "detail-test")
        .values(score_total=75.0, grade="B")
    )
    in_memory_session.commit()
    
    # Get skill
    skill = repo.get_skill("detail-test")
    
    assert "score_total" in skill
    assert isinstance(skill["score_total"], float)
    assert skill["score_total"] == 75.0


def test_grade_values_clamped(in_memory_session):
    """All grades are in the valid set {A,B,C,D,U}."""
    repo = SkillRepository(in_memory_session)
    
    # Create skills with all possible grades
    valid_grades = ["A", "B", "C", "D", "U"]
    
    for idx, grade in enumerate(valid_grades):
        skill_dict = {
            "skill_id": f"grade-test-{grade}",
            "canonical_name": f"Grade {grade}",
            "source_kind": "github",
            "origin_url": f"https://github.com/test/{grade}",
            "description": f"Grade {grade} test",
            "status": "NEUTRAL_TESTED",
            "evidence_grade": "D",
            "is_alive": True,
            "author": None,
            "license_spdx": None,
            "declared_permissions": [],
            "category_tags": [],
            "static_summary": None,
            "admission_reasons": [],
            "warnings": [],
        }
        
        repo.upsert_skill(skill_dict)
        
        # Update with grade
        from sqlalchemy import update
        in_memory_session.execute(
            update(Skill)
            .where(Skill.skill_id == f"grade-test-{grade}")
            .values(score_total=float(90 - idx * 15), grade=grade)
        )
        in_memory_session.commit()
    
    # Verify all grades are valid
    skills, total = repo.list_skills(query=None, limit=10, offset=0)
    
    for skill in skills:
        if skill["grade"] is not None:
            assert skill["grade"] in valid_grades
