"""Docker 冒烟测试：默认 skip。

仅当环境变量 SANDBOX_LIVE=1 且本机有 docker CLI 时运行（当前开发机
无 WSL2/Docker，此文件在 CI/本地默认全部跳过）。
"""

import os
import shutil

import pytest

from sandbox.dsl import StepKind, TaskPlan, TaskStep
from sandbox.runner import DockerSandboxRunner

_LIVE = os.environ.get("SANDBOX_LIVE") == "1" and shutil.which("docker") is not None

pytestmark = pytest.mark.skipif(
    not _LIVE, reason="requires SANDBOX_LIVE=1 and docker CLI on PATH"
)


class TestDockerSmoke:
    def test_preflight_finds_cli(self):
        assert DockerSandboxRunner().preflight()

    def test_run_raises_not_implemented_phase0(self):
        # Phase 0 执行路径未实现：即使 docker 可用也应显式抛基础设施异常，
        # 防止误以为已具备真实隔离执行能力
        from sandbox.errors import SandboxInfraUnavailable

        plan = TaskPlan(
            plan_id="smoke-1",
            steps=(TaskStep(name="x", kind=StepKind.RUN, argv=("true",)),),
        )
        with pytest.raises(SandboxInfraUnavailable):
            DockerSandboxRunner().run(plan)
