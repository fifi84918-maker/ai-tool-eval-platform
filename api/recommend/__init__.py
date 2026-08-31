"""api/recommend — compat-weighted ranking + conflict detection (PRD §7)."""
from api.recommend.ranker import RecommendRanker, COMPAT_WEIGHTS
from api.recommend.conflict import ConflictDetector, Conflict

__all__ = ["RecommendRanker", "COMPAT_WEIGHTS", "ConflictDetector", "Conflict"]
