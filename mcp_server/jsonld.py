"""JSON-LD 结构化输出：对 Skill 详情序列化为标准格式。借助现有元数据使其可被 LLM/搜索工具解析。"""

import json

from mcp_server.models import SkillDetail
from mcp_server.errors import McpToolError
from mcp_server.policy import scrub, clamp_evidence_grade


def to_json_ld(detail: SkillDetail) -> dict:
    # 使用 policy.scrub() 进行脱敏，TypedDict 本身就是 dict
    scrubbed_detail = scrub(detail)
    
    # 安全处理 static_summary（可能为 None）
    static_summary = scrubbed_detail.get("static_summary") or {}
    static_issues_count = len(static_summary.get("issues", []))
    
    # 输出结构
    json_ld = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": scrubbed_detail["summary"]["canonical_name"],
        "description": scrubbed_detail["summary"]["description"],
        "applicationCategory": "AI Skill / Agent Tool",
        "operatingSystem": "Platform-independent",
        "license": scrubbed_detail["license_spdx"] or "Unknown",
        "author": {"@type": "Organization", "name": scrubbed_detail["author"] or "Unknown"},
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "skill_id", "value": scrubbed_detail["summary"]["skill_id"]},
            {"@type": "PropertyValue", "name": "status", "value": scrubbed_detail["summary"]["status"]},
            {"@type": "PropertyValue", "name": "source_kind", "value": scrubbed_detail["summary"]["source_kind"]},
            {"@type": "PropertyValue", "name": "evidence_grade", "value": clamp_evidence_grade(scrubbed_detail["summary"]["evidence_grade"])} ,
            {"@type": "PropertyValue", "name": "static_issues_count", "value": static_issues_count},
            {"@type": "PropertyValue", "name": "admission_reasons", "value": ", ".join(scrubbed_detail["admission_reasons"])},
            {"@type": "PropertyValue", "name": "warnings_count", "value": len(scrubbed_detail["warnings"])}
        ]
    }
    # 序列化后担保不泄露敏感信息
    json_ld_str = json.dumps(json_ld, ensure_ascii=False)
    if any(key in json_ld_str for key in ("api_key", "sk-", "-----BEGIN", "ghp_")):
        raise McpToolError("jsonld_leak_detected", "sensitive data detected in JSON-LD output")
    return json_ld
