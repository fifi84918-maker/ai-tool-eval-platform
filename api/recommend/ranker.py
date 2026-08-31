"""Compat-weighted skill ranker (PRD §7).

rank_score = composite × compat_weight × (1 + context_boost)

Phase 1 simplifications:
  - context_boost = 0   (TODO: wire user profile when available)
  - compat_weight is a fixed lookup table (TODO: make dynamic in Phase 2)
  - composite = None  → evidence_level fallback score
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compat weight table  (§7 spec)
# ---------------------------------------------------------------------------

COMPAT_WEIGHTS: dict[str, float] = {
    "COMPATIBLE":              1.00,
    "COMPATIBLE_WITH_ADAPTER": 0.85,
    "PARTIAL":                 0.60,
    "PENDING_VERIFICATION":    0.50,
    "UNKNOWN":                 0.30,
    "INCOMPATIBLE":            0.00,   # excluded from pool
    "BLOCKED":                 0.00,   # excluded and flagged
}

# Evidence-level fallback composite scores (when composite is None)
_EVIDENCE_FALLBACK: dict[str, float] = {
    "A": 80.0,
    "B": 60.0,
    "C": 40.0,
    "D": 20.0,
    "U":  0.0,
}


# ---------------------------------------------------------------------------
# RecommendRanker
# ---------------------------------------------------------------------------

class RecommendRanker:
    """Rank a pool of skill dicts by compat-weighted composite score.

    Each input skill dict may contain:
      skill_id        str
      composite       float | None   (from ScoreResult)
      evidence_level  str | None     (A/B/C/D/U)
      compat_status   str | None     (7-state)

    Each output skill dict is the original plus:
      rank_score      float
      compat_weight   float
      excluded        bool    (True when compat_weight == 0)
      score_source    str     ('composite' | 'evidence_fallback' | 'zero')
    """

    def rank(
        self,
        skills: list[dict],
        context: dict | None = None,  # TODO Phase 2: user profile / context
    ) -> list[dict]:
        """Return skills sorted by rank_score descending.

        Skills with compat_weight == 0 are NOT removed here — they are
        marked excluded=True so callers can filter them as needed.
        The router applies the include_blocked filter.
        """
        if not skills:
            return []

        # TODO Phase 2: derive context_boost from user profile
        context_boost: float = 0.0

        ranked: list[dict] = []
        for skill in skills:
            s = dict(skill)  # don't mutate caller's dict

            compat_status = s.get("compat_status") or "UNKNOWN"
            compat_weight = COMPAT_WEIGHTS.get(compat_status, COMPAT_WEIGHTS["UNKNOWN"])

            composite = s.get("composite")
            evidence_level = (s.get("evidence_level") or "U").upper()

            if composite is None:
                # Evidence-level fallback
                fallback = _EVIDENCE_FALLBACK.get(evidence_level, 0.0)
                s["rank_score"]   = round(fallback * compat_weight * (1 + context_boost), 2)
                s["score_source"] = "evidence_fallback"
            else:
                s["rank_score"]   = round(float(composite) * compat_weight * (1 + context_boost), 2)
                s["score_source"] = "composite"

            s["compat_weight"] = compat_weight
            s["excluded"]      = (compat_weight == 0.0)
            ranked.append(s)

        ranked.sort(key=lambda x: x["rank_score"], reverse=True)
        return ranked
