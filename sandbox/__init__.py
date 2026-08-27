"""sandbox：中立沙箱层原型（Phase 0）。

定义运行器协议、最小任务步骤 DSL、策略与报告形状、测试员 Agent 协议。
本机当前无 WSL2/Docker：DockerSandboxRunner 只构造命令并在执行前探测
CLI（缺失抛 SandboxInfraUnavailable）；LocalSimRunner 用 subprocess 做
形状验证，明确不提供安全隔离。不接真实 LLM、不评分、不驱动状态机。
"""

from sandbox.agent_protocol import StubTesterAgent, TesterAgent
from sandbox.dsl import StepKind, TaskPlan, TaskStep
from sandbox.errors import (
    SandboxError,
    SandboxInfraUnavailable,
    SandboxSecurityBlock,
    SandboxTimeout,
)
from sandbox.policy import SandboxPolicy, default_sandbox_policy
from sandbox.report import AgentJudgement, SandboxRunReport, StepOutcome, Verdict
from sandbox.runner import DockerSandboxRunner, LocalSimRunner, SandboxRunner

__all__ = [
    "AgentJudgement",
    "DockerSandboxRunner",
    "LocalSimRunner",
    "SandboxError",
    "SandboxInfraUnavailable",
    "SandboxPolicy",
    "SandboxRunner",
    "SandboxRunReport",
    "SandboxSecurityBlock",
    "SandboxTimeout",
    "StepKind",
    "StepOutcome",
    "StubTesterAgent",
    "TaskPlan",
    "TaskStep",
    "TesterAgent",
    "Verdict",
    "default_sandbox_policy",
]
