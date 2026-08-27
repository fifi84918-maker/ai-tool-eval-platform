"""LocalSimRunner 端到端形状验证（本机 subprocess，非隔离，仅开发用）。

计划只含我方编写的确定性 Python 步骤（python -c），不运行任何外部制品。
"""

import sys

from sandbox.dsl import StepKind, TaskPlan, TaskStep
from sandbox.report import SandboxRunReport
from sandbox.runner import LocalSimRunner

_PY = sys.executable


def _run_step(name: str, code: str) -> TaskStep:
    return TaskStep(name=name, kind=StepKind.RUN, argv=(_PY, "-c", code))


class TestLocalSim:
    def test_success_path_with_assertions(self):
        plan = TaskPlan(
            plan_id="sim-ok",
            steps=(
                _run_step("emit", "print('marker-42')"),
                TaskStep(
                    name="exit0", kind=StepKind.ASSERT_EXIT_CODE, expect_exit_code=0
                ),
                TaskStep(
                    name="has-marker",
                    kind=StepKind.ASSERT_OUTPUT_CONTAINS,
                    expect_substring="marker-42",
                ),
            ),
        )
        report = LocalSimRunner().run(plan)
        assert isinstance(report, SandboxRunReport)
        assert report.runner_name == "local-sim"
        assert report.isolated is False  # 关键标记：绝不声称隔离
        assert report.all_assertions_passed is True
        assert [s.step_name for s in report.steps] == ["emit", "exit0", "has-marker"]

    def test_failure_detected(self):
        plan = TaskPlan(
            plan_id="sim-fail",
            steps=(
                _run_step("boom", "import sys; sys.exit(3)"),
                TaskStep(
                    name="expect-zero",
                    kind=StepKind.ASSERT_EXIT_CODE,
                    expect_exit_code=0,
                ),
            ),
        )
        report = LocalSimRunner().run(plan)
        assert report.all_assertions_passed is False
        assert report.steps[0].exit_code == 3

    def test_no_assertions_is_none(self):
        report = LocalSimRunner().run(
            TaskPlan(plan_id="sim-none", steps=(_run_step("only", "print(1)"),))
        )
        assert report.all_assertions_passed is None

    def test_copy_steps_are_noop(self):
        report = LocalSimRunner().run(
            TaskPlan(
                plan_id="sim-copy",
                steps=(
                    TaskStep(
                        name="cin", kind=StepKind.COPY_IN, src="a.txt", dst="b.txt"
                    ),
                ),
            )
        )
        assert report.steps[0].passed is None
        assert "no-op" in (report.steps[0].stderr_snippet or "")

    def test_warning_present_in_meta(self):
        report = LocalSimRunner().run(TaskPlan(plan_id="sim-meta", steps=()))
        assert "NO isolation" in report.infra_meta.get("warning", "")
