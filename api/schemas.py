"""Pydantic schemas for API responses, aligned with mcp_server/models.py TypedDict."""

from typing import Any
from pydantic import BaseModel, Field


class SkillSummaryOut(BaseModel):
    """搜索结果条目：最小元数据。"""
    skill_id: str
    canonical_name: str
    entity_type: str
    status: str
    source_kind: str
    origin_url: str
    description: str | None
    evidence_grade: str


class SkillDetailOut(BaseModel):
    """单 Skill 详情：摘要 + 声明面元数据（无正文）。"""
    summary: SkillSummaryOut
    author: str | None
    license_spdx: str | None
    declared_permissions: list[str]
    category_tags: list[str]
    is_alive: bool
    static_summary: dict[str, int] | None
    admission_reasons: list[str]
    warnings: list[str]
    json_ld: dict[str, Any] | None = Field(None, description="JSON-LD structured card")


class ArtifactRefOut(BaseModel):
    """制品引用：只有指针与摘要，绝无内容（D-005）。"""
    bucket: str
    key: str
    sha256: str
    size_bytes: int
    summary: str | None


class TrialReportOut(BaseModel):
    """Phase 0 试评报告的脱敏投影。"""
    trial_id: str
    generated_at: str
    sample_count: int
    all_matched_expectation: bool
    compliance: dict[str, Any]
    entries: list[dict[str, Any]]


class ErrorOut(BaseModel):
    """标准错误响应。"""
    error: str
    message: str
