"""Eight-dimension scoring constants and weight table (PRD §6.2).

Dimension names, weights, and short descriptions for the composite score.
All weights sum to exactly 1.0.

Usage::

    from api.scoring.dimensions import DIMENSIONS, dim_weight, dim_names

    # Access weight for a dimension
    w = dim_weight("task_effect")  # 0.35

    # Verify invariant
    assert abs(sum(DIMENSIONS.values()) - 1.0) < 1e-9
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical dimension registry
# Keys are stable identifiers used throughout the codebase.
# Values are float weights (must sum to 1.0).
# ---------------------------------------------------------------------------

DIMENSIONS: dict[str, float] = {
    "task_effect":         0.35,  # 任务效果 — primary quality signal
    "stability":           0.15,  # 稳定性   — repeat-run pass rate
    "trigger_quality":     0.10,  # 触发质量 — prompt/keyword completeness
    "permission_privacy":  0.10,  # 权限与隐私 — risk-flag inverse score
    "cost_efficiency":     0.10,  # 成本效率 — token / latency cost
    "platform_compat":     0.10,  # 平台兼容性 — tested platform coverage
    "maintainability":     0.05,  # 可维护性 — doc structure + versioning
    "doc_explainability":  0.05,  # 文档可解释性 — clarity of SKILL.md
}

# Sanity check at import time — catches copy-paste weight errors immediately
_weight_sum = sum(DIMENSIONS.values())
assert abs(_weight_sum - 1.0) < 1e-9, (
    f"DIMENSIONS weights must sum to 1.0, got {_weight_sum}"
)

# ---------------------------------------------------------------------------
# Dimension metadata (display name + short description)
# ---------------------------------------------------------------------------

DIM_META: dict[str, dict[str, str]] = {
    "task_effect": {
        "label":       "Task Effect",
        "description": "How well the skill completes its declared task (dynamic eval)",
        "data_source": "dynamic_result.score",
    },
    "stability": {
        "label":       "Stability",
        "description": "Consistency across multiple repeated runs",
        "data_source": "TODO: test_runs repeat pass-rate",  # Phase 2
    },
    "trigger_quality": {
        "label":       "Trigger Quality",
        "description": "Quality and completeness of trigger keywords / prompts",
        "data_source": "static: frontmatter name + description + triggers",
    },
    "permission_privacy": {
        "label":       "Permission & Privacy",
        "description": "Absence of dangerous permissions and credential leaks",
        "data_source": "static: risk_flags (inverse mapping)",
    },
    "cost_efficiency": {
        "label":       "Cost Efficiency",
        "description": "Token cost and latency efficiency per task",
        "data_source": "TODO: test_runs cost_info",  # Phase 2
    },
    "platform_compat": {
        "label":       "Platform Compatibility",
        "description": "Coverage of target platforms declared vs tested",
        "data_source": "TODO: platform_test_results",  # Phase 1 P1
    },
    "maintainability": {
        "label":       "Maintainability",
        "description": "Documentation structure, versioning, and changelog",
        "data_source": "static: quality.doc_completeness",
    },
    "doc_explainability": {
        "label":       "Doc Explainability",
        "description": "Clarity and completeness of SKILL.md explanation",
        "data_source": "static: SKILL.md section analysis",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dim_weight(name: str) -> float:
    """Return the weight for a dimension; raises KeyError if unknown."""
    return DIMENSIONS[name]


def dim_names() -> list[str]:
    """Return dimension names in canonical order (descending weight)."""
    return list(DIMENSIONS.keys())


def empty_dimensions() -> dict[str, float | None]:
    """Return a dict of all dimensions set to None (no data available)."""
    return {k: None for k in DIMENSIONS}
