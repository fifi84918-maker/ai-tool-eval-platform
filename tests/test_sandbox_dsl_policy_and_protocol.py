"""DSL / policy / 协议形状测试。无 subprocess、无 docker。"""

from sandbox.agent_protocol import StubTesterAgent
from sandbox.dsl import StepKind, TaskPlan, TaskStep
from sandbox.policy import default_sandbox_policy, render_docker_run_args
from sandbox.report import (
    AgentJudgement,
    SandboxRunReport,
    StepOutcome,
    Verdict,
)


def _plan(**overrides) -> TaskPlan:
    base = dict(
        plan_id="plan-1",
        steps=(
            TaskStep(name="hello", kind=StepKind.RUN, argv=("echo", "hi")),
            TaskStep(name="check", kind=StepKind.ASSERT_EXIT_CODE, expect_exit_code=0),
        ),
    )
    base.update(overrides)
    return TaskPlan(**base)


class TestPolicyDefaults:
    def test_conservative_defaults(self):
        p = default_sandbox_policy()
        assert p.network == "off"
        assert p.privileged is False
        assert p.read_only_rootfs is True
        assert p.forbid_sensitive_mounts is True

    def test_render_docker_args_offline_readonly(self):
        args = render_docker_run_args(default_sandbox_policy(), _plan())
        joined = " ".join(args)
        assert "--network none" in joined
        assert "--read-only" in joined
        assert "--security-opt no-new-privileges" in joined
        assert args[0] == "run" and "--rm" in args

    def test_plan_env_rendered_sorted(self):
        args = render_docker_run_args(
            default_sandbox_policy(), _plan(env={"B": "2", "A": "1"})
        )
        joined = " ".join(args)
        assert joined.index("A=1") < joined.index("B=2")


class TestStubAgent:
    def _report(self, all_passed) -> SandboxRunReport:
        return SandboxRunReport(
            plan_id="plan-1",
            runner_name="local-sim",
            isolated=False,
            started_at_iso="2026-01-01T00:00:00+00:00",
            finished_at_iso=None,
            steps=(
                StepOutcome(
                    step_name="check",
                    kind="assert_exit_code",
                    passed=all_passed if all_passed is not None else None,
                    exit_code=0,
                    stdout_snippet=None,
                    stderr_snippet=None,
                    duration_seconds=None,
                ),
            ),
            all_assertions_passed=all_passed,
        )

    def test_prepare_plan_shape(self):
        plan = StubTesterAgent().prepare_plan("do a research task", "p-9")
        assert isinstance(plan, TaskPlan) and plan.plan_id == "p-9"

    def test_judgement_mapping(self):
        agent = StubTesterAgent()
        assert agent.judge_run(self._report(True)).verdict is Verdict.PASS
        assert agent.judge_run(self._report(False)).verdict is Verdict.FAIL
        j = agent.judge_run(self._report(None))
        assert j.verdict is Verdict.INCONCLUSIVE
        assert isinstance(j, AgentJudgement)
