"""沙箱策略：默认值 + docker run 参数渲染（渲染不等于执行）。

TODO(未决)：镜像来源/tag 固定策略、网络白名单域名列表的传入方、
CPU/内存配额的项目级覆盖 —— 均待测试环境镜像任务定夺，当前为保守默认。
"""

from dataclasses import dataclass, field

from sandbox.dsl import TaskPlan


@dataclass(frozen=True)
class SandboxPolicy:
    network: str = "off"                # "off" | "allowlist"
    allowlist_domains: tuple[str, ...] = field(default_factory=tuple)
    privileged: bool = False
    read_only_rootfs: bool = True
    forbid_sensitive_mounts: bool = True   # 禁止挂载 $HOME/凭证/docker.sock 等
    cpu_limit: str = "1.0"
    memory_limit: str = "1g"
    default_timeout_sec: float = 120.0
    default_workdir: str = "/work"
    image: str = "python:3.12-slim"     # TODO：镜像版本固化策略待定


def default_sandbox_policy() -> SandboxPolicy:
    """PRD 23.2 语义的保守默认：断网、非特权、只读根、无敏感挂载。"""
    return SandboxPolicy()


def render_docker_run_args(policy: SandboxPolicy, plan: TaskPlan) -> tuple[str, ...]:
    """把策略+计划渲染为 docker run 参数序列（不含步骤命令本身，不执行）。"""
    args: list[str] = ["run", "--rm"]
    network = plan.network or policy.network
    if network == "off":
        args += ["--network", "none"]
    # allowlist 模式的实际出口控制需 sidecar/代理，Phase 0 只保留标记
    if not policy.privileged:
        args += ["--security-opt", "no-new-privileges"]
    if policy.read_only_rootfs:
        args += ["--read-only"]
    args += [
        "--cpus", policy.cpu_limit,
        "--memory", policy.memory_limit,
        "--workdir", plan.workdir or policy.default_workdir,
    ]
    for key, value in sorted((plan.env or {}).items()):
        args += ["--env", f"{key}={value}"]
    args.append(policy.image)
    return tuple(args)
