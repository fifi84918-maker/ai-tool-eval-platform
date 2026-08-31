"""SQLite persistence layer for the API store.

DB path priority:
  1. APP_DB_PATH environment variable
  2. <project-root>/data/app.db  (auto-created)

Use APP_DB_PATH=:memory: or a tmp_path in tests for isolation.
"""

import json
import os
import sqlite3
from pathlib import Path
from threading import local

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _resolve_db_path() -> str:
    """Return the effective DB path from env or project default."""
    env = os.environ.get("APP_DB_PATH", "")
    if env:
        return env
    # Default: <repo-root>/data/app.db
    root = Path(__file__).parent.parent.parent  # api/db/ -> repo root
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "app.db")


# ---------------------------------------------------------------------------
# Connection management (thread-local, auto-connect)
# ---------------------------------------------------------------------------

_tl = local()


def get_conn() -> sqlite3.Connection:
    """Return (or open) the thread-local SQLite connection.
    
    Tables are created automatically on first connection (lazy init).
    This ensures APP_DB_PATH is read *after* tests can override it.

    For :memory: mode the URI ``file::memory:?cache=shared&mode=memory``
    is used so that all threads/connections within the same process share
    the same in-memory database — which is critical for TestClient tests
    that handle requests on a worker thread different from the test thread.
    """
    conn = getattr(_tl, "conn", None)
    if conn is None:
        path = _resolve_db_path()
        if path == ":memory:":
            # Shared in-memory DB — all threads see the same data
            conn = sqlite3.connect(
                "file::memory:?cache=shared&mode=memory",
                uri=True,
                check_same_thread=False,
            )
        else:
            conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _tl.conn = conn
        # Lazy schema init: create tables if not present
        _init_schema(conn)
    return conn


def close_conn() -> None:
    """Close the thread-local connection if open."""
    conn = getattr(_tl, "conn", None)
    if conn:
        conn.close()
        _tl.conn = None


# ---------------------------------------------------------------------------
# Schema initialisation (idempotent)
# ---------------------------------------------------------------------------

DDL = """
-- canonical skills --------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    skill_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    platform        TEXT NOT NULL,
    platform_skill_id TEXT,
    underlying_model TEXT,
    license         TEXT,
    security_level  TEXT NOT NULL DEFAULT 'standard',
    high_risk       INTEGER NOT NULL DEFAULT 0,   -- BOOL (0/1)
    target_domains  TEXT NOT NULL DEFAULT '[]',   -- JSON list
    required_languages TEXT NOT NULL DEFAULT '[]',-- JSON list
    cost_info       TEXT,                          -- JSON obj or NULL
    benchmark_score REAL,
    certification   TEXT,
    state           TEXT NOT NULL,
    state_history   TEXT NOT NULL DEFAULT '[]',   -- JSON list of dicts
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    source_refs     TEXT NOT NULL DEFAULT '[]',   -- JSON list of source_ids
    artifact_refs   TEXT NOT NULL DEFAULT '[]'    -- JSON list of artifact_ids
);

-- source records -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    source_id        TEXT PRIMARY KEY,
    platform         TEXT NOT NULL,
    platform_skill_id TEXT NOT NULL,
    fetched_at       TEXT NOT NULL,
    raw_url          TEXT NOT NULL,
    dedupe_hash      TEXT NOT NULL UNIQUE,
    canonical_skill_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_sources_dedupe ON sources(dedupe_hash);
CREATE INDEX IF NOT EXISTS idx_sources_skill  ON sources(canonical_skill_id);

-- artifact records ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id  TEXT PRIMARY KEY,
    skill_id     TEXT NOT NULL,
    kind         TEXT NOT NULL,
    path_or_text TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_skill ON artifacts(skill_id);

-- project profiles ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    security_requirement TEXT NOT NULL DEFAULT 'standard',
    languages       TEXT NOT NULL DEFAULT '[]',   -- JSON list
    frameworks      TEXT NOT NULL DEFAULT '[]',   -- JSON list
    domains         TEXT NOT NULL DEFAULT '[]',   -- JSON list
    team_size       INTEGER,
    description     TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

-- recommendation history ---------------------------------------------------
CREATE TABLE IF NOT EXISTS recommend_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  TEXT,
    profile_name TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    response_json TEXT NOT NULL    -- full serialised RecommendationResponse
);
CREATE INDEX IF NOT EXISTS idx_rh_profile ON recommend_history(profile_id);

-- ingest runs --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingest_runs (
    run_id      TEXT PRIMARY KEY,
    query       TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    discovered  INTEGER NOT NULL DEFAULT 0,
    acquired    INTEGER NOT NULL DEFAULT 0,
    reviewed    INTEGER NOT NULL DEFAULT 0,
    quarantined INTEGER NOT NULL DEFAULT 0,
    runnable    INTEGER NOT NULL DEFAULT 0,
    errors_json TEXT NOT NULL DEFAULT '[]'  -- JSON list of error dicts
);
"""


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables (internal, called once per new connection)."""
    conn.executescript(DDL)
    conn.commit()


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Create all tables if they don't exist (idempotent).
    
    Public API kept for explicit call from tests / app startup.
    Normally not needed because get_conn() does lazy init.
    """
    c = conn or get_conn()
    _init_schema(c)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_loads_safe(s: str | None, default=None):
    if s is None:
        return default
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default
