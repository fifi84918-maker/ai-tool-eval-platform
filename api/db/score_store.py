"""Persistence helpers for 8-dimension scoring results (V1F).

Stores scores alongside skill rows in the `skills` table via the
three additional columns added by _ensure_columns():

    dimensions_json  TEXT            -- JSON object {dim: value|null}
    evidence_level   TEXT            -- A/B/C/D/U
    sample_size      INTEGER         -- test-run count (0 = static only)

A separate `skill_scores` snapshot table is also maintained for history.
Both operations are idempotent (UPSERT).
"""

import json
import logging
from datetime import datetime, timezone

from api.db.database import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ensure the snapshot table exists (supplements _ensure_columns for new table)
# ---------------------------------------------------------------------------

_SCORES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS skill_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id        TEXT NOT NULL,
    dimensions_json TEXT NOT NULL,          -- {dim: value|null}
    composite       REAL,
    evidence_level  TEXT NOT NULL DEFAULT 'U',
    sample_size     INTEGER NOT NULL DEFAULT 0,
    valid_until     TEXT,
    uplift          REAL,
    scored_at       TEXT NOT NULL,
    UNIQUE(skill_id)                        -- one current row per skill (upsert)
);
CREATE INDEX IF NOT EXISTS idx_ss_skill ON skill_scores(skill_id);
"""


def _ensure_scores_table() -> None:
    """Idempotent: create skill_scores table if absent."""
    conn = get_conn()
    conn.executescript(_SCORES_TABLE_DDL)
    conn.commit()


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def upsert_score(score_result) -> None:
    """Persist a ScoreResult to both skill_scores table and skills row.

    Parameters
    ----------
    score_result : ScoreResult
        Must have skill_id, dimensions, composite, evidence_level,
        sample_size, valid_until, uplift.
    """
    _ensure_scores_table()

    skill_id     = score_result.skill_id
    dims_json    = json.dumps(score_result.dimensions)
    composite    = score_result.composite
    evidence     = score_result.evidence_level
    sample_size  = score_result.sample_size
    valid_until  = score_result.valid_until
    uplift       = score_result.uplift
    scored_at    = datetime.now(timezone.utc).isoformat()

    conn = get_conn()

    # 1. Upsert into snapshot table
    conn.execute(
        """
        INSERT INTO skill_scores
            (skill_id, dimensions_json, composite, evidence_level,
             sample_size, valid_until, uplift, scored_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(skill_id) DO UPDATE SET
            dimensions_json = excluded.dimensions_json,
            composite       = excluded.composite,
            evidence_level  = excluded.evidence_level,
            sample_size     = excluded.sample_size,
            valid_until     = excluded.valid_until,
            uplift          = excluded.uplift,
            scored_at       = excluded.scored_at
        """,
        (skill_id, dims_json, composite, evidence,
         sample_size, valid_until, uplift, scored_at),
    )

    # 2. Mirror key fields onto skills row (for JOIN-free API reads)
    conn.execute(
        """
        UPDATE skills
        SET dimensions_json = ?,
            evidence_level  = ?,
            sample_size     = ?
        WHERE skill_id = ?
        """,
        (dims_json, evidence, sample_size, skill_id),
    )

    conn.commit()
    logger.info("upsert_score skill=%s evidence=%s composite=%s",
                skill_id[:12], evidence, composite)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_score(skill_id: str) -> dict | None:
    """Return the latest score record for skill_id, or None if absent."""
    _ensure_scores_table()
    conn = get_conn()
    row = conn.execute(
        """SELECT skill_id, dimensions_json, composite, evidence_level,
                  sample_size, valid_until, uplift, scored_at
           FROM skill_scores
           WHERE skill_id = ?""",
        (skill_id,),
    ).fetchone()

    if row is None:
        return None

    d = dict(row)
    try:
        d["dimensions"] = json.loads(d.pop("dimensions_json", "{}") or "{}")
    except (json.JSONDecodeError, TypeError):
        d["dimensions"] = {}

    return d


def list_scores(limit: int = 100) -> list[dict]:
    """Return up to ``limit`` score records, most recently scored first."""
    _ensure_scores_table()
    conn = get_conn()
    rows = conn.execute(
        """SELECT skill_id, dimensions_json, composite, evidence_level,
                  sample_size, valid_until, uplift, scored_at
           FROM skill_scores
           ORDER BY scored_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        try:
            d["dimensions"] = json.loads(d.pop("dimensions_json", "{}") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["dimensions"] = {}
        results.append(d)
    return results
