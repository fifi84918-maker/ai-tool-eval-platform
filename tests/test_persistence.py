"""Persistence tests — SQLite store (V1A SQLite).

Verifies:
1. restart_equivalence: write → reopen same DB → read back consistent
2. dedup: same repo twice → only one CanonicalSkill
3. skill_list_detail: list/get are consistent across connection lifecycle
4. recommend_history: history survives multiple connections

All tests use a fresh temporary DB file via APP_DB_PATH to avoid
polluting data/app.db and to guarantee cross-connection visibility
(a temp file is used rather than :memory: so reconnect works cleanly).
"""

import json
import os
import uuid
import pytest
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Fixture: isolated per-test DB
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point APP_DB_PATH at a fresh temp file and reset the thread-local
    connection so every call to get_conn() uses this new DB."""
    db_file = str(tmp_path / "test_persist.db")
    monkeypatch.setenv("APP_DB_PATH", db_file)

    # Force-close any existing thread-local connection so next get_conn()
    # opens a fresh connection to the new path.
    from api.db.database import close_conn, _tl
    close_conn()

    # Import store modules to trigger lazy init on the new path
    from api.db.database import get_conn
    conn = get_conn()  # creates tables

    yield db_file

    # Cleanup: close connection after test
    close_conn()


# ---------------------------------------------------------------------------
# Test 1: restart equivalence
# ---------------------------------------------------------------------------

def test_restart_equivalence(tmp_db):
    """Write skills/sources/artifacts → close connection → reopen same file → read back identical data."""
    from api.db.database import close_conn, _tl

    # --- Write phase ---
    from api.store.skill_store import put_skill, put_source, put_artifact

    skill_id = "a" * 64
    now = datetime.now(timezone.utc)

    from api.models import CanonicalSkill, SourceRecord, ArtifactRecord
    skill = CanonicalSkill(
        skill_id=skill_id,
        name="Restart Test Skill",
        description="Persists across restart",
        platform="github",
        platform_skill_id="test/restart",
        state="DISCOVERED",
        created_at=now,
        updated_at=now,
    )
    put_skill(skill)

    source_id = uuid.uuid4().hex
    source = SourceRecord(
        source_id=source_id,
        platform="github",
        platform_skill_id="test/restart",
        fetched_at=now,
        raw_url="https://github.com/test/restart",
        dedupe_hash="github:test/restart",
        canonical_skill_id=skill_id,
    )
    put_source(source)

    artifact_id = uuid.uuid4().hex
    artifact = ArtifactRecord(
        artifact_id=artifact_id,
        skill_id=skill_id,
        kind="skill_md",
        path_or_text="# Test",
        created_at=now,
    )
    put_artifact(artifact)

    # --- Simulate "restart": close the thread-local connection ---
    close_conn()

    # --- Reopen phase: new connection to same file ---
    from api.db.database import get_conn
    conn2 = get_conn()
    assert conn2 is not None

    # Reload from store (uses same file because APP_DB_PATH unchanged)
    from api.store.skill_store import get_skill, get_source, get_artifact

    loaded_skill = get_skill(skill_id)
    assert loaded_skill is not None, "Skill lost after connection reset"
    assert loaded_skill.name == "Restart Test Skill"
    assert loaded_skill.state == "DISCOVERED"

    loaded_source = get_source(source_id)
    assert loaded_source is not None, "Source lost after connection reset"
    assert loaded_source.dedupe_hash == "github:test/restart"

    loaded_artifact = get_artifact(artifact_id)
    assert loaded_artifact is not None, "Artifact lost after connection reset"
    assert loaded_artifact.kind == "skill_md"


# ---------------------------------------------------------------------------
# Test 2: dedup — same repo twice → single skill
# ---------------------------------------------------------------------------

def test_dedup_same_repo(tmp_db):
    """Ingesting the same repo twice must not create duplicate skills."""
    from api.adapters.dedup import compute_dedupe_hash, is_duplicate
    from api.store.skill_store import put_source, list_sources, list_skills

    platform = "github"
    platform_id = "acme/dedup-test"
    dedupe_hash = compute_dedupe_hash(platform, platform_id)

    now = datetime.now(timezone.utc)
    from api.models import SourceRecord

    # First insert
    assert not is_duplicate(platform, platform_id), "Should not be duplicate before first insert"
    src1 = SourceRecord(
        source_id="src-001",
        platform=platform,
        platform_skill_id=platform_id,
        fetched_at=now,
        raw_url=f"https://github.com/{platform_id}",
        dedupe_hash=dedupe_hash,
    )
    put_source(src1)

    # Dedup check after first insert
    assert is_duplicate(platform, platform_id), "Should be duplicate after first insert"

    # Second attempted insert with same dedupe_hash (upsert — won't duplicate)
    src2 = SourceRecord(
        source_id="src-001",  # same source_id → upsert replaces
        platform=platform,
        platform_skill_id=platform_id,
        fetched_at=now,
        raw_url=f"https://github.com/{platform_id}",
        dedupe_hash=dedupe_hash,
    )
    put_source(src2)

    sources = list_sources()
    matching = [s for s in sources if s.platform_skill_id == platform_id]
    assert len(matching) == 1, f"Expected 1 source, got {len(matching)}"


# ---------------------------------------------------------------------------
# Test 3: skill list/detail consistency
# ---------------------------------------------------------------------------

def test_skill_list_detail_consistent(tmp_db):
    """list_skills and get_skill return consistent data after multiple put_skill calls."""
    from api.store.skill_store import put_skill, get_skill, list_skills, transition_state
    from api.models import CanonicalSkill

    now = datetime.now(timezone.utc)
    ids = [f"{str(i).zfill(2)}{'a'*62}" for i in range(3)]

    for i, sid in enumerate(ids):
        skill = CanonicalSkill(
            skill_id=sid,
            name=f"Skill {i}",
            description=f"Description {i}",
            platform="github",
            platform_skill_id=f"org/skill{i}",
            state="DISCOVERED",
            created_at=now,
            updated_at=now,
        )
        put_skill(skill)

    # List returns all three
    all_skills = list_skills()
    assert len(all_skills) >= 3

    # Individual get matches list
    for sid in ids:
        s = get_skill(sid)
        assert s is not None
        found_in_list = any(x.skill_id == sid for x in all_skills)
        assert found_in_list, f"{sid} missing from list_skills"

    # Transition state and verify consistency
    transition_state(ids[0], "ACQUIRED", "test transition")
    s_after = get_skill(ids[0])
    assert s_after.state == "ACQUIRED"
    assert any(t["to_state"] == "ACQUIRED" for t in s_after.state_history)

    # Filter by state
    discovered = list_skills(filter_by_state="DISCOVERED")
    assert all(s.state == "DISCOVERED" for s in discovered)
    assert not any(s.skill_id == ids[0] for s in discovered)


# ---------------------------------------------------------------------------
# Test 4: recommend history survives reconnect
# ---------------------------------------------------------------------------

def test_recommend_history_persistent(tmp_db):
    """Recommendation history entries survive connection reset."""
    from api.db.database import close_conn
    from api.db.aux_store import append_recommend_history, list_recommend_history, clear_recommend_history

    clear_recommend_history()

    ts = datetime.now(timezone.utc).isoformat()
    fake_response = {"total": 2, "items": [{"bundle_id": "bundle-starter"}]}

    append_recommend_history(
        profile_id="test-profile-001",
        profile_name="My Test Project",
        timestamp=ts,
        response_json=json.dumps(fake_response),
    )

    # Verify before reconnect
    history = list_recommend_history()
    assert len(history) == 1
    assert history[0]["profile_name"] == "My Test Project"
    assert history[0]["response"]["total"] == 2

    # Simulate reconnect
    close_conn()

    # Re-read after reconnect
    history2 = list_recommend_history()
    assert len(history2) == 1, "History lost after connection reset"
    assert history2[0]["profile_id"] == "test-profile-001"
    assert history2[0]["response"]["items"][0]["bundle_id"] == "bundle-starter"

    # Filter by profile_id
    filtered = list_recommend_history(profile_id="test-profile-001")
    assert len(filtered) == 1

    none_found = list_recommend_history(profile_id="nonexistent")
    assert none_found == []
