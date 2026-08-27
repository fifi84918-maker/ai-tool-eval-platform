"""4 个 MCP 工具的纯函数 handler：接收索引/数据，返回 JSON-able dict。

server.py 负责 MCP 协议壳；这里可直接单测。所有返回值过 policy.scrub。
"""

import json
from pathlib import Path
from typing import Any

from mcp_server.errors import McpToolError
from mcp_server.index import InMemorySkillIndex
from mcp_server.models import to_json_dict
from mcp_server.policy import clamp_evidence_grade, scrub


def search_skills(index: InMemorySkillIndex, query: str, limit: int = 10) -> dict:
    if not isinstance(query, str):
        raise McpToolError("invalid_argument", "query must be a string")
    limit = max(1, min(int(limit), 50))
    results = index.search(query, limit=limit)
    return scrub(
        {
            "query": query,
            "count": len(results),
            "results": [
                to_json_dict(s)
                for s in results
            ],
            "note": "install/inspect via origin_url only; no file downloads (D-005)",
        }
    )


def get_skill(index: InMemorySkillIndex, skill_id: str) -> dict:
    detail = index.get(skill_id)  # 由 index.get 获取所需的 SkillDetail.
    if detail is None:
        raise McpToolError("skill_not_found", f"unknown skill_id: {skill_id}")
    return scrub(to_json_dict(detail))


def get_skill_artifacts(index: InMemorySkillIndex, skill_id: str) -> dict:
    artifacts = index.get_artifacts(skill_id)
    if artifacts is None:
        raise McpToolError("skill_not_found", f"unknown skill_id: {skill_id}")
    return scrub({
        "skill_id": skill_id,
        "artifacts": [
            to_json_dict(a)
            for a in artifacts
        ],
        "note": "references only (bucket/key/sha256); content is never served",
    })


def get_trial_report(report_path: Path) -> dict:
    if not report_path.exists():
        raise McpToolError(
            "report_not_found",
            "phase0 trial report not generated yet; run scripts/run_phase0_trial.py",
        )
    try:
        raw: Any = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise McpToolError("report_unreadable", f"{type(exc).__name__}: {exc}") from None

    return scrub(
        {
            "trial_id": raw.get("trial_id"),
            "generated_at": raw.get("generated_at"),
            "sample_count": raw.get("sample_count"),
            "all_matched_expectation": raw.get("all_matched_expectation"),
            "compliance": raw.get("compliance", {}),
            "entries": [
                {
                    "sample_id": e.get("sample_id"),
                    "label": e.get("label"),
                    "skill_id": e.get("skill_id"),
                    "status_after": e.get("status_after"),
                    "matched_expectation": e.get("matched_expectation"),
                    "non_isolated": e.get("non_isolated"),
                    "evidence_grade_cap": clamp_evidence_grade(e.get("evidence_grade_cap")),
                }
                for e in raw.get("entries", [])
            ],
        }
    )
