"""api/scoring package — static, dynamic, composite, and compatibility scoring."""
from api.scoring.dynamic import DynamicExecutor, DynamicResult, CheckResult
from api.scoring.static_check import StaticChecker, StaticResult, CheckDetail
from api.scoring.dimensions import DIMENSIONS, dim_weight, dim_names, empty_dimensions
from api.scoring.scorer import SkillScorer, ScoreResult, get_evidence_level
from api.scoring.compat import (
    CompatAnalyzer, CompatResult,
    PortableCoreProfile, HostOverlayReport, CompatEvidence,
)

__all__ = [
    "DynamicExecutor", "DynamicResult", "CheckResult",
    "StaticChecker", "StaticResult", "CheckDetail",
    "DIMENSIONS", "dim_weight", "dim_names", "empty_dimensions",
    "SkillScorer", "ScoreResult", "get_evidence_level",
    "CompatAnalyzer", "CompatResult",
    "PortableCoreProfile", "HostOverlayReport", "CompatEvidence",
]
