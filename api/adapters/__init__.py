"""Source Adapters Package for L1 Collectors (V1A L1)."""

from api.adapters.base import SourceAdapter
from api.adapters.github import GitHubAdapter, FakeGitHubFetcher, RealGitHubFetcher
from api.adapters.dedup import compute_dedupe_hash, is_duplicate

__all__ = [
    "SourceAdapter",
    "GitHubAdapter",
    "FakeGitHubFetcher",
    "RealGitHubFetcher",
    "compute_dedupe_hash",
    "is_duplicate",
]
