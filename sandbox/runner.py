"""沙箱运行器：Protocol + LocalSimRunner + DockerSandboxRunner。

LocalSimRunner —— 仅 Phase 0 开发/形状验证：
  用 subprocess 在本机直接跑 RUN/SCRIPT 步骤，**不提供任何安全隔离**
  （无容器、无断网、无文件系统保护）。报告中 isolated=False 恒真。
  只允许跑我方自己编写的确定性测试计划，绝不能跑外部 Skill 制品。

DockerSandboxRunner —— 完整构造 docker run 参数并探测 CLI：
  本机无 docker 时抛 SandboxInfraUnavailable。执行路径经 subprocess 调
  docker CLI（零新依赖；TODO：环境就绪后如需 docker-py 另行评审，
  pyproject.toml 暂不动）。
"""

import shutil
import subprocess
from datetime import datetime, timezone
from typing import Protocol

from sandbox.dsl import StepKind, TaskPlan, TaskStep
from sandbox.errors import SandboxInfraUnavailable, SandboxSecurityBlock, SandboxTimeout
from sandbox.policy import SandboxPolicy, default_sandbox_policy, render_docker_run_args
from sandbox.report import SandboxRunReport, StepOutcome

_SNIPPET_LIMIT = 2000


class SandboxRunner(Protocol):
    """运行器协议：执行 TaskPlan，产出 SandboxRunReport。"""

    def run(self, plan: TaskPlan) -> SandboxRunReport: ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snippet(text: str | None) -> str | None:
    if text is None:
        return None
    return text[:_SNIPPET_LIMIT]


class LocalSimRunner:
    """本机模拟运行器 —— 仅开发验证，非安全隔离（见模块 docstring）。"""

    name = "local-sim"

    def __init__(self, policy: SandboxPolicy | None = None) -> None:
        self._policy = policy or default_sandbox_policy()

    def run(self, plan: TaskPlan) -> SandboxRunReport:
        started = _now_iso()
        steps: list[StepOutcome] = []
        last_exit: int | None = None
        last_stdout: str = ""
        assertions: list[bool] = []

        for step in plan.steps:
            timeout = step.timeout_sec or self._policy.default_timeout_sec
            if step.kind in (StepKind.RUN, StepKind.SCRIPT):
                argv = (
                    list(step.argv)
                    if step.kind is StepKind.RUN
                    else ["pwsh", "-NoProfile", "-Command", step.script_text or ""]
                )
                try:
                    proc = subprocess.run(
                        argv,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=plan.workdir,  # None → 继承当前目录（模拟器语义）
                    )
                except subprocess.TimeoutExpired:
                    raise SandboxTimeout(step.name, timeout) from None
                last_exit, last_stdout = proc.returncode, proc.stdout or ""
                steps.append(
                    StepOutcome(
                        step_name=step.name,
                        kind=step.kind.value,
                        passed=None,
                        exit_code=proc.returncode,
                        stdout_snippet=_snippet(proc.stdout),
                        stderr_snippet=_snippet(proc.stderr),
                        duration_seconds=None,
                    )
                )
            elif step.kind is StepKind.ASSERT_EXIT_CODE:
                ok = last_exit == step.expect_exit_code
                assertions.append(ok)
                steps.append(
                    StepOutcome(
                        step_name=step.name,
                        kind=step.kind.value,
                        passed=ok,
                        exit_code=last_exit,
                        stdout_snippet=None,
                        stderr_snippet=None,
                        duration_seconds=None,
                    )
                )
            elif step.kind is StepKind.ASSERT_OUTPUT_CONTAINS:
                ok = (step.expect_substring or "") in last_stdout
                assertions.append(ok)
                steps.append(
                    StepOutcome(
                        step_name=step.name,
                        kind=step.kind.value,
                        passed=ok,
                        exit_code=last_exit,
                        stdout_snippet=_snippet(last_stdout),
                        stderr_snippet=None,
                        duration_seconds=None,
                    )
                )
            else:  # COPY_IN / COPY_OUT：模拟器不做文件搬运，记录为未执行断言
                steps.append(
                    StepOutcome(
                        step_name=step.name,
                        kind=step.kind.value,
                        passed=None,
                        exit_code=None,
                        stdout_snippet=None,
                        stderr_snippet="copy steps are no-op in local-sim",
                        duration_seconds=None,
                    )
                )

        return SandboxRunReport(
            plan_id=plan.plan_id,
            runner_name=self.name,
            isolated=False,
            started_at_iso=started,
            finished_at_iso=_now_iso(),
            steps=tuple(steps),
            all_assertions_passed=all(assertions) if assertions else None,
            infra_meta={"warning": "local-sim provides NO isolation; dev only"},
        )


class DockerSandboxRunner:
    """Docker 一次性容器运行器（PRD 23.2）。执行前探测 CLI。"""

    name = "docker"

    def __init__(
        self,
        policy: SandboxPolicy | None = None,
        docker_path: str | None = None,
    ) -> None:
        self._policy = policy or default_sandbox_policy()
        self._docker_path = docker_path  # None → shutil.which 探测

    def preflight(self) -> str:
        """探测 docker CLI；不可用抛 SandboxInfraUnavailable，可用返回路径。"""
        path = self._docker_path or shutil.which("docker")
        if path is None:
            raise SandboxInfraUnavailable("docker CLI not found on PATH")
        try:
            proc = subprocess.run(
                [path, "version", "--format", "{{.Client.Version}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxInfraUnavailable(f"docker CLI not runnable: {exc}") from None
        if proc.returncode != 0:
            raise SandboxInfraUnavailable(
                f"docker CLI returned {proc.returncode}: {_snippet(proc.stderr)}"
            )
        return path

    def build_run_args(self, plan: TaskPlan) -> tuple[str, ...]:
        """渲染 docker run 参数（纯函数封装，可测试；不执行）。"""
        if plan.network not in (None, "off") and not self._policy.allowlist_domains:
            raise SandboxSecurityBlock(
                "plan requests network but policy has no allowlist"
            )
        return render_docker_run_args(self._policy, plan)

    def run(self, plan: TaskPlan) -> SandboxRunReport:
        docker = self.preflight()  # 环境不可用在此抛出
        args = self.build_run_args(plan)
        # TODO(环境就绪后)：逐步执行 plan.steps —— copy_in 用 docker cp /
        # 卷挂载，RUN/SCRIPT 经 `docker run` 执行并回收退出码与输出，
        # 每步一次性容器、运行后清理（PRD 23.2）。当前环境无 docker，
        # 此路径在 preflight 即抛 SandboxInfraUnavailable，不会到达这里。
        raise SandboxInfraUnavailable(
            f"docker execution path not implemented in Phase 0 "
            f"(cli={docker}, args={' '.join(args[:6])}…)"
        )
