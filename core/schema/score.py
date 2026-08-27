"""评分记录与 Bundle 推荐单元形状（PRD 15 / 18）。"""

from dataclasses import dataclass, field
from datetime import datetime

from core.enums import BundleTier, EvidenceGrade, PermScope, ScoreDimension


@dataclass(frozen=True)
class DimensionScore:
    """单一维度分值。权重仅默认场景适用，推荐时按项目目标动态调权。"""

    dimension: ScoreDimension
    score: float
    weight: float


@dataclass(frozen=True)
class ScoreRecord:
    """评分快照：绑定 Artifact 版本、评分规则版本与证据等级（PRD 15.1/22.2）。

    没有动态测试不得给出动态能力分；D/U 级不得展示动态效果结论。
    """

    score_id: str
    artifact_id: str
    scoring_rule_version: str
    dimensions: tuple[DimensionScore, ...]
    composite: float | None          # 默认权重综合分；无动态测试时为 None
    uplift: float | None             # 相对无 Skill 基线的增益；无基线为 None
    evidence_grade: EvidenceGrade    # 必填（PRD 15.1 第 8 条：公开分数必须带等级）
    sample_size: int                 # 任务数 × 重复次数；必填
    env_snapshot_id: str
    evaluated_at: datetime
    valid_until: datetime | None     # 过期置 STALE 并触发回归


@dataclass(frozen=True)
class BundleItem:
    """Bundle 内单个 Skill 条目（PRD 18.4）。安装一律跳转原始来源。"""

    skill_id: str
    artifact_id: str
    role_in_project: str                       # 该 Skill 承担的任务
    required_permissions: frozenset[PermScope]
    install_origin_url: str                    # 原始来源链接；平台不提供下载
    known_limitations: tuple[str, ...] = field(default_factory=tuple)
    alternative_skill_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BundleRecommendation:
    """面向某项目画像的一档推荐方案（轻量/平衡/增强，PRD 18.5）。"""

    bundle_id: str
    project_profile_id: str
    tier: BundleTier
    items: tuple[BundleItem, ...]
    excluded_skill_ids: tuple[str, ...]        # 不推荐/排除项（含原因由展示层关联）
    acceptance_test_case_ids: tuple[str, ...]  # 验收测试
    estimated_cost_cny: float | None
    created_at: datetime | None = None
