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
    score_total: float | None = None
    grade: str | None = None


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
    
    # V1A Task 29.4.3: PRD 19.3 extended fields
    evidence_grade_detail: str | None = Field(None, description="Evidence grade with detail (C/D/U)")
    applicable_scenarios: list[str] = Field(default_factory=list, description="Applicable use cases")
    not_applicable_scenarios: list[str] = Field(default_factory=list, description="Not applicable scenarios")
    compatibility_status: str | None = Field(None, description="Platform compatibility status")
    compatibility_notes: str | None = Field(None, description="Compatibility details")
    static_findings: list[dict[str, str]] = Field(default_factory=list, description="Static check findings")
    failure_cases: list[str] = Field(default_factory=list, description="Known failure cases")
    test_env: dict[str, str] | None = Field(None, description="Test environment info")
    source_platforms: list[str] = Field(default_factory=list, description="Source platforms")


class ArtifactRefOut(BaseModel):
    """制品引用：只有指针与摘要，绝无内容（D-005）。"""
    bucket: str
    key: str
    sha256: str
    size_bytes: int
    summary: str | None


class BundleSummaryOut(BaseModel):
    """Bundle 摘要：列表视图使用。"""
    bundle_id: str
    name: str
    description: str
    category: str
    tier: str | None = None  # V1A 29.4.5: starter/standard/enterprise


class BundleOut(BaseModel):
    """Bundle 完整信息：一组相关 skills 的组合。"""
    bundle_id: str
    name: str
    description: str
    category: str
    skill_ids: list[str]
    tags: list[str]
    # V1A 29.4.5: Tiered bundle fields
    tier: str | None = None                    # starter/standard/enterprise
    target_domains: list[str] = []             # 适用领域
    required_languages: list[str] = []         # 建议语言栈
    security_level: str = "standard"           # lax/standard/strict
    highlights: list[str] = []                 # 卖点/亮点
    skill_count: int | None = None             # len(skill_ids)


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


# V1A Task 29.4.4: Project Profile Models
class ProjectProfileBase(BaseModel):
    """项目画像基础模型。"""
    name: str                    # 项目名称
    languages: list[str] = []    # 语言栈 ["python","typescript","go"]
    frameworks: list[str] = []   # 框架 ["fastapi","react","django"]
    domains: list[str] = []      # 领域 ["web","cli","data","ml","devops"]
    team_size: int | None = None # 团队规模
    security_requirement: str = "standard"  # lax / standard / strict
    description: str = ""        # 项目描述


class ProjectProfileCreate(ProjectProfileBase):
    """创建项目画像请求。"""
    pass


class ProjectProfileOut(ProjectProfileBase):
    """项目画像响应。"""
    id: str                      # UUID hex
    created_at: str

    model_config = {"from_attributes": True}


# V1A Task 29.4.5: Bundle recommendation input
class BundleRecommendRequest(BaseModel):
    """Bundle 推荐请求（使用项目画像）。"""
    name: str                    # 项目名称
    languages: list[str] = []    # 语言栈
    frameworks: list[str] = []   # 框架
    domains: list[str] = []      # 领域
    team_size: int | None = None
    security_requirement: str = "standard"
    description: str = ""


# V1A Task 29.4.6: Recommendation generation schemas
class RecommendedSkillOut(BaseModel):
    """推荐结果中的 Skill 详情。"""
    skill_id: str
    name: str
    grade: str | None = None
    score_total: float | None = None
    metrics: dict[str, float] = {}   # accuracy/reliability/security/performance


class BundleRecommendationOut(BaseModel):
    """推荐结果中的 Bundle（含展开的 skills）。"""
    bundle_id: str
    name: str
    tier: str
    description: str = ""
    security_level: str = "standard"
    highlights: list[str] = []
    score: float = 0.0          # 匹配得分
    match_reasons: list[str] = []  # 可读的匹配理由
    skills: list[RecommendedSkillOut] = []  # 展开详情


class RecommendationResponse(BaseModel):
    """推荐响应。"""
    profile_id: str | None = None
    profile_name: str | None = None
    total: int
    items: list[BundleRecommendationOut]
