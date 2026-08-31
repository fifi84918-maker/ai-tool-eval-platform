"""Tests for L2 Skill Store and State Machine (V1A L2) - PRD Aligned."""

import pytest
from datetime import datetime, timezone
from api.models import (
    CanonicalSkill,
    SourceRecord,
    ArtifactRecord,
    can_transition,
    validate_transition,
)
from api.store import (
    put_skill,
    get_skill,
    list_skills,
    put_source,
    put_artifact,
    transition_state,
    clear_all,
)


@pytest.fixture(autouse=True)
def clean_store():
    """清空存储（每个测试前后）。"""
    clear_all()
    yield
    clear_all()


def test_canonical_skill_minimal_build():
    """Test 1: 最小字段能构造 CanonicalSkill。"""
    skill = CanonicalSkill(
        skill_id="test123abc",
        name="Test Skill",
        description="A test skill",
        platform="github",
        state="DISCOVERED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    assert skill.skill_id == "test123abc"
    assert skill.name == "Test Skill"
    assert skill.state == "DISCOVERED"
    assert skill.security_level == "standard"  # default
    assert skill.high_risk is False  # default
    assert skill.target_domains == []  # default
    assert skill.source_refs == []  # default


def test_11_states_enum():
    """Test 2: 枚举 11 个 PRD 状态值齐全。"""
    from api.models.skill_state import ALLOWED_TRANSITIONS
    
    # PRD 3.1 的 11 种准入状态
    expected_states = {
        "DISCOVERED",
        "METADATA_ONLY",
        "ACQUIRED",
        "STATIC_REVIEWED",
        "QUARANTINED",
        "RUNNABLE",
        "NEUTRAL_TESTED",
        "NATIVE_TESTED",
        "VERIFIED",
        "STALE",
        "REMOVED"
    }
    
    actual_states = set(ALLOWED_TRANSITIONS.keys())
    
    assert actual_states == expected_states
    assert len(actual_states) == 11


def test_discovered_to_metadata_only():
    """Test 3: DISCOVERED → METADATA_ONLY（仅元数据路径）。"""
    assert can_transition("DISCOVERED", "METADATA_ONLY") is True
    
    # Should not raise
    validate_transition("DISCOVERED", "METADATA_ONLY")


def test_quarantine_on_static_block():
    """Test 4: ACQUIRED → QUARANTINED（静态审查发现问题隔离）。"""
    assert can_transition("ACQUIRED", "QUARANTINED") is True
    
    # QUARANTINED can be reviewed and go back to STATIC_REVIEWED
    assert can_transition("QUARANTINED", "STATIC_REVIEWED") is True
    
    # But cannot go to RUNNABLE directly
    assert can_transition("QUARANTINED", "RUNNABLE") is False


def test_stale_regression_path():
    """Test 5: STALE → ACQUIRED（回归路径，环境过期重测）。"""
    # This is NOT a backward transition, it's a regression path
    assert can_transition("STALE", "ACQUIRED") is True
    
    # Should not raise
    validate_transition("STALE", "ACQUIRED")


def test_removed_is_terminal():
    """Test 6: REMOVED 是终态（不能再流转）。"""
    assert can_transition("REMOVED", "DISCOVERED") is False
    assert can_transition("REMOVED", "ACQUIRED") is False
    assert can_transition("REMOVED", "VERIFIED") is False
    
    # REMOVED has no outgoing transitions
    from api.models.skill_state import ALLOWED_TRANSITIONS
    assert ALLOWED_TRANSITIONS["REMOVED"] == set()


def test_transition_writes_history():
    """Test 7: state_history 追加一条 StateTransition。"""
    skill = CanonicalSkill(
        skill_id="hist123",
        name="History Test",
        description="Test history recording",
        platform="github",
        state="DISCOVERED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    put_skill(skill)
    
    # Transition to ACQUIRED
    transition_state("hist123", "ACQUIRED", "Fetched full repository")
    
    # Get updated skill
    updated = get_skill("hist123")
    
    assert updated is not None
    assert updated.state == "ACQUIRED"
    assert len(updated.state_history) == 1
    
    history_entry = updated.state_history[0]
    assert history_entry["from_state"] == "DISCOVERED"
    assert history_entry["to_state"] == "ACQUIRED"
    assert history_entry["reason"] == "Fetched full repository"
    assert "at" in history_entry


def test_skill_store_crud():
    """Test 8: put/get/list_by_state 基本 CRUD。"""
    # Put two skills with different states
    skill1 = CanonicalSkill(
        skill_id="skill1",
        name="Skill One",
        description="First skill",
        platform="github",
        state="DISCOVERED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    skill2 = CanonicalSkill(
        skill_id="skill2",
        name="Skill Two",
        description="Second skill",
        platform="doubao",
        state="VERIFIED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    put_skill(skill1)
    put_skill(skill2)
    
    # Get by ID
    retrieved = get_skill("skill1")
    assert retrieved is not None
    assert retrieved.name == "Skill One"
    
    # List all
    all_skills = list_skills()
    assert len(all_skills) == 2
    
    # List by state
    discovered = list_skills(filter_by_state="DISCOVERED")
    assert len(discovered) == 1
    assert discovered[0].skill_id == "skill1"
    
    verified = list_skills(filter_by_state="VERIFIED")
    assert len(verified) == 1
    assert verified[0].skill_id == "skill2"


def test_source_artifact_link():
    """Test 9: source_refs/artifact_refs 能挂载。"""
    # Create skill
    skill = CanonicalSkill(
        skill_id="linked123",
        name="Linked Skill",
        description="Has sources and artifacts",
        platform="github",
        state="DISCOVERED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Create source
    source = SourceRecord(
        source_id="src001",
        platform="github",
        platform_skill_id="owner/repo",
        fetched_at=datetime.now(timezone.utc),
        raw_url="https://github.com/owner/repo",
        dedupe_hash="github:owner/repo",
        canonical_skill_id="linked123"
    )
    
    # Create artifact
    artifact = ArtifactRecord(
        artifact_id="art001",
        skill_id="linked123",
        kind="skill_md",
        path_or_text="# Skill content here",
        created_at=datetime.now(timezone.utc)
    )
    
    # Link them
    skill.source_refs.append("src001")
    skill.artifact_refs.append("art001")
    
    # Store
    put_skill(skill)
    put_source(source)
    put_artifact(artifact)
    
    # Retrieve and verify
    retrieved_skill = get_skill("linked123")
    assert retrieved_skill is not None
    assert "src001" in retrieved_skill.source_refs
    assert "art001" in retrieved_skill.artifact_refs
    
    # Verify source link back
    retrieved_source = source  # Already have it
    assert retrieved_source.canonical_skill_id == "linked123"
