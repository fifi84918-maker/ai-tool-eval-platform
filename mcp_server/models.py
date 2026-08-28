"""模型数据输出：序列化友好的 Skill JSON-LD 调用必须的返回结构。"""

from typing import Any, TypedDict


class SkillSummary(TypedDict):
    """搜索结果条目：最小元数据。"""
    skill_id: str
    canonical_name: str
    entity_type: str
    status: str
    source_kind: str
    origin_url: str            # 安装/查看一律跳原始来源（D-005）
    description: str | None
    evidence_grade: str        # 本期数据源恒为 "D" 或 "U"


class SkillDetail(TypedDict):
    """单 Skill 详情：摘要 + 声明面元数据（无正文）。"""
    summary: SkillSummary
    author: str | None
    license_spdx: str | None
    declared_permissions: tuple[str, ...]
    category_tags: tuple[str, ...]
    is_alive: bool
    static_summary: dict[str, int] | None      # 静态检测结论计数（无 finding 正文）
    admission_reasons: tuple[str, ...]
    warnings: tuple[str, ...]


class ArtifactRefDTO(TypedDict):
    """制品引用：只有指针与摘要，绝无内容（D-005）。"""
    bucket: str
    key: str
    sha256: str
    size_bytes: int
    summary: str | None


class BundleSummary(TypedDict):
    """Bundle 摘要：列表视图使用。"""
    bundle_id: str
    name: str
    description: str
    category: str


class Bundle(TypedDict):
    """Bundle 完整信息：一组相关 skills 的组合。"""
    bundle_id: str
    name: str
    description: str
    category: str
    skill_ids: tuple[str, ...]
    tags: tuple[str, ...]


class TrialReportSummary(TypedDict):
    """Phase 0 试评报告的脱敏投影。"""
    trial_id: str
    generated_at: str
    sample_count: int
    all_matched_expectation: bool
    compliance: dict[str, Any]
    entries: tuple[dict[str, Any], ...]


def to_json_dict(dto: Any) -> dict:
    """TypedDict/dict → JSON-able dict。TypedDict 本身就是 dict，直接返回。"""
    if isinstance(dto, dict):
        return dto
    # 如果是其他类型（如 dataclass），需要其他处理
    raise TypeError(f"Unsupported type for to_json_dict: {type(dto)}")
