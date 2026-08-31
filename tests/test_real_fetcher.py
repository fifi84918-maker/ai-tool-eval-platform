"""Tests for RealGitHubFetcher (V1A real-data)."""

import pytest
import os
from api.adapters import RealGitHubFetcher


def test_real_fetcher_requires_token():
    """Test 1: RealGitHubFetcher 需要 GITHUB_TOKEN。"""
    # Save current token if exists
    original_token = os.environ.get("GITHUB_TOKEN")
    
    try:
        # Remove token
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            RealGitHubFetcher()
    
    finally:
        # Restore original token
        if original_token:
            os.environ["GITHUB_TOKEN"] = original_token


@pytest.mark.integration
def test_real_fetcher_search_returns_results():
    """Test 2: RealGitHubFetcher.search 返回真实结果。
    
    Requires GITHUB_TOKEN environment variable.
    Marked as @pytest.mark.integration - skip in CI without token.
    """
    # Check if token is available
    if not os.environ.get("GITHUB_TOKEN"):
        pytest.skip("GITHUB_TOKEN not set, skipping integration test")
    
    # Create fetcher
    fetcher = RealGitHubFetcher()
    
    # Search
    results = fetcher.search("pdf", limit=2)
    
    # Verify results
    assert isinstance(results, list)
    assert len(results) <= 2
    
    # Verify structure
    if results:
        result = results[0]
        assert "repo_full_name" in result
        assert "description" in result
        assert "html_url" in result
        assert "topics" in result
        
        # Verify repo_full_name format
        assert "/" in result["repo_full_name"]
        
        # Verify URL format
        assert result["html_url"].startswith("https://github.com/")


@pytest.mark.integration
def test_real_fetcher_get_skill_md():
    """Test 3: RealGitHubFetcher.get_skill_md 读取文件。
    
    Tests against a known public repository (if available).
    Marked as @pytest.mark.integration.
    """
    if not os.environ.get("GITHUB_TOKEN"):
        pytest.skip("GITHUB_TOKEN not set, skipping integration test")
    
    fetcher = RealGitHubFetcher()
    
    # Try to fetch from a test repo (this will fail if SKILL.md doesn't exist)
    # We test the mechanism, not necessarily success
    result = fetcher.get_skill_md("octocat/Hello-World")
    
    # Result should be None (no SKILL.md) or a string
    assert result is None or isinstance(result, str)
