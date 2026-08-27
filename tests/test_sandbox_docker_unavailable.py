"""DockerSandboxRunner 在 docker CLI 缺失/坏路径时抛 SandboxInfraUnavailable。"""

import pytest

from sandbox.dsl import StepKind, TaskPlan, TaskStep
from sandbox.errors import SandboxInfraUnavailable, SandboxSecurityBlock
from sandbox.runner import DockerSandboxRunner

_PLAN = TaskPlan(
    plan_id="d-1",
    steps=(TaskStep(name="x", kind=StepKind.RUN, argv=("true",)),),
)


class TestDockerUnavailable:
    def test_missing_cli_raises(self, monkeypatch):
        monkeypatch.setattr("sandbox.runner.shutil.which", lambda _: None)
        runner = DockerSandboxRunner()
        with pytest.raises(SandboxInfraUnavailable):
            runner.preflight()
        with pytest.raises(SandboxInfraUnavailable):
            runner.run(_PLAN)

    def test_broken_cli_path_raises(self):
        runner = DockerSandboxRunner(
            docker_path="Z:\\definitely\\missing\\docker.exe"
        )
        with pytest.raises(SandboxInfraUnavailable):
            runner.preflight()

    def test_build_args_works_without_docker(self):
        # 参数构造是纯函数路径，不需要 docker 存在
        args = DockerSandboxRunner().build_run_args(_PLAN)
        assert "--network" in args and "none" in args

    def test_network_without_allowlist_blocked(self):
        plan = TaskPlan(plan_id="d-2", steps=_PLAN.steps, network="allowlist")
        with pytest.raises(SandboxSecurityBlock):
            DockerSandboxRunner().build_run_args(plan)
