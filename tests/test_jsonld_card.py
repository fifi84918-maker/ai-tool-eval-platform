"""新增 JSON-LD 结构化输出验证，确保不泄露敏感信息。"""

import json
from mcp_server.models import SkillDetail, SkillSummary
from mcp_server.jsonld import to_json_ld


class TestJsonLdCard:
    def test_skill_json_ld_sanitized(self):
        summary = SkillSummary(
            skill_id="test-skill-1",
            canonical_name="test-skill",
            entity_type="skill",
            status="NEUTRAL_TESTED",
            source_kind="github",
            origin_url="https://github.com/test/test",
            description="A test skill",
            evidence_grade="D",
        )
        detail = SkillDetail(
            summary=summary,
            author="author",
            license_spdx="MIT",
            declared_permissions=("file_read",),
            category_tags=(),
            is_alive=True,
            static_summary=None,
            admission_reasons=("reason one", "reason two"),
            warnings=("warning one",),
        )
        json_ld = to_json_ld(detail)
        assert json_ld["@context"] == "https://schema.org"
        assert json_ld["@type"] == "SoftwareApplication"
        assert "api_key" not in json.dumps(json_ld)
        assert "script_text" not in json.dumps(json_ld)
        assert "-----BEGIN" not in json.dumps(json_ld)

    def test_d5_json_ld_no_key_leak(self):
        summary = SkillSummary(
            skill_id="test-skill-2",
            canonical_name="test-skill-2",
            entity_type="skill",
            status="NEUTRAL_TESTED",
            source_kind="github",
            origin_url="https://github.com/test/test2",
            description="Another test skill",
            evidence_grade="U",
        )
        detail = SkillDetail(
            summary=summary,
            author="author",
            license_spdx=None,
            declared_permissions=("file_read",),
            category_tags=(),
            is_alive=True,
            static_summary=None,
            admission_reasons=("reason one",),
            warnings=("warning two",),
        )
        json_ld = to_json_ld(detail)
        assert "api_key" not in json.dumps(json_ld)
        assert "sk-" not in json.dumps(json_ld)
