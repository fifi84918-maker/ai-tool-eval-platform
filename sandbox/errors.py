"""沙箱层错误类型。"""


class SandboxError(Exception):
    """沙箱层错误基类。"""


class SandboxTimeout(SandboxError):
    """步骤或整体运行超时。"""

    def __init__(self, step_name: str, timeout_sec: float) -> None:
        super().__init__(f"step '{step_name}' timed out after {timeout_sec}s")
        self.step_name = step_name
        self.timeout_sec = timeout_sec


class SandboxSecurityBlock(SandboxError):
    """计划或步骤违反沙箱策略（如要求联网/特权），拒绝执行。"""

    def __init__(self, reason: str) -> None:
        super().__init__(f"blocked by sandbox policy: {reason}")
        self.reason = reason


class SandboxInfraUnavailable(SandboxError):
    """执行基础设施不可用（如本机无 docker CLI）。"""

    def __init__(self, detail: str) -> None:
        super().__init__(f"sandbox infrastructure unavailable: {detail}")
        self.detail = detail
