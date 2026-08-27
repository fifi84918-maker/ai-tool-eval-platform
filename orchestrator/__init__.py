"""orchestrator：编排层（Phase 0）。

把 collector → analyzer → 准入判定 → sandbox 串成可重放的测评流水线，
状态推进消费 core.state.transition（事件驱动，非法转移记录不中断）。
不接真实网络/LLM/DB、不评分（Task 08）、不持久化。
只服务 NEUTRAL_TESTED 路径；NATIVE_TESTED/Phase 2 不在此处理。
"""

from orchestrator.admission import AdmissionDecision, apply_admission
from orchestrator.errors import (
    AdmissionBlocked,
    OrchestratorError,
    PipelineStepFailed,
)
from orchestrator.pipeline import SkillReviewPipeline, run
from orchestrator.report import PipelineReport, StageResult
from orchestrator.state_driver import DriveResult, drive_status

__all__ = [
    "AdmissionBlocked",
    "AdmissionDecision",
    "DriveResult",
    "OrchestratorError",
    "PipelineReport",
    "PipelineStepFailed",
    "SkillReviewPipeline",
    "StageResult",
    "apply_admission",
    "drive_status",
    "run",
]
