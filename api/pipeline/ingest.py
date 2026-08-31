"""Ingest Pipeline Orchestrator for L5 (V1A L5).

Orchestrates: discover → fetch → static-check (V1E) → benchmark-score → [dynamic-check (V1D)]

Stage order (§4.2)
  1. L1 discover  – query → SourceRecord list
  2. L1 fetch     – DISCOVERED → ACQUIRED  (with skill_md / artifacts)
  3. V1E static   – ACQUIRED   → STATIC_REVIEWED | QUARANTINED | METADATA_ONLY
  4. L4 score     – STATIC_REVIEWED → scored  (QUARANTINED skips)
  5. V1D dynamic  – scored (opt-in via DYNAMIC_SCORING=enabled)
"""

import json
import logging
import os
from datetime import datetime, timezone

from api.adapters.github import GitHubAdapter, FakeGitHubFetcher
from api.scanners.static_scan import static_scan_skill
from api.scorer.benchmark import score_skill
from api.store import get_skill, put_skill, list_artifacts, transition_state

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_skill_md(artifacts) -> str:
    """Extract SKILL.md text from an artifact list."""
    for a in (artifacts or []):
        if hasattr(a, "kind") and a.kind in ("skill_md", "SKILL.md"):
            return a.path_or_text or ""
    return ""


def _artifacts_to_dicts(artifacts) -> list[dict]:
    """Convert ArtifactRecord objects to plain dicts for StaticChecker."""
    result = []
    for a in (artifacts or []):
        kind = getattr(a, "kind", "") or ""
        content = getattr(a, "path_or_text", "") or ""
        result.append({"kind": kind, "content": content})
    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(query: str, limit: int = 5, fetcher=None) -> dict:
    """Run complete ingestion pipeline.

    Pipeline stages:
    1. L1 discover: query → SourceRecord + DISCOVERED skills
    2. L1 fetch:    DISCOVERED → ACQUIRED (with skill_md)
    3. V1E static:  ACQUIRED   → STATIC_REVIEWED | QUARANTINED | METADATA_ONLY
    4. L4 score:    STATIC_REVIEWED → scored  (benchmark_score set)
    5. V1D dynamic: STATIC_REVIEWED (opt-in)  → dynamic_score set

    Args:
        query:   Search query
        limit:   Maximum skills to process
        fetcher: Optional custom fetcher (defaults to FakeGitHubFetcher)

    Returns:
        Pipeline report dict
    """
    adapter = GitHubAdapter(fetcher=fetcher or FakeGitHubFetcher())

    report = {
        "query":       query,
        "discovered":  0,
        "acquired":    0,
        "reviewed":    0,
        "quarantined": 0,
        "metadata_only": 0,
        "runnable":    0,
        "errors":      [],
        "skills":      [],
    }

    # ── Stage 1: Discover ───────────────────────────────────────────────────
    try:
        sources = adapter.discover(query, limit=limit)
        report["discovered"] = len(sources)
    except Exception as e:
        report["errors"].append({"stage": "discover", "error": str(e)})
        return report

    # ── Process each source ─────────────────────────────────────────────────
    for source in sources:
        skill_id = None
        try:
            # ── Stage 2: Fetch ──────────────────────────────────────────────
            skill, artifacts = adapter.fetch(source)
            skill_id = skill.skill_id
            report["acquired"] += 1

            # ── Stage 3: V1E Static Check ───────────────────────────────────
            static_result = _run_static_check(skill_id, artifacts)
            # Derive verdict/risk_flags defensively (None = check errored → fail-open)
            static_verdict = getattr(static_result, "verdict", "REVIEWED") if static_result else "REVIEWED"
            risk_flags     = getattr(static_result, "risk_flags", []) if static_result else []

            if static_verdict == "QUARANTINE":
                report["quarantined"] += 1
                skill = get_skill(skill_id)
                # V1F/V1G: score + compat for quarantined skill
                _run_skill_scorer(skill_id, skill, static_result, None, artifacts)
                _run_compat_analysis(skill_id, static_result, None, artifacts)
                report["skills"].append({
                    "skill_id":      skill_id,
                    "name":          skill.name if skill else skill_id,
                    "benchmark_score": None,
                    "dynamic_score": None,
                    "status":        "QUARANTINED",
                    "state":         "QUARANTINED",
                    "risk_flags":    risk_flags,
                })
                continue  # skip scoring for quarantined skills

            if static_verdict == "METADATA_ONLY":
                report["metadata_only"] += 1
                skill = get_skill(skill_id)
                # V1F/V1G: score + compat for metadata-only skill
                _run_skill_scorer(skill_id, skill, static_result, None, artifacts)
                _run_compat_analysis(skill_id, static_result, None, artifacts)
                report["skills"].append({
                    "skill_id":      skill_id,
                    "name":          skill.name if skill else skill_id,
                    "benchmark_score": None,
                    "dynamic_score": None,
                    "status":        "METADATA_ONLY",
                    "state":         "METADATA_ONLY",
                    "risk_flags":    risk_flags,
                })
                continue

            # ── Stage 3b: Legacy L3 scan (for state-machine compatibility) ──
            scan_result = static_scan_skill(skill_id)
            if scan_result["decision"] == "QUARANTINED":
                # Legacy scan overrules — treat as quarantine
                report["quarantined"] += 1
                skill = get_skill(skill_id)
                report["skills"].append({
                    "skill_id":      skill_id,
                    "name":          skill.name if skill else skill_id,
                    "benchmark_score": None,
                    "dynamic_score": None,
                    "status":        "QUARANTINED",
                    "state":         "QUARANTINED",
                    "risk_flags":    risk_flags,
                })
                continue

            report["reviewed"] += 1

            # ── Stage 4: L4 Benchmark Score ──────────────────────────────────
            score_result = score_skill(skill_id)
            report["runnable"] += 1

            skill = get_skill(skill_id)

            # ── Stage 5: V1D Dynamic Check (opt-in) ──────────────────────────
            dynamic_score = None
            dynamic_result = None
            if os.environ.get("DYNAMIC_SCORING", "disabled").lower() == "enabled":
                dynamic_score, dynamic_result = _run_dynamic_check(
                    skill_id, skill, artifacts
                )

            # ── Stage 6: V1F 8-dimension scoring ─────────────────────────────
            _run_skill_scorer(skill_id, skill, static_result, dynamic_result, artifacts)

            # ── Stage 7: V1G Compatibility analysis ──────────────────────────
            _run_compat_analysis(skill_id, static_result, dynamic_result, artifacts)

            report["skills"].append({
                "skill_id":      skill_id,
                "name":          skill.name,
                "benchmark_score": skill.benchmark_score,
                "dynamic_score": dynamic_score,
                "status":        "STATIC_REVIEWED",
                "state":         "RUNNABLE",
                "risk_flags":    risk_flags,
            })

        except Exception as e:
            report["errors"].append({
                "source":   source.platform_skill_id,
                "skill_id": skill_id,
                "error":    str(e),
            })

    return report


# ---------------------------------------------------------------------------
# Internal stage helpers
# ---------------------------------------------------------------------------

def _run_static_check(skill_id: str, artifacts):
    """Run V1E StaticChecker and persist status + risk_flags on the skill.

    Returns the full StaticResult (or None on error).
    Callers use .verdict and .risk_flags from the result.
    """
    try:
        from api.scoring.static_check import StaticChecker
        skill = get_skill(skill_id)
        if skill is None:
            return None

        skill_md = _collect_skill_md(artifacts)
        artifact_dicts = _artifacts_to_dicts(artifacts)

        result = StaticChecker().check({
            "skill_id":      skill_id,
            "skill_md":      skill_md,
            "artifacts":     artifact_dicts,
            "repo_metadata": {},
        })

        # Persist V1E fields back to the DB row (only status/risk_flags/timestamp)
        skill.status      = result.status
        skill.risk_flags  = result.risk_flags
        skill.status_changed_at = datetime.now(timezone.utc)
        put_skill(skill)

        # For QUARANTINE: also drive the legacy `state` machine so that
        # stored_skill.state == "QUARANTINED" (backward-compat with tests).
        # For REVIEWED: do NOT touch state — legacy static_scan_skill will
        # handle the ACQUIRED → STATIC_REVIEWED transition below.
        if result.verdict == "QUARANTINE":
            try:
                transition_state(skill_id, "QUARANTINED",
                                 reason="V1E static check: block rule triggered")
            except Exception:
                pass  # already in target state — safe to ignore

        if result.verdict == "QUARANTINE":
            logger.warning(
                "static_check QUARANTINE skill=%s flags=%s",
                skill_id[:12],
                [f["rule"] for f in result.risk_flags if f.get("severity") == "block"],
            )
        return result

    except Exception as exc:
        logger.warning("static_check error for %s: %s", skill_id, exc)
        return None   # fail-open: let pipeline continue


def _run_dynamic_check(skill_id: str, skill, artifacts) -> tuple:
    """Run V1D DynamicExecutor (opt-in) and persist dynamic_score.

    Returns (dynamic_score: float|None, dyn_result: DynamicResult|None).
    """
    try:
        from api.scoring.dynamic import DynamicExecutor
        skill_md = _collect_skill_md(artifacts)
        dyn_result = DynamicExecutor().run_skill_check({
            "skill_id": skill_id,
            "skill_md": skill_md,
        })
        dynamic_score = dyn_result.score
        if dynamic_score is not None:
            skill.dynamic_score = dynamic_score
            put_skill(skill)
        logger.info(
            "dynamic check skill=%s score=%s duration=%.0fms",
            skill_id[:12], dynamic_score, dyn_result.duration_ms,
        )
        return dynamic_score, dyn_result
    except Exception as exc:
        logger.warning("dynamic check failed for %s: %s", skill_id, exc)
        return None, None


def _run_skill_scorer(
    skill_id: str,
    skill,
    static_result,
    dynamic_result,
    artifacts,
) -> None:
    """V1F: compute 8-dimension composite score and persist to DB."""
    try:
        from api.scoring.scorer import SkillScorer
        from api.db.score_store import upsert_score

        skill_md = _collect_skill_md(artifacts)
        score_result = SkillScorer().score(
            {"skill_id": skill_id, "skill_md": skill_md},
            static_result=static_result,
            dynamic_result=dynamic_result,
        )
        upsert_score(score_result)
        logger.info(
            "v1f score skill=%s composite=%s evidence=%s",
            skill_id[:12],
            score_result.composite,
            score_result.evidence_level,
        )
    except Exception as exc:
        logger.warning("v1f scoring failed for %s: %s", skill_id, exc)


def _run_compat_analysis(
    skill_id: str,
    static_result,
    dynamic_result,
    artifacts,
) -> None:
    """V1G: run CompatAnalyzer and persist result to DB."""
    try:
        from api.scoring.compat import CompatAnalyzer
        from api.db.compat_store import upsert_compat

        skill_md = _collect_skill_md(artifacts)
        artifact_dicts = _artifacts_to_dicts(artifacts)

        compat_result = CompatAnalyzer().analyze(
            {
                "skill_id":   skill_id,
                "skill_md":   skill_md,
                "artifacts":  artifact_dicts,
            },
            static_result=static_result,
            dynamic_result=dynamic_result,
        )
        upsert_compat(compat_result)
        logger.info(
            "v1g compat skill=%s status=%s",
            skill_id[:12], compat_result.compat_status,
        )
    except Exception as exc:
        logger.warning("v1g compat failed for %s: %s", skill_id, exc)
