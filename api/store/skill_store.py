"""SQLite-backed Skill Store for L2 Data Layer (V1A persistent).

Replaces the in-memory dicts with SQLite while keeping the exact same
public interface, so all callers (adapters, scanners, scorer, pipeline,
tests) work unchanged.

Thread-safety: sqlite3 WAL mode + thread-local connections.
Test isolation: set APP_DB_PATH=:memory: (or any tmp file) before import.
"""

import json
from datetime import datetime, timezone

from api.db.database import get_conn, _json_loads_safe
from api.models import (
    CanonicalSkill,
    SourceRecord,
    ArtifactRecord,
    create_transition,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(obj) -> str:
    """JSON-serialize with datetime → ISO string fallback."""
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Not serializable: {type(o)}")
    return json.dumps(obj, default=default)


def _skill_to_row(skill: CanonicalSkill) -> dict:
    """Serialise CanonicalSkill → column dict."""
    return {
        "skill_id":          skill.skill_id,
        "name":              skill.name,
        "description":       skill.description,
        "platform":          skill.platform,
        "platform_skill_id": skill.platform_skill_id,
        "underlying_model":  skill.underlying_model,
        "license":           skill.license,
        "security_level":    skill.security_level,
        "high_risk":         int(skill.high_risk),
        "target_domains":    json.dumps(skill.target_domains),
        "required_languages": json.dumps(skill.required_languages),
        "cost_info":         json.dumps(skill.cost_info) if skill.cost_info is not None else None,
        "benchmark_score":   skill.benchmark_score,
        "dynamic_score":     skill.dynamic_score,
        "certification":     skill.certification,
        "state":             skill.state,
        "state_history":     _json_dumps(skill.state_history),
        # V1E admission fields
        "status":            skill.status,
        "entity_type":       skill.entity_type,
        "risk_flags":        json.dumps(skill.risk_flags),
        "status_changed_at": skill.status_changed_at.isoformat()
                             if skill.status_changed_at is not None else None,
        "canonical_name":    skill.canonical_name,
        "created_at":        skill.created_at.isoformat(),
        "updated_at":        skill.updated_at.isoformat(),
        "source_refs":       json.dumps(skill.source_refs),
        "artifact_refs":     json.dumps(skill.artifact_refs),
    }


def _row_to_skill(row) -> CanonicalSkill:
    """Deserialise a sqlite3.Row → CanonicalSkill."""
    d = dict(row)
    # status_changed_at may be absent in older rows
    sca_raw = d.get("status_changed_at")
    status_changed_at = None
    if sca_raw:
        try:
            from datetime import datetime as _dt
            status_changed_at = _dt.fromisoformat(sca_raw)
        except ValueError:
            pass
    return CanonicalSkill(
        skill_id=d["skill_id"],
        name=d["name"],
        description=d["description"],
        platform=d["platform"],
        platform_skill_id=d.get("platform_skill_id"),
        underlying_model=d.get("underlying_model"),
        license=d.get("license"),
        security_level=d.get("security_level", "standard"),
        high_risk=bool(d.get("high_risk", 0)),
        target_domains=_json_loads_safe(d.get("target_domains"), []),
        required_languages=_json_loads_safe(d.get("required_languages"), []),
        cost_info=_json_loads_safe(d.get("cost_info"), None),
        benchmark_score=d.get("benchmark_score"),
        dynamic_score=d.get("dynamic_score"),
        certification=d.get("certification"),
        state=d["state"],
        state_history=_json_loads_safe(d.get("state_history"), []),
        # V1E admission fields — default-safe for old rows
        status=d.get("status") or "DISCOVERED",
        entity_type=d.get("entity_type") or "SKILL",
        risk_flags=_json_loads_safe(d.get("risk_flags"), []),
        status_changed_at=status_changed_at,
        canonical_name=d.get("canonical_name"),
        created_at=datetime.fromisoformat(d["created_at"]),
        updated_at=datetime.fromisoformat(d["updated_at"]),
        source_refs=_json_loads_safe(d.get("source_refs"), []),
        artifact_refs=_json_loads_safe(d.get("artifact_refs"), []),
    )


def _source_to_row(source: SourceRecord) -> dict:
    return {
        "source_id":          source.source_id,
        "platform":           source.platform,
        "platform_skill_id":  source.platform_skill_id,
        "fetched_at":         source.fetched_at.isoformat(),
        "raw_url":            source.raw_url,
        "dedupe_hash":        source.dedupe_hash,
        "canonical_skill_id": source.canonical_skill_id,
    }


def _row_to_source(row) -> SourceRecord:
    d = dict(row)
    return SourceRecord(
        source_id=d["source_id"],
        platform=d["platform"],
        platform_skill_id=d["platform_skill_id"],
        fetched_at=datetime.fromisoformat(d["fetched_at"]),
        raw_url=d["raw_url"],
        dedupe_hash=d["dedupe_hash"],
        canonical_skill_id=d.get("canonical_skill_id"),
    )


def _artifact_to_row(artifact: ArtifactRecord) -> dict:
    return {
        "artifact_id":  artifact.artifact_id,
        "skill_id":     artifact.skill_id,
        "kind":         artifact.kind,
        "path_or_text": artifact.path_or_text,
        "created_at":   artifact.created_at.isoformat(),
    }


def _row_to_artifact(row) -> ArtifactRecord:
    d = dict(row)
    return ArtifactRecord(
        artifact_id=d["artifact_id"],
        skill_id=d["skill_id"],
        kind=d["kind"],
        path_or_text=d["path_or_text"],
        created_at=datetime.fromisoformat(d["created_at"]),
    )


# ---------------------------------------------------------------------------
# Public skill API
# ---------------------------------------------------------------------------

def put_skill(skill: CanonicalSkill) -> None:
    """Upsert a skill into the DB (updates updated_at automatically)."""
    skill.updated_at = datetime.now(timezone.utc)
    row = _skill_to_row(skill)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO skills (
            skill_id, name, description, platform, platform_skill_id,
            underlying_model, license, security_level, high_risk,
            target_domains, required_languages, cost_info, benchmark_score,
            dynamic_score, certification, state, state_history,
            status, entity_type, risk_flags, status_changed_at, canonical_name,
            created_at, updated_at, source_refs, artifact_refs
        ) VALUES (
            :skill_id, :name, :description, :platform, :platform_skill_id,
            :underlying_model, :license, :security_level, :high_risk,
            :target_domains, :required_languages, :cost_info, :benchmark_score,
            :dynamic_score, :certification, :state, :state_history,
            :status, :entity_type, :risk_flags, :status_changed_at, :canonical_name,
            :created_at, :updated_at, :source_refs, :artifact_refs
        )
        ON CONFLICT(skill_id) DO UPDATE SET
            name              = excluded.name,
            description       = excluded.description,
            platform          = excluded.platform,
            platform_skill_id = excluded.platform_skill_id,
            underlying_model  = excluded.underlying_model,
            license           = excluded.license,
            security_level    = excluded.security_level,
            high_risk         = excluded.high_risk,
            target_domains    = excluded.target_domains,
            required_languages= excluded.required_languages,
            cost_info         = excluded.cost_info,
            benchmark_score   = excluded.benchmark_score,
            dynamic_score     = excluded.dynamic_score,
            certification     = excluded.certification,
            state             = excluded.state,
            state_history     = excluded.state_history,
            status            = excluded.status,
            entity_type       = excluded.entity_type,
            risk_flags        = excluded.risk_flags,
            status_changed_at = excluded.status_changed_at,
            canonical_name    = excluded.canonical_name,
            updated_at        = excluded.updated_at,
            source_refs       = excluded.source_refs,
            artifact_refs     = excluded.artifact_refs
        """,
        row,
    )
    conn.commit()


def get_skill(skill_id: str) -> CanonicalSkill | None:
    """Fetch a skill by ID; returns None if not found."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM skills WHERE skill_id = ?", (skill_id,)
    ).fetchone()
    return _row_to_skill(row) if row else None


def list_skills(filter_by_state: str | None = None) -> list[CanonicalSkill]:
    """List all skills, optionally filtered by state."""
    conn = get_conn()
    if filter_by_state is None:
        rows = conn.execute("SELECT * FROM skills").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM skills WHERE state = ?", (filter_by_state,)
        ).fetchall()
    return [_row_to_skill(r) for r in rows]


# ---------------------------------------------------------------------------
# Public source API
# ---------------------------------------------------------------------------

def put_source(source: SourceRecord) -> None:
    """Upsert a source record (unique on dedupe_hash)."""
    row = _source_to_row(source)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO sources (
            source_id, platform, platform_skill_id, fetched_at,
            raw_url, dedupe_hash, canonical_skill_id
        ) VALUES (
            :source_id, :platform, :platform_skill_id, :fetched_at,
            :raw_url, :dedupe_hash, :canonical_skill_id
        )
        ON CONFLICT(source_id) DO UPDATE SET
            platform           = excluded.platform,
            platform_skill_id  = excluded.platform_skill_id,
            fetched_at         = excluded.fetched_at,
            raw_url            = excluded.raw_url,
            dedupe_hash        = excluded.dedupe_hash,
            canonical_skill_id = excluded.canonical_skill_id
        """,
        row,
    )
    conn.commit()


def get_source(source_id: str) -> SourceRecord | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM sources WHERE source_id = ?", (source_id,)
    ).fetchone()
    return _row_to_source(row) if row else None


def list_sources() -> list[SourceRecord]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM sources").fetchall()
    return [_row_to_source(r) for r in rows]


# ---------------------------------------------------------------------------
# Public artifact API
# ---------------------------------------------------------------------------

def put_artifact(artifact: ArtifactRecord) -> None:
    """Upsert an artifact record."""
    row = _artifact_to_row(artifact)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO artifacts (artifact_id, skill_id, kind, path_or_text, created_at)
        VALUES (:artifact_id, :skill_id, :kind, :path_or_text, :created_at)
        ON CONFLICT(artifact_id) DO UPDATE SET
            skill_id     = excluded.skill_id,
            kind         = excluded.kind,
            path_or_text = excluded.path_or_text,
            created_at   = excluded.created_at
        """,
        row,
    )
    conn.commit()


def get_artifact(artifact_id: str) -> ArtifactRecord | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)
    ).fetchone()
    return _row_to_artifact(row) if row else None


def list_artifacts(skill_id: str | None = None) -> list[ArtifactRecord]:
    conn = get_conn()
    if skill_id is None:
        rows = conn.execute("SELECT * FROM artifacts").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM artifacts WHERE skill_id = ?", (skill_id,)
        ).fetchall()
    return [_row_to_artifact(r) for r in rows]


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

def transition_state(skill_id: str, to_state: str, reason: str) -> None:
    """Validate and apply a state transition (persists immediately)."""
    skill = get_skill(skill_id)
    if skill is None:
        raise ValueError(f"Skill not found: {skill_id}")

    transition = create_transition(skill.state, to_state, reason)

    skill.state = to_state
    skill.state_history.append(transition.model_dump())
    skill.updated_at = datetime.now(timezone.utc)

    put_skill(skill)


# ---------------------------------------------------------------------------
# Test helper
# ---------------------------------------------------------------------------

def clear_all() -> None:
    """Delete all rows from all store tables.

    Used by test fixtures (autouse) to isolate test runs.
    Works for both :memory: DB and file DB pointed at by APP_DB_PATH.
    """
    conn = get_conn()
    conn.execute("DELETE FROM artifacts")
    conn.execute("DELETE FROM sources")
    conn.execute("DELETE FROM skills")
    conn.commit()
