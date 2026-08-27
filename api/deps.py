"""Dependency injection for FastAPI endpoints."""

from mcp_server.index import InMemorySkillIndex
from scripts.samples import SAMPLES


def get_index() -> InMemorySkillIndex:
    """Return shared InMemorySkillIndex instance (singleton pattern)."""
    return InMemorySkillIndex(SAMPLES)
