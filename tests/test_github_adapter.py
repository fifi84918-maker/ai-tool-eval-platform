"""Tests for GitHub source collector."""
import asyncio
from unittest.mock import patch
import pytest
from collector.github_adapter import GitHubCollector, ingest_from_github
from collector.base import AuthenticationError
from db.repository import SourceRepository
from db.models import SourceRecord
MOCK_REPO_RESPONSE = {"full_name": "test/repo", "name": "repo", "description": "Test repo", "owner": {"login": "test"}, "html_url": "https://github.com/test/repo", "private": False, "license": {"spdx_id": "MIT"}, "default_branch": "main"}
MOCK_SEARCH_RESPONSE = {"items": [MOCK_REPO_RESPONSE, {"full_name": "test/repo2", "name": "repo2", "description": None, "owner": {"login": "test2"}, "html_url": "https://github.com/test/repo2", "private": False, "license": None, "default_branch": "master"}]}
def test_discover_parses_search_response():
    collector = GitHubCollector()
    with patch.object(collector, '_make_request', return_value=MOCK_SEARCH_RESPONSE):
        candidates = asyncio.run(collector.discover("test", 10))
    assert len(candidates) == 2
    assert candidates[0].platform_object_id == "test/repo"
    assert candidates[0].skill_name == "repo"
    assert candidates[0].license == "MIT"
    assert candidates[0].author == "test"
    assert candidates[1].license == "unknown"
    assert candidates[1].raw_description == ""
def test_ingest_creates_source_records(db_session):
    with patch('collector.github_adapter.GitHubCollector._make_request', return_value=MOCK_SEARCH_RESPONSE):
        report = asyncio.run(ingest_from_github("test", 10, db_session))
    assert report.created == 2
    assert report.updated == 0
    assert report.skipped == 0
    repo = SourceRepository(db_session)
    source1 = repo.get_by_platform_object("github", "test/repo")
    assert source1 is not None
    assert source1.platform == "github"
    assert source1.acquired is False
    assert source1.license == "MIT"
def test_ingest_is_idempotent(db_session):
    with patch('collector.github_adapter.GitHubCollector._make_request', return_value=MOCK_SEARCH_RESPONSE):
        report1 = asyncio.run(ingest_from_github("test", 10, db_session))
        report2 = asyncio.run(ingest_from_github("test", 10, db_session))
    assert report1.created == 2
    assert report1.updated == 0
    assert report2.created == 0
    assert report2.updated == 2
    sources = db_session.query(SourceRecord).filter_by(platform="github").all()
    assert len(sources) == 2
def test_ingest_handles_403_gracefully(db_session):
    def mock_request_403(url, retry=True):
        raise AuthenticationError("GitHub API auth failed")
    with patch('collector.github_adapter.GitHubCollector._make_request', side_effect=mock_request_403):
        report = asyncio.run(ingest_from_github("test", 10, db_session))
    assert report.created == 0
    assert report.updated == 0
    assert len(report.warnings) > 0
def test_upsert_by_platform_uniqueness(db_session):
    repo = SourceRepository(db_session)
    source1 = repo.upsert_by_platform("github", "test/repo", skill_name="repo1", author="test1", raw_description="desc1", origin_url="http://example.com", acquired=False)
    source2 = repo.upsert_by_platform("github", "test/repo", skill_name="repo2", author="test2", raw_description="desc2", origin_url="http://example.com", acquired=False)
    assert source1.id == source2.id
    assert source2.skill_name == "repo2"
    count = db_session.query(SourceRecord).filter_by(platform="github", platform_object_id="test/repo").count()
    assert count == 1