"""对外 DTO：序列化友好的 dataclass（asdict 即 JSON-able）。

字段白名单原则：这里没有的字段就不会出去（policy.py 再做兜底过滤）。
"""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SkillSummary:
    """搜索结果条目：最小元数据。"""

    skill_id: str
    canonical_name: str
    entity_type: str
    status: str
    source_kind: str
    origin_url: str            # 安装/查看一律跳原始来源（D-005）
    description: str | None
    evidence_grade: str        # 本期数据源恒为 "D" 或 "U"


@dataclass(frozen=True)
class SkillDetail:
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
    bundle_hint: None = None                   # D-010 预留；Phase 1 聚合


@dataclass(frozen=True)
class ArtifactRefDTO:
    """制品引用：只有指针与摘要，绝无内容（D-005）。"""

    bucket: str
    key: str
    sha256: str
    size_bytes: int
    summary: str | None


@dataclass(frozen=True)
class TrialReportSummary:
    """Phase 0 试评报告的脱敏投影。"""

    trial_id: str
    generated_at: str
    sample_count: int
    all_matched_expectation: bool
    compliance: dict[str, Any]
    entries: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def to_json_dict(dto: Any) -> dict:
    """dataclass → JSON-able dict。"""
    return asdict(dto)
