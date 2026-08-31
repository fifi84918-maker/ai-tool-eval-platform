"""Tests for L4 Benchmark Scorer (V1A L4)."""

import pytest
import json
from datetime import datetime, timezone
from api.adapters import GitHubAdapter
from api.scanners import static_scan_skill
from api.scorer import score_skill, score_all_reviewed
from api.store import (
    get_skill,
    list_artifacts,
    put_skill,
    put_artifact,
    clear_all,
)
from api.models import CanonicalSkill, ArtifactRecord


@pytest.fixture(autouse=True)
def clean_store():
    """清空存储（每个测试前后）。"""
    clear_all()
    yield
    clear_all()


def create_static_reviewed_skill(
    content: str,
    repo_name: str = "test/skill",
    license: str = "MIT",
    description: str = "A test skill",
    domains: list = None
) -> str:
    """Helper: 创建 STATIC_REVIEWED 状态的 skill。
    
    Returns:
        skill_id
    """
    # Use custom fetcher
    class CustomFetcher:
        def __init__(self, repo_name, content, license, description):
            self.repo_name = repo_name
            self.content = content
            self.license_info = license
            self.description_text = description
        
        def search(self, query, limit=20):
            return [{
                "repo_full_name": self.repo_name,
                "description": self.description_text,
                "html_url": f"https://github.com/{self.repo_name}",
                "license": {"spdx_id": self.license_info} if self.license_info else None,
                "topics": domains or [],
            }]
        
        def get_skill_md(self, repo_full_name):
            return self.content
    
    adapter = GitHubAdapter(fetcher=CustomFetcher(repo_name, content, license, description))
    
    # Discover and fetch (creates ACQUIRED)
    sources = adapter.discover("test")
    source = sources[0]
    skill, artifacts = adapter.fetch(source)
    
    # Scan (transitions to STATIC_REVIEWED)
    static_scan_skill(skill.skill_id)
    
    return skill.skill_id


def test_score_basic_github_skill():
    """Test 1: github 来源 + license + 长 description + domains → 100 分。"""
    content = """---
name: Perfect Skill
description: This is a very long description with more than fifty characters to qualify for the bonus
---

# Perfect Skill
"""
    skill_id = create_static_reviewed_skill(
        content=content,
        repo_name="test/perfect",
        license="MIT",
        description="This is a very long description with more than fifty characters to qualify for the bonus",
        domains=["documentation", "pdf"]
    )
    
    # Verify initial state
    skill = get_skill(skill_id)
    assert skill.state == "STATIC_REVIEWED"
    assert skill.benchmark_score is None  # Not yet scored
    
    # Score
    result = score_skill(skill_id)
    
    # Verify result
    assert result["decision"] == "RUNNABLE"
    assert result["benchmark_score"] == 100.0  # 70+10+10+5+5=100
    
    # Verify components
    components = result["components"]
    assert components["base"] == 70.0
    assert components["platform_bonus"] == 10.0
    assert components["license_bonus"] == 10.0
    assert components["description_bonus"] == 5.0
    assert components["domain_bonus"] == 5.0
    assert components["finding_penalty"] == 0.0
    
    # Verify state transition
    skill = get_skill(skill_id)
    assert skill.state == "RUNNABLE"
    assert skill.benchmark_score == 100.0


def test_score_penalizes_findings():
    """Test 2: 有 3 条 findings → 扣 6 分。"""
    content = """---
name: Test Skill
description: This is a long enough description to get the bonus points
---

# Test skill with documentation and pdf keywords
"""
    skill_id = create_static_reviewed_skill(
        content=content,
        repo_name="test/findings",
        license="MIT",
        description="This is a long enough description to get the bonus points",
        domains=["documentation"]
    )
    
    # Verify initial score components before modifying scan_report
    skill = get_skill(skill_id)
    # Base=70, platform=10, license=10, description=5, domains=5 = 100
    # Then we'll add findings to make it 94
    
    # Manually add scan_report with findings
    scan_artifacts = [a for a in list_artifacts(skill_id) if a.kind == "scan_report"]
    if scan_artifacts:
        # Update existing scan_report
        report = json.loads(scan_artifacts[0].path_or_text)
        report["finding_count"] = 3
        report["findings"] = [
            {"rule_id": "S001", "severity": "low", "message": "Issue 1"},
            {"rule_id": "S002", "severity": "low", "message": "Issue 2"},
            {"rule_id": "S003", "severity": "low", "message": "Issue 3"},
        ]
        scan_artifacts[0].path_or_text = json.dumps(report)
        put_artifact(scan_artifacts[0])
    
    # Score
    result = score_skill(skill_id)
    
    # Expected: 70+10+10+5+5-6 = 94
    assert result["benchmark_score"] == 94.0
    assert result["components"]["finding_penalty"] == -6.0


def test_score_floor_at_zero():
    """Test 3: 大量 findings 扣分 → 封底到 0。"""
    content = "# Test"
    skill_id = create_static_reviewed_skill(
        content=content,
        repo_name="test/floor",
        license=None,  # No license
        description="Short",  # Short description
        domains=[]  # No domains
    )
    
    # Manually add scan_report with many findings
    scan_artifacts = [a for a in list_artifacts(skill_id) if a.kind == "scan_report"]
    if scan_artifacts:
        report = json.loads(scan_artifacts[0].path_or_text)
        report["finding_count"] = 100  # Huge penalty
        scan_artifacts[0].path_or_text = json.dumps(report)
        put_artifact(scan_artifacts[0])
    
    # Score
    result = score_skill(skill_id)
    
    # Should be clamped to 0
    assert result["benchmark_score"] == 0.0
    
    # Verify state still transitions
    skill = get_skill(skill_id)
    assert skill.state == "RUNNABLE"


def test_score_rejects_non_reviewed():
    """Test 4: 对非 STATIC_REVIEWED 状态调用 → ValueError。"""
    # Create ACQUIRED skill (skip scan)
    class CustomFetcher:
        def search(self, query, limit=20):
            return [{
                "repo_full_name": "test/acquired",
                "description": "Test",
                "html_url": "https://github.com/test/acquired",
                "license": {"spdx_id": "MIT"},
                "topics": [],
            }]
        
        def get_skill_md(self, repo_full_name):
            return "# Test"
    
    adapter = GitHubAdapter(fetcher=CustomFetcher())
    sources = adapter.discover("test")
    skill, artifacts = adapter.fetch(sources[0])
    
    # Skill is ACQUIRED, not STATIC_REVIEWED
    assert skill.state == "ACQUIRED"
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="expected STATIC_REVIEWED"):
        score_skill(skill.skill_id)


def test_score_all_reviewed_only_touches_reviewed():
    """Test 5: score_all_reviewed 只处理 STATIC_REVIEWED 状态。"""
    # Create 2 STATIC_REVIEWED skills
    skill_id_1 = create_static_reviewed_skill(
        "# Skill 1",
        repo_name="test/skill1"
    )
    skill_id_2 = create_static_reviewed_skill(
        "# Skill 2",
        repo_name="test/skill2"
    )
    
    # Create 1 ACQUIRED skill
    class CustomFetcher:
        def search(self, query, limit=20):
            return [{
                "repo_full_name": "test/acquired",
                "description": "Test",
                "html_url": "https://github.com/test/acquired",
                "license": {"spdx_id": "MIT"},
                "topics": [],
            }]
        
        def get_skill_md(self, repo_full_name):
            return "# Test"
    
    adapter = GitHubAdapter(fetcher=CustomFetcher())
    sources = adapter.discover("test")
    skill, artifacts = adapter.fetch(sources[0])
    skill_id_3 = skill.skill_id
    
    # Score all
    results = score_all_reviewed()
    
    # Should have processed 2 skills
    successful_results = [r for r in results if "error" not in r]
    assert len(successful_results) == 2
    
    # Verify STATIC_REVIEWED skills became RUNNABLE
    skill_1 = get_skill(skill_id_1)
    skill_2 = get_skill(skill_id_2)
    assert skill_1.state == "RUNNABLE"
    assert skill_2.state == "RUNNABLE"
    assert skill_1.benchmark_score is not None
    assert skill_2.benchmark_score is not None
    
    # Verify ACQUIRED skill unchanged
    skill_3 = get_skill(skill_id_3)
    assert skill_3.state == "ACQUIRED"
    assert skill_3.benchmark_score is None
