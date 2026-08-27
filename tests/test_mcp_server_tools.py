"""MCP Server 工具测试：直调 handler + server 注册检查（anyio 跑异步）。无网络。"""

import asyncio
import json
from pathlib import Path

import pytest

from mcp_server.errors import McpToolError
from mcp_server.index import InMemorySkillIndex
from mcp_server.server import TOOL_NAMES, build_server
from mcp_server.tools import (
    get_skill,
    get_skill_artifacts,
    get_trial_report,
    search_skills,
)

_REPORT = Path(__file__).resolve().parent.parent / "reports" / "phase0_trial_report.json"


@pytest.fixture(scope="module")
def index() -> InMemorySkillIndex:
    return InMemorySkillIndex()


class TestRegistration:
    def test_four_tools_registered_on_server(self, index):
        server = build_server(index=index)
        tools = asyncio.run(server.list_tools())
        assert {t.name for t in tools} == TOOL_NAMES == {
            "search_skills",
            "get_skill",
            "get_skill_artifacts",
            "get_trial_report",
        }

    def test_call_tool_roundtrip_via_server(self, index):
        server = build_server(index=index)
        result = asyncio.run(server.call_tool("search_skills", {"query": "doc-skill"}))
        # MCPServer 返回 (content, structured) 或 content 列表；取序列化文本断言
        text = json.dumps(
            result[1] if isinstance(result, tuple) else str(result),
            ensure_ascii=False,
            default=str,
        )
        assert "doc-skill" in text

    def test_unknown_skill_structured_error_via_server(self, index):
        server = build_server(index=index)
        result = asyncio.run(server.call_tool("get_skill", {"skill_id": "nope"}))
        text = json.dumps(
            result[1] if isinstance(result, tuple) else str(result),
            ensure_ascii=False,
            default=str,
        )
        assert "skill_not_found" in text


class TestSearch:
    def test_match_by_name(self, index):
        out = search_skills(index, "doc-skill")
        assert out["count"] >= 1
        assert any(r["canonical_name"] == "doc-skill" for r in out["results"])

    def test_empty_query_lists_all(self, index):
        out = search_skills(index, "")
        assert out["count"] == len(index) == 5

    def test_no_match(self, index):
        assert search_skills(index, "zzz-not-exist")["count"] == 0

    def test_evidence_grade_only_d_or_u(self, index):
        for r in search_skills(index, "")["results"]:
            assert r["evidence_grade"] in ("D", "U")


class TestGetSkill:
    def test_detail_has_no_content_fields(self, index):
        skill_id = search_skills(index, "doc-skill")["results"][0]["skill_id"]
        detail = get_skill(index, skill_id)
        text = json.dumps(detail)
        for forbidden in ("script_text", "skill_md_body", "source_code", "api_key"):
            assert forbidden not in text
        assert detail["summary"]["origin_url"].startswith("https://")

    def test_unknown_id_structured_error(self, index):
        with pytest.raises(McpToolError) as exc_info:
            get_skill(index, "nope")
        payload = exc_info.value.to_payload()
        assert payload["error"]["code"] == "skill_not_found"


class TestArtifacts:
    def test_refs_only_no_content(self, index):
        skill_id = search_skills(index, "doc-skill")["results"][0]["skill_id"]
        out = get_skill_artifacts(index, skill_id)
        assert out["artifacts"], "expected at least one artifact ref"
        for a in out["artifacts"]:
            assert set(a) == {"bucket", "key", "sha256", "size_bytes", "summary"}
            assert a["sha256"] == "0" * 64  # 占位哈希：内容从未被获取
            assert a["size_bytes"] == 0

    def test_unknown_id_error(self, index):
        with pytest.raises(McpToolError):
            get_skill_artifacts(index, "nope")


class TestTrialReport:
    def test_report_sanitized(self):
        if not _REPORT.exists():
            pytest.skip("trial report not generated")
        out = get_trial_report(_REPORT)
        assert out["sample_count"] == 5
        text = json.dumps(out, ensure_ascii=False)
        assert "fake1234fake5678" not in text   # S5 构造凭证不得出现
        assert "script_text" not in text
        for e in out["entries"]:
            assert e["evidence_grade_cap"] in ("D", "U")

    def test_missing_report_structured_error(self, tmp_path):
        with pytest.raises(McpToolError) as exc_info:
            get_trial_report(tmp_path / "absent.json")
        assert exc_info.value.code == "report_not_found"


class TestD005NoLeak:
    def test_whole_surface_never_contains_manifest_text(self, index):
        # 全表面扫描：搜索+全部详情+全部制品引用序列化后不含 S5 假凭证字面量
        surface: list = [search_skills(index, "")]
        for r in search_skills(index, "")["results"]:
            surface.append(get_skill(index, r["skill_id"]))
            surface.append(get_skill_artifacts(index, r["skill_id"]))
        text = json.dumps(surface, ensure_ascii=False)
        assert "fake1234fake5678" not in text
        assert "-----BEGIN" not in text
