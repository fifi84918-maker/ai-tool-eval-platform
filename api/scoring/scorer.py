"""Eight-dimension composite scorer (PRD §6.1–6.2).

Architecture
------------
SkillScorer.score(skill, static_result, dynamic_result=None) → ScoreResult

Phase 1 (current): deterministic layer only.
  - Dimensions backed by real data are scored.
  - Dimensions requiring test-run data are returned as None (TODO).
  - No LLM calls (§1.3 deterministic-first rule).

Evidence levels
  A  Full environment snapshot + multi-task repeats + baseline comparison (Phase 2)
  B  Dynamic execution result present (dynamic_result with score)
  C  Static detection passed (most current cases)
  D  Metadata-only (METADATA_ONLY verdict)
  U  Unable to evaluate (no data at all)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from api.scoring.dimensions import DIMENSIONS, empty_dimensions

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class ScoreResult:
    skill_id:       str
    dimensions:     dict[str, Optional[float]] = field(
        default_factory=empty_dimensions
    )
    composite:      Optional[float] = None   # weighted average of non-None dims
    evidence_level: str = "U"               # A/B/C/D/U
    sample_size:    int = 0                  # test-run count (0 = static only)
    valid_until:    Optional[str] = None     # ISO-8601 expiry (Phase 2)
    uplift:         Optional[float] = None   # vs baseline (Phase 2)

    def to_dict(self) -> dict:
        return {
            "skill_id":       self.skill_id,
            "dimensions":     self.dimensions,
            "composite":      self.composite,
            "evidence_level": self.evidence_level,
            "sample_size":    self.sample_size,
            "valid_until":    self.valid_until,
            "uplift":         self.uplift,
        }


# ---------------------------------------------------------------------------
# Evidence level
# ---------------------------------------------------------------------------

def get_evidence_level(static_result=None, dynamic_result=None) -> str:
    """Derive evidence level from available results (§6.2).

    A: Phase 2 only — full env snapshot + multi-task repeats (not yet)
    B: dynamic_result present with a real score
    C: static checks passed (verdict REVIEWED)
    D: METADATA_ONLY
    U: nothing usable
    """
    # Phase 2 evidence A: not yet supported
    # 'A' would require test_runs data with sample_size >= threshold

    if dynamic_result is not None:
        score = getattr(dynamic_result, "score", None)
        if score is not None:
            return "B"

    if static_result is not None:
        verdict = getattr(static_result, "verdict", None)
        if verdict == "METADATA_ONLY":
            return "D"
        if verdict in ("REVIEWED", "QUARANTINE"):
            # QUARANTINE still produces a static result, just negative
            return "C"

    return "U"


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------

def _score_task_effect(
    dynamic_result=None,
    static_result=None,
) -> Optional[float]:
    """task_effect (35%): Dynamic score if available; static structure fallback.

    TODO (Phase 2): replace static fallback with real task-completion metrics.
    """
    if dynamic_result is not None:
        dyn_score = getattr(dynamic_result, "score", None)
        if dyn_score is not None:
            # Dynamic score already 0-100
            return float(dyn_score)

    # Static fallback: code block syntax validity from static_result
    if static_result is not None:
        verdict = getattr(static_result, "verdict", None)
        if verdict == "QUARANTINE":
            return 20.0   # blocked skill gets very low task-effect base
        if verdict == "METADATA_ONLY":
            return None   # no content to evaluate
        # REVIEWED: gave basic structural pass → base score 55
        # Bonus: doc completeness passed → +10; frontmatter valid → +10
        score = 55.0
        checks = getattr(static_result, "checks", [])
        for c in checks:
            name = getattr(c, "name", "")
            passed = getattr(c, "passed", False)
            if name == "quality.doc_completeness" and passed:
                score += 10.0
            if name == "structure.frontmatter_valid" and passed:
                score += 10.0
        return min(score, 100.0)

    return None


def _score_stability(dynamic_result=None) -> Optional[float]:
    """stability (15%): Repeat-run pass rate.

    TODO (Phase 2): compute from test_runs table (repeat × pass_count).
    """
    # Phase 2: return repeat_pass_rate × 100 when test_runs available
    return None


def _score_trigger_quality(static_result=None, skill_md: str = "") -> Optional[float]:
    """trigger_quality (10%): Prompt/keyword completeness from static analysis.

    Checks:
    - frontmatter has name + description (required)
    - description length ≥ 30 chars
    - SKILL.md has usage/example section or code block
    - name looks like a natural trigger phrase (not too short, no special chars)
    """
    if static_result is None and not skill_md:
        return None

    score = 0.0
    total = 0.0

    # (a) frontmatter valid check  (40 pts)
    total += 40.0
    if static_result is not None:
        checks = getattr(static_result, "checks", [])
        fm_check = next(
            (c for c in checks if getattr(c, "name", "") == "structure.frontmatter_valid"),
            None,
        )
        if fm_check and getattr(fm_check, "passed", False):
            score += 40.0

    # (b) description length ≥ 30 chars  (20 pts)
    total += 20.0
    desc = _extract_frontmatter_field(skill_md, "description")
    if desc and len(desc.strip()) >= 30:
        score += 20.0

    # (c) usage/example section  (20 pts)
    total += 20.0
    if skill_md and re.search(
        r"#+\s*(usage|example|how.to|demo|sample)", skill_md, re.IGNORECASE
    ):
        score += 20.0
    elif skill_md and "```" in skill_md:
        score += 10.0   # partial credit: has code block

    # (d) sensible name  (20 pts)
    total += 20.0
    name = _extract_frontmatter_field(skill_md, "name")
    if name and len(name.strip()) >= 3 and re.match(r"^[\w\s\-]+$", name.strip()):
        score += 20.0

    if total == 0:
        return None
    return round((score / total) * 100, 1)


def _score_permission_privacy(static_result=None) -> Optional[float]:
    """permission_privacy (10%): Inverse mapping from risk_flags.

    block flag present → low score; warn only → moderate; clean → high.
    """
    if static_result is None:
        return None

    risk_flags = getattr(static_result, "risk_flags", [])

    # Count by severity
    block_count = sum(1 for f in risk_flags if f.get("severity") == "block")
    warn_count  = sum(1 for f in risk_flags if f.get("severity") == "warn")

    if block_count > 0:
        # Each block flag costs 25 pts, minimum 10
        return max(10.0, 100.0 - block_count * 25.0)
    if warn_count > 0:
        return max(50.0, 100.0 - warn_count * 10.0)
    return 100.0


def _score_cost_efficiency() -> Optional[float]:
    """cost_efficiency (10%): Token/latency cost per task.

    TODO (Phase 2): derive from test_runs.cost_info data.
    """
    return None


def _score_platform_compat() -> Optional[float]:
    """platform_compat (10%): Platform coverage tested vs declared.

    TODO (Phase 1 P1): populate from platform_test_results table.
    """
    return None


def _score_maintainability(static_result=None) -> Optional[float]:
    """maintainability (5%): Doc structure + versioning signals."""
    if static_result is None:
        return None

    verdict = getattr(static_result, "verdict", None)
    if verdict == "METADATA_ONLY":
        return None

    checks = getattr(static_result, "checks", [])
    doc_check = next(
        (c for c in checks if getattr(c, "name", "") == "quality.doc_completeness"),
        None,
    )
    req_check = next(
        (c for c in checks if getattr(c, "name", "") == "structure.required_files"),
        None,
    )

    score = 40.0  # baseline
    if req_check and getattr(req_check, "passed", False):
        score += 30.0
    if doc_check and getattr(doc_check, "passed", False):
        score += 30.0
    return score


def _score_doc_explainability(static_result=None, skill_md: str = "") -> Optional[float]:
    """doc_explainability (5%): Clarity and completeness of SKILL.md."""
    if not skill_md:
        return None if static_result is None else 10.0

    score = 0.0

    # Has SKILL.md content at all
    score += 20.0

    # Has frontmatter with name + description
    if static_result is not None:
        checks = getattr(static_result, "checks", [])
        fm_check = next(
            (c for c in checks if getattr(c, "name", "") == "structure.frontmatter_valid"),
            None,
        )
        if fm_check and getattr(fm_check, "passed", False):
            score += 25.0

    # Has multiple sections (## headings)
    heading_count = len(re.findall(r"^#{1,3}\s+\w", skill_md, re.MULTILINE))
    if heading_count >= 3:
        score += 25.0
    elif heading_count >= 1:
        score += 10.0

    # Has a code example
    if "```" in skill_md:
        score += 30.0

    return min(score, 100.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_frontmatter_field(skill_md: str, field_name: str) -> Optional[str]:
    """Extract a single field from YAML frontmatter."""
    if not skill_md or not skill_md.strip().startswith("---"):
        return None
    try:
        import yaml
        lines = skill_md.split("\n")
        fm_lines = []
        for line in lines[1:]:
            if line.strip() == "---":
                break
            fm_lines.append(line)
        parsed = yaml.safe_load("\n".join(fm_lines)) or {}
        val = parsed.get(field_name)
        return str(val) if val is not None else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

class SkillScorer:
    """Compute 8-dimension composite score for a skill.

    Operates on static + optional dynamic results — no LLM calls (§1.3).
    Dimensions lacking data return None; composite uses only non-None dims.
    """

    def score(
        self,
        skill: dict,
        static_result=None,
        dynamic_result=None,
    ) -> ScoreResult:
        """Compute ScoreResult for ``skill``.

        Parameters
        ----------
        skill : dict
            Must contain at least ``skill_id``.
            Optional keys: ``skill_md`` (str).
        static_result : StaticResult | None
        dynamic_result : DynamicResult | None
        """
        skill_id = skill.get("skill_id", "unknown")
        skill_md = skill.get("skill_md", "") or ""

        result = ScoreResult(skill_id=skill_id)

        # ----- Compute each dimension ----------------------------------------
        dims: dict[str, Optional[float]] = {}

        dims["task_effect"] = _score_task_effect(dynamic_result, static_result)
        dims["stability"]   = _score_stability(dynamic_result)
        dims["trigger_quality"] = _score_trigger_quality(static_result, skill_md)
        dims["permission_privacy"] = _score_permission_privacy(static_result)
        dims["cost_efficiency"] = _score_cost_efficiency()
        dims["platform_compat"] = _score_platform_compat()
        dims["maintainability"] = _score_maintainability(static_result)
        dims["doc_explainability"] = _score_doc_explainability(static_result, skill_md)

        # D-level evidence → hide dynamic-dependent dimensions (§6.2)
        evidence = get_evidence_level(static_result, dynamic_result)
        if evidence == "D":
            dims["task_effect"]  = None
            dims["stability"]    = None
            dims["trigger_quality"] = None

        result.dimensions = dims

        # ----- Composite (weighted average over non-None dims) ---------------
        result.composite = self._compute_composite(dims)

        # ----- Evidence level ------------------------------------------------
        result.evidence_level = evidence

        # ----- Metadata -------------------------------------------------------
        result.sample_size = 0  # TODO Phase 2: from test_runs
        result.valid_until = None  # TODO Phase 2: set TTL from scoring date
        result.uplift = None   # TODO Phase 2: vs baseline

        logger.info(
            "scored skill=%s composite=%.1f evidence=%s",
            skill_id[:12],
            result.composite or 0,
            result.evidence_level,
        )
        return result

    @staticmethod
    def _compute_composite(dims: dict[str, Optional[float]]) -> Optional[float]:
        """Weighted average of dimensions that have data (non-None)."""
        earned = 0.0
        weight_sum = 0.0
        for dim_name, value in dims.items():
            if value is not None:
                w = DIMENSIONS.get(dim_name, 0.0)
                earned += value * w
                weight_sum += w

        if weight_sum == 0:
            return None
        return round(earned / weight_sum, 1)
