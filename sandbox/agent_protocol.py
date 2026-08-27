"""测试员 Agent 协议：编排/重试/判定的接口骨架。Phase 0 不接 LLM。"""

from typing import Protocol

from sandbox.dsl import TaskPlan
from sandbox.report import AgentJudgement, SandboxRunReport, Verdict


class TesterAgent(Protocol):
    """测试员 Agent：把任务意图变成计划（prepare_plan），并对运行报告
    给出判定（judge_run）。真实实现（DSL 编译 + LLM 辅助）留待后续任务。"""

    def prepare_plan(self, task_intent: str, plan_id: str) -> TaskPlan: ...

    def judge_run(self, report: SandboxRunReport) -> AgentJudgement: ...


class StubTesterAgent:
    """确定性 stub：不调用任何模型。

    prepare_plan 返回空步骤计划（形状占位）；judge_run 只读断言汇总：
    全过 → PASS，有失败 → FAIL，无断言 → INCONCLUSIVE。
    """

    def prepare_plan(self, task_intent: str, plan_id: str) -> TaskPlan:
        return TaskPlan(plan_id=plan_id, steps=(), labels=("stub", task_intent[:40]))

    def judge_run(self, report: SandboxRunReport) -> AgentJudgement:
        if report.all_assertions_passed is None:
            return AgentJudgement(
                plan_id=report.plan_id,
                verdict=Verdict.INCONCLUSIVE,
                reasons=("no assertion steps in plan",),
            )
        if report.all_assertions_passed:
            return AgentJudgement(
                plan_id=report.plan_id,
                verdict=Verdict.PASS,
                reasons=("all assertions passed",),
            )
        failed = tuple(
            s.step_name for s in report.steps if s.passed is False
        )
        return AgentJudgement(
            plan_id=report.plan_id,
            verdict=Verdict.FAIL,
            reasons=tuple(f"assertion failed: {name}" for name in failed),
        )
