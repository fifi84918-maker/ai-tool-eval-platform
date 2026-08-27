"""测试运行记录形状。证据只存指针/摘要（EvidenceRef），不存证据体。"""

from dataclasses import dataclass, field
from datetime import datetime

from core.schema.artifact import ArtifactRef


@dataclass(frozen=True)
class EvidenceRef:
    """一条证据的引用：日志/产物/Diff/截图/校验结果等，存于对象存储。"""

    kind: str                # log / output_file / diff / screenshot / check_result …
    ref: ArtifactRef         # 指针 + sha256 + 摘要；不内嵌内容
    is_public: bool | None   # 是否可公开（None = 未裁定）


@dataclass(frozen=True)
class StepResult:
    """一次运行中的单个步骤结果。"""

    step_index: int
    name: str
    passed: bool | None      # None = 该步不产生通过/失败结论
    detail_summary: str | None
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TestRun:
    """固定环境中一次可追溯的测试执行（PRD 22.1）。

    结果必须绑定 ArtifactVersion 与测试环境快照；含无 Skill 基线运行
    （artifact_id 为 None 表示基线）。
    """

    run_id: str
    artifact_id: str | None          # None = 无 Skill 基线运行
    test_case_id: str
    test_case_version: str
    env_snapshot_id: str             # 宿主/模型/系统/工具环境快照标识
    started_at: datetime
    finished_at: datetime | None
    passed: bool | None              # None = 未完成或不可判定
    cost_tokens: int | None
    cost_external_cny: float | None  # 外部 API 费用（受成本上限约束，PRD 13.1）
    duration_seconds: float | None
    steps: tuple[StepResult, ...] = field(default_factory=tuple)
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)
