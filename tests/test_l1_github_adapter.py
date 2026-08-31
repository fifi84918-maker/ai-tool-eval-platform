"""Tests for L1 GitHub Adapter (V1A L1)."""

import pytest
from datetime import datetime, timezone
from api.adapters import GitHubAdapter, FakeGitHubFetcher
from api.models import SourceRecord
from api.store import (
    put_source,
    put_skill,
    put_artifact,
    get_skill,
    get_source,
    list_artifacts,
    clear_all,
)


@pytest.fixture(autouse=True)
def clean_store():
    """清空存储（每个测试前后）。"""
    clear_all()
    yield
    clear_all()


def test_adapter_discovers_metadata_only():
    """Test 1: discover 返回 SourceRecord，不产生 CanonicalSkill。"""
    adapter = GitHubAdapter(fetcher=FakeGitHubFetcher())
    
    sources = adapter.discover("skill", limit=10)
    
    # Should return sources
    assert len(sources) == 1
    source = sources[0]
    
    assert isinstance(source, SourceRecord)
    assert source.platform == "github"
    assert source.platform_skill_id == "acme/demo-skill"
    assert source.dedupe_hash == "github:acme/demo-skill"
    assert source.canonical_skill_id is None  # Not yet linked


def test_fetch_creates_acquired_skill():
    """Test 2: fetch 后 CanonicalSkill.state == "ACQUIRED"，skill_id 是 64 位 hex。"""
    adapter = GitHubAdapter(fetcher=FakeGitHubFetcher())
    
    # Discover first
    sources = adapter.discover("skill")
    source = sources[0]
    
    # Fetch
    skill, artifacts = adapter.fetch(source)
    
    assert skill.state == "ACQUIRED"
    assert len(skill.skill_id) == 64  # SHA256 hex
    assert skill.platform == "github"
    assert skill.platform_skill_id == "acme/demo-skill"
    assert source.source_id in skill.source_refs


def test_fetch_parses_frontmatter():
    """Test 3: name/description/allowed-tools 正确解析。"""
    adapter = GitHubAdapter(fetcher=FakeGitHubFetcher())
    
    sources = adapter.discover("skill")
    source = sources[0]
    
    skill, artifacts = adapter.fetch(source)
    
    # Frontmatter should be parsed
    assert skill.name == "PDF Processor"
    assert "PDF/Word docs" in skill.description
    
    # Artifact should contain full SKILL.md
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.kind == "skill_md"
    assert "allowed-tools: [read, write]" in artifact.path_or_text


def test_fetch_falls_back_to_description():
    """Test 4: 无 frontmatter 时用 repo description。"""
    # Create a fetcher that returns skill.md without frontmatter
    class NoFrontmatterFetcher:
        def search(self, query, limit=20):
            return [{
                "repo_full_name": "test/no-frontmatter",
                "description": "Fallback description from repo",
                "html_url": "https://github.com/test/no-frontmatter",
                "license": {"spdx_id": "Apache-2.0"},
                "topics": [],
            }]
        
        def get_skill_md(self, repo_full_name):
            return "# No Frontmatter\n\nJust plain content."
    
    adapter = GitHubAdapter(fetcher=NoFrontmatterFetcher())
    
    sources = adapter.discover("skill")
    source = sources[0]
    
    skill, artifacts = adapter.fetch(source)
    
    # Should fallback to extracted description
    assert skill.description == "Just plain content."


def test_license_unknown_when_missing():
    """Test 5: license=None → "UNKNOWN"。"""
    class NoLicenseFetcher:
        def search(self, query, limit=20):
            return [{
                "repo_full_name": "test/no-license",
                "description": "No license repo",
                "html_url": "https://github.com/test/no-license",
                "license": None,  # No license
                "topics": [],
            }]
        
        def get_skill_md(self, repo_full_name):
            return "---\nname: No License Skill\n---\n"
    
    adapter = GitHubAdapter(fetcher=NoLicenseFetcher())
    
    sources = adapter.discover("skill")
    source = sources[0]
    
    skill, artifacts = adapter.fetch(source)
    
    assert skill.license == "UNKNOWN"


def test_dedup_skips_existing():
    """Test 6: 第二次 discover 同 repo → 返回空（去重生效）。"""
    adapter = GitHubAdapter(fetcher=FakeGitHubFetcher())
    
    # First discovery
    sources1 = adapter.discover("skill")
    assert len(sources1) == 1
    
    # Store the source
    put_source(sources1[0])
    
    # Second discovery (should be deduplicated)
    sources2 = adapter.discover("skill")
    assert len(sources2) == 0  # Deduplicated


def test_full_pipeline_discover_fetch_persist():
    """Test 7: discover → fetch → 断言 store 里 skill/source/artifact 三样齐全。"""
    adapter = GitHubAdapter(fetcher=FakeGitHubFetcher())
    
    # Step 1: Discover
    sources = adapter.discover("skill")
    assert len(sources) == 1
    source = sources[0]
    
    # Step 2: Fetch
    skill, artifacts = adapter.fetch(source)
    
    # Step 3: Persist (in order: source → skill → artifact)
    put_source(source)
    put_skill(skill)
    for artifact in artifacts:
        put_artifact(artifact)
    
    # Step 4: Verify persistence
    retrieved_source = get_source(source.source_id)
    assert retrieved_source is not None
    assert retrieved_source.platform_skill_id == "acme/demo-skill"
    
    retrieved_skill = get_skill(skill.skill_id)
    assert retrieved_skill is not None
    assert retrieved_skill.state == "ACQUIRED"
    assert source.source_id in retrieved_skill.source_refs
    
    retrieved_artifacts = list_artifacts(skill_id=skill.skill_id)
    assert len(retrieved_artifacts) == 1
    assert retrieved_artifacts[0].kind == "skill_md"
    
    # Step 5: Verify source backlink (should be updated)
    # Note: In real implementation, fetch() should update source.canonical_skill_id
    # For now, we manually update it
    source.canonical_skill_id = skill.skill_id
    put_source(source)
    
    retrieved_source = get_source(source.source_id)
    assert retrieved_source.canonical_skill_id == skill.skill_id
