"""流水线报告形状。纯数据，不持久化（落盘位置属后续任务）。"""

from dataclasses import dataclass, field

from analyzer.pipeline import StaticReviewReport
from core.state import SkillStatus
from orchestrator.admission import AdmissionDecision
from sandbox.report import SandboxRunReport


@dataclass(frozen=True)
class StageResult:
    """单阶段结果。skipped=True 时 ok 表示"跳过是预期的"。"""

    name: str
    ok: bool
    skipped: bool = False
    detail: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class PipelineReport:
    pipeline_id: str
    skill_id: str | None                 # collect 阶段失败时为 None
    canonical_name: str | None
    status_before: SkillStatus
    status_after: SkillStatus
    per_stage: tuple[StageResult, ...]   # 保序；dict 语义用 stage(name) 取
    admission: AdmissionDecision | None = None
    static_report: StaticReviewReport | None = None
    sandbox_report: SandboxRunReport | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def stage(self, name: str) -> StageResult | None:
        for result in self.per_stage:
            if result.name == name:
                return result
        return None
