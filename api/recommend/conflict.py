"""Conflict detection for skill recommendation pools (PRD §7).

Two conflict types:
  version  — same canonical_name, multiple entries
  overlap  — target_domains Jaccard similarity ≥ threshold (default 0.7)

Phase 1: deterministic set-based Jaccard; no LLM (§1.3).
Phase 2 TODO: semantic similarity for description overlap.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import combinations
from typing import Literal

logger = logging.getLogger(__name__)

ConflictType = Literal["version", "overlap"]

OVERLAP_THRESHOLD = 0.7  # Jaccard coefficient threshold for domain overlap


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Conflict:
    """A single detected conflict between skills."""
    type:   ConflictType
    items:  list[str]      # skill_id list involved
    reason: str = ""

    def to_dict(self) -> dict:
        return {"type": self.type, "items": self.items, "reason": self.reason}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity coefficient for two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union        = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _normalise_name(name: str | None) -> str | None:
    """Normalise skill name for comparison (strip, lowercase)."""
    if not name:
        return None
    return name.strip().lower()


# ---------------------------------------------------------------------------
# ConflictDetector
# ---------------------------------------------------------------------------

class ConflictDetector:
    """Detect version and overlap conflicts in a skill pool.

    Parameters
    ----------
    overlap_threshold : float
        Jaccard threshold for target_domains overlap detection.
        Default: 0.7.
    """

    def __init__(self, overlap_threshold: float = OVERLAP_THRESHOLD) -> None:
        self.overlap_threshold = overlap_threshold

    def detect(self, skills: list[dict]) -> list[Conflict]:
        """Detect all conflicts in ``skills`` list.

        Each skill dict should contain:
          skill_id       str
          canonical_name str | None   (for version conflicts)
          target_domains list[str]    (for overlap detection)

        Returns list of Conflict objects; [] when no conflicts found.
        """
        if len(skills) < 2:
            return []

        conflicts: list[Conflict] = []
        conflicts.extend(self._detect_version_conflicts(skills))
        conflicts.extend(self._detect_overlap_conflicts(skills))
        return conflicts

    # ------------------------------------------------------------------

    def _detect_version_conflicts(self, skills: list[dict]) -> list[Conflict]:
        """Group by canonical_name; if >1 entry → version conflict."""
        name_map: dict[str, list[str]] = {}
        for s in skills:
            name = _normalise_name(s.get("canonical_name") or s.get("name"))
            if not name:
                continue
            name_map.setdefault(name, []).append(s["skill_id"])

        result: list[Conflict] = []
        for name, ids in name_map.items():
            if len(ids) > 1:
                result.append(Conflict(
                    type="version",
                    items=ids,
                    reason=f"Multiple entries with canonical name '{name}' ({len(ids)} versions)",
                ))
        return result

    def _detect_overlap_conflicts(self, skills: list[dict]) -> list[Conflict]:
        """Pairwise Jaccard on target_domains; report pairs above threshold."""
        result: list[Conflict] = []

        # Only consider skills that have at least one domain
        domain_map: dict[str, set[str]] = {}
        for s in skills:
            sid     = s.get("skill_id", "")
            domains = s.get("target_domains") or []
            if isinstance(domains, str):
                import json as _json
                try:
                    domains = _json.loads(domains)
                except Exception:
                    domains = []
            domain_set = {str(d).strip().lower() for d in domains if d}
            if domain_set:
                domain_map[sid] = domain_set

        ids = list(domain_map.keys())
        for id_a, id_b in combinations(ids, 2):
            score = _jaccard(domain_map[id_a], domain_map[id_b])
            if score >= self.overlap_threshold:
                result.append(Conflict(
                    type="overlap",
                    items=[id_a, id_b],
                    reason=(
                        f"target_domains overlap (Jaccard={score:.2f}): "
                        f"{sorted(domain_map[id_a] & domain_map[id_b])}"
                    ),
                ))
        return result
