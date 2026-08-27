"""编排层错误类型。

流水线 run() 本身不抛这些异常（每阶段兜底转入报告）；它们供严格模式
调用方与内部标注使用。
"""


class OrchestratorError(Exception):
    """编排层错误基类。"""


class AdmissionBlocked(OrchestratorError):
    """准入被阻断（secrets 阻断 / D-008 权利未确认）。"""

    def __init__(self, reason: str) -> None:
        super().__init__(f"admission blocked: {reason}")
        self.reason = reason


class PipelineStepFailed(OrchestratorError):
    """某个流水线阶段执行失败。"""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"pipeline stage '{stage}' failed: {detail}")
        self.stage = stage
        self.detail = detail
