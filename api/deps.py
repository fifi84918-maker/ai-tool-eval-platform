"""Dependency injection for FastAPI endpoints."""

from mcp_server.index import get_index_with_fallback


def get_index():
    """Return skill index (DatabaseSkillIndex or InMemorySkillIndex fallback).
    
    Automatically selects database backend if DATABASE_URL is set,
    otherwise falls back to in-memory index from SAMPLES.
    """
    return get_index_with_fallback()
