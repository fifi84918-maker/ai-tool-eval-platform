"""沙箱运行报告与测试员 Agent 判定形状。"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    NEED_INFO = "need_info"


@dataclass(frozen=True)
class StepOutcome:
    """单步执行结果。stdout/stderr 只保留截断摘要，全文留给证据存储环节。"""

    step_name: str
    kind: str
    passed: bool | None            # 断言步为 True/False；执行步 None=无断言语义
    exit_code: int | None
    stdout_snippet: str | None
    stderr_snippet: str | None
    duration_seconds: float | None


@dataclass(frozen=True)
class SandboxRunReport:
    """一次沙箱运行的完整报告；后续由编排层转为 core.TestRun + EvidenceRef。"""

    plan_id: str
    runner_name: str               # "local-sim" | "docker" …
    isolated: bool                 # LocalSimRunner 必须为 False
    started_at_iso: str
    finished_at_iso: str | None
    steps: tuple[StepOutcome, ...]
    all_assertions_passed: bool | None   # 无断言步时为 None
    infra_meta: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentJudgement:
    """测试员 Agent 对一次运行的判定（Phase 0 为 stub 产出，不接 LLM）。"""

    plan_id: str
    verdict: Verdict
    reasons: tuple[str, ...] = field(default_factory=tuple)
