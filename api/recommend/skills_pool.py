"""Skills pool loader for the recommendation engine (PRD §7).

Reads composite scores + compat status from the SQLite cache tables
(skill_scores JOIN skill_compat JOIN skills).

Never re-runs scoring or compat analysis — read-only, cache-only.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from api.db.database import get_conn

logger = logging.getLogger(__name__)


def _ensure_aux_tables() -> None:
    """Lazily create skill_scores and skill_compat if they don't exist yet."""
    from api.db.score_store import _ensure_scores_table
    from api.db.compat_store import _ensure_compat_table
    _ensure_scores_table()
    _ensure_compat_table()


def load_skill_pool(limit: int = 200) -> list[dict]:
    """Return a flat list of skill dicts ready for RecommendRanker.

    Each dict contains:
      skill_id        str
      name            str
      canonical_name  str | None
      description     str
      target_domains  list[str]
      composite       float | None
      evidence_level  str | None
      compat_status   str
      status          str          (V1E lifecycle status)
      platform        str

    Joins skill_scores + skill_compat onto skills so callers see
    one denormalised row per skill. Skills without any score record
    are still included (composite=None → evidence_fallback in ranker).
    """
    _ensure_aux_tables()
    conn = get_conn()

    # LEFT JOIN so skills without scores/compat are still returned
    rows = conn.execute(
        """
        SELECT
            s.skill_id,
            s.name,
            s.canonical_name,
            s.description,
            s.target_domains,
            s.platform,
            s.status,
            COALESCE(sc.compat_status, s.compat_status, 'UNKNOWN') AS compat_status,
            ss.composite,
            ss.evidence_level,
            ss.sample_size
        FROM skills s
        LEFT JOIN skill_scores  ss ON ss.skill_id = s.skill_id
        LEFT JOIN skill_compat  sc ON sc.skill_id = s.skill_id
        ORDER BY ss.composite DESC NULLS LAST
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    result: list[dict] = []
    for row in rows:
        d = dict(row)
        # Deserialise JSON target_domains
        td = d.get("target_domains")
        if isinstance(td, str):
            try:
                d["target_domains"] = json.loads(td)
            except (json.JSONDecodeError, TypeError):
                d["target_domains"] = []
        elif td is None:
            d["target_domains"] = []
        result.append(d)

    return result
