"""Benchmark isolation tests - verify hidden test set is properly isolated."""

import json
from pathlib import Path

from benchmarks.registry import BenchmarksRegistry
from mcp_server.tools import search_skills, get_skill
from mcp_server.index import InMemorySkillIndex
from scripts.samples import SAMPLES


class TestBenchmarkIsolation:
    """确保评测断言/标准答案不会泄露到公开接口。"""

    def test_benchmarks_in_gitignore(self):
        """验证 benchmarks/ 在 .gitignore 中。"""
        gitignore = Path(".gitignore")
        assert gitignore.exists()
        content = gitignore.read_text(encoding="utf-8")
        assert "benchmarks/" in content

    def test_benchmarks_registry_loads_samples(self):
        """BenchmarksRegistry 能正常加载样本。"""
        registry = BenchmarksRegistry()
        benchmarks = registry.list_benchmarks()
        assert len(benchmarks) > 0
        assert "placeholder-benchmark-001" in benchmarks

    def test_get_benchmark_returns_none_for_unknown_id(self):
        """get_benchmark 对未知 id 返回 None。"""
        registry = BenchmarksRegistry()
        result = registry.get_benchmark("nonexistent-benchmark-id")
        assert result is None

    def test_get_benchmark_returns_case_for_known_id(self):
        """get_benchmark 对已知 id 返回 BenchmarkCase。"""
        registry = BenchmarksRegistry()
        result = registry.get_benchmark("placeholder-benchmark-001")
        assert result is not None
        assert result.skill_id == "placeholder-benchmark-001"
        assert len(result.assertions) > 0
        assert len(result.scoring_weights) > 0

    def test_mcp_search_skills_no_benchmark_leakage(self):
        """MCP search_skills 返回不含评测断言字段。"""
        index = InMemorySkillIndex(SAMPLES)
        result = search_skills(index, "")
        result_str = json.dumps(result, ensure_ascii=False)
        
        # 断言不含评测相关字段
        assert "assertions" not in result_str
        assert "scoring_weights" not in result_str
        assert "payload_hash" not in result_str
        assert "expected" not in result_str.lower() or "matched_expectation" in result_str.lower()  # expected 可能出现在其他合法字段

    def test_mcp_get_skill_no_benchmark_leakage(self):
        """MCP get_skill 返回不含评测断言字段。"""
        index = InMemorySkillIndex(SAMPLES)
        # Get first skill
        search_result = search_skills(index, "")
        skill_id = search_result["results"][0]["skill_id"]
        
        result = get_skill(index, skill_id)
        result_str = json.dumps(result, ensure_ascii=False)
        
        # 断言不含评测相关字段
        assert "assertions" not in result_str
        assert "scoring_weights" not in result_str
        assert "payload_hash" not in result_str

    def test_api_skills_no_benchmark_leakage(self):
        """API /api/v1/skills 返回不含评测断言字段。"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Test search
        response = client.get("/api/v1/skills")
        assert response.status_code == 200
        result_str = json.dumps(response.json(), ensure_ascii=False)
        assert "assertions" not in result_str
        assert "scoring_weights" not in result_str
        assert "payload_hash" not in result_str
        
        # Test detail
        skills_data = response.json()
        if skills_data.get("items"):
            skill_id = skills_data["items"][0]["skill_id"]
            response = client.get(f"/api/v1/skills/{skill_id}")
            assert response.status_code == 200
            result_str = json.dumps(response.json(), ensure_ascii=False)
            assert "assertions" not in result_str
            assert "scoring_weights" not in result_str
            assert "payload_hash" not in result_str
