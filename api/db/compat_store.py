"""Persistence for CompatResult (V1G — §6.3).

Stores compatibility analysis results in two places:
  1. skill_compat snapshot table (full history, one row per skill)
  2. skills.compat_status + skills.compat_details_json (fast read columns)

Both operations are idempotent (UPSERT on skill_id).
"""

import json
import logging
from datetime import datetime, timezone

from api.db.database import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Snapshot table DDL
# ---------------------------------------------------------------------------

_COMPAT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS skill_compat (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id            TEXT NOT NULL,
    compat_status       TEXT NOT NULL DEFAULT 'UNKNOWN',
    portable_core_json  TEXT NOT NULL DEFAULT '{}',
    host_overlay_json   TEXT NOT NULL DEFAULT '{}',
    evidence_json       TEXT NOT NULL DEFAULT '{}',
    recommendations_json TEXT NOT NULL DEFAULT '[]',
    analyzed_at         TEXT NOT NULL,
    UNIQUE(skill_id)
);
CREATE INDEX IF NOT EXISTS idx_sc_skill ON skill_compat(skill_id);
"""


def _ensure_compat_table() -> None:
    """Idempotent: create skill_compat table if absent."""
    conn = get_conn()
    conn.executescript(_COMPAT_TABLE_DDL)
    conn.commit()


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def upsert_compat(compat_result) -> None:
    """Persist a CompatResult to the snapshot table and skills row.

    Parameters
    ----------
    compat_result : CompatResult
    """
    _ensure_compat_table()

    skill_id     = compat_result.skill_id
    status       = compat_result.compat_status
    portable_j   = json.dumps(compat_result.portable_core.to_dict())
    overlay_j    = json.dumps(compat_result.host_overlay.to_dict())
    evidence_j   = json.dumps(compat_result.evidence.to_dict())
    recs_j       = json.dumps(compat_result.recommendations)
    analyzed_at  = datetime.now(timezone.utc).isoformat()

    # Full details snapshot for the compat_details_json column
    details_snap = {
        "compat_status":   status,
        "portable_core":   compat_result.portable_core.to_dict(),
        "host_overlay":    compat_result.host_overlay.to_dict(),
        "evidence":        compat_result.evidence.to_dict(),
        "recommendations": compat_result.recommendations,
    }
    details_j = json.dumps(details_snap)

    conn = get_conn()

    # 1. Upsert snapshot table
    conn.execute(
        """
        INSERT INTO skill_compat
            (skill_id, compat_status, portable_core_json, host_overlay_json,
             evidence_json, recommendations_json, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(skill_id) DO UPDATE SET
            compat_status        = excluded.compat_status,
            portable_core_json   = excluded.portable_core_json,
            host_overlay_json    = excluded.host_overlay_json,
            evidence_json        = excluded.evidence_json,
            recommendations_json = excluded.recommendations_json,
            analyzed_at          = excluded.analyzed_at
        """,
        (skill_id, status, portable_j, overlay_j, evidence_j, recs_j, analyzed_at),
    )

    # 2. Mirror onto skills row (for JOIN-free reads)
    conn.execute(
        """
        UPDATE skills
        SET compat_status       = ?,
            compat_details_json = ?
        WHERE skill_id = ?
        """,
        (status, details_j, skill_id),
    )

    conn.commit()
    logger.info("upsert_compat skill=%s status=%s", skill_id[:12], status)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_compat(skill_id: str) -> dict | None:
    """Return the latest compat record, or None."""
    _ensure_compat_table()
    conn = get_conn()
    row = conn.execute(
        """SELECT skill_id, compat_status,
                  portable_core_json, host_overlay_json,
                  evidence_json, recommendations_json, analyzed_at
           FROM skill_compat
           WHERE skill_id = ?""",
        (skill_id,),
    ).fetchone()

    if row is None:
        return None

    d = dict(row)
    try:
        d["portable_core"]   = json.loads(d.pop("portable_core_json", "{}") or "{}")
        d["host_overlay"]    = json.loads(d.pop("host_overlay_json", "{}") or "{}")
        d["evidence"]        = json.loads(d.pop("evidence_json", "{}") or "{}")
        d["recommendations"] = json.loads(d.pop("recommendations_json", "[]") or "[]")
    except (json.JSONDecodeError, TypeError):
        pass
    return d
