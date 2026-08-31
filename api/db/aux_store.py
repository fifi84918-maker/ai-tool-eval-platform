"""SQLite-backed storage for profiles and recommendation history.

Provides drop-in replacements for the in-memory dicts in
api/routers/profiles.py and api/routers/recommend.py.
"""

import json
from datetime import datetime, timezone

from api.db.database import get_conn, _json_loads_safe


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def put_profile(profile_id: str, data: dict) -> None:
    """Upsert a project profile."""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO profiles (id, name, security_requirement, languages,
                              frameworks, domains, team_size, description, created_at)
        VALUES (:id, :name, :security_requirement, :languages,
                :frameworks, :domains, :team_size, :description, :created_at)
        ON CONFLICT(id) DO UPDATE SET
            name                 = excluded.name,
            security_requirement = excluded.security_requirement,
            languages            = excluded.languages,
            frameworks           = excluded.frameworks,
            domains              = excluded.domains,
            team_size            = excluded.team_size,
            description          = excluded.description
        """,
        {
            "id":                   profile_id,
            "name":                 data.get("name", ""),
            "security_requirement": data.get("security_requirement", "standard"),
            "languages":            json.dumps(data.get("languages", [])),
            "frameworks":           json.dumps(data.get("frameworks", [])),
            "domains":              json.dumps(data.get("domains", [])),
            "team_size":            data.get("team_size"),
            "description":          data.get("description", ""),
            "created_at":           data.get("created_at", datetime.now(timezone.utc).isoformat()),
        },
    )
    conn.commit()


def get_profile(profile_id: str) -> dict | None:
    """Retrieve a single profile dict or None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    return _row_to_profile(row) if row else None


def list_profiles() -> list[dict]:
    """Return all profiles as dicts."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM profiles ORDER BY created_at").fetchall()
    return [_row_to_profile(r) for r in rows]


def _row_to_profile(row) -> dict:
    d = dict(row)
    return {
        "id":                   d["id"],
        "name":                 d["name"],
        "security_requirement": d.get("security_requirement", "standard"),
        "languages":            _json_loads_safe(d.get("languages"), []),
        "frameworks":           _json_loads_safe(d.get("frameworks"), []),
        "domains":              _json_loads_safe(d.get("domains"), []),
        "team_size":            d.get("team_size"),
        "description":          d.get("description", ""),
        "created_at":           d.get("created_at"),
    }


def clear_profiles() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM profiles")
    conn.commit()


# ---------------------------------------------------------------------------
# Recommendation history
# ---------------------------------------------------------------------------

MAX_HISTORY = 20


def append_recommend_history(
    profile_id: str | None,
    profile_name: str,
    timestamp: str,
    response_json: str,
) -> None:
    """Insert a new history entry; trim oldest beyond MAX_HISTORY."""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO recommend_history (profile_id, profile_name, timestamp, response_json)
        VALUES (?, ?, ?, ?)
        """,
        (profile_id, profile_name, timestamp, response_json),
    )
    # Trim: delete oldest rows beyond MAX_HISTORY
    conn.execute(
        """
        DELETE FROM recommend_history
        WHERE id NOT IN (
            SELECT id FROM recommend_history
            ORDER BY id DESC
            LIMIT ?
        )
        """,
        (MAX_HISTORY,),
    )
    conn.commit()


def list_recommend_history(profile_id: str | None = None) -> list[dict]:
    """Return history entries (all or filtered by profile_id)."""
    conn = get_conn()
    if profile_id is None:
        rows = conn.execute(
            "SELECT * FROM recommend_history ORDER BY id ASC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM recommend_history WHERE profile_id = ? ORDER BY id ASC",
            (profile_id,),
        ).fetchall()
    return [_row_to_history(r) for r in rows]


def _row_to_history(row) -> dict:
    d = dict(row)
    return {
        "profile_id":   d.get("profile_id"),
        "profile_name": d["profile_name"],
        "timestamp":    d["timestamp"],
        "response":     _json_loads_safe(d["response_json"], {}),
    }


def clear_recommend_history() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM recommend_history")
    conn.commit()


# ---------------------------------------------------------------------------
# Ingest runs
# ---------------------------------------------------------------------------

def save_ingest_run(run: dict) -> None:
    """Upsert an ingest run record."""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO ingest_runs (
            run_id, query, started_at, finished_at,
            discovered, acquired, reviewed, quarantined, runnable, errors_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            finished_at = excluded.finished_at,
            discovered  = excluded.discovered,
            acquired    = excluded.acquired,
            reviewed    = excluded.reviewed,
            quarantined = excluded.quarantined,
            runnable    = excluded.runnable,
            errors_json = excluded.errors_json
        """,
        (
            run["run_id"],
            run.get("query", ""),
            run.get("started_at", datetime.now(timezone.utc).isoformat()),
            run.get("finished_at"),
            run.get("discovered", 0),
            run.get("acquired", 0),
            run.get("reviewed", 0),
            run.get("quarantined", 0),
            run.get("runnable", 0),
            json.dumps(run.get("errors", [])),
        ),
    )
    conn.commit()


def list_ingest_runs(limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ingest_runs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [_row_to_ingest_run(r) for r in rows]


def _row_to_ingest_run(row) -> dict:
    d = dict(row)
    return {
        "run_id":      d["run_id"],
        "query":       d["query"],
        "started_at":  d["started_at"],
        "finished_at": d.get("finished_at"),
        "discovered":  d.get("discovered", 0),
        "acquired":    d.get("acquired", 0),
        "reviewed":    d.get("reviewed", 0),
        "quarantined": d.get("quarantined", 0),
        "runnable":    d.get("runnable", 0),
        "errors":      _json_loads_safe(d.get("errors_json"), []),
    }


def clear_ingest_runs() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM ingest_runs")
    conn.commit()


# ---------------------------------------------------------------------------
# Convenience: clear everything (used in tests)
# ---------------------------------------------------------------------------

def clear_all_aux() -> None:
    """Clear profiles + history + ingest_runs (test helper)."""
    clear_profiles()
    clear_recommend_history()
    clear_ingest_runs()
