"""采集层错误类型。"""


class CollectorError(Exception):
    """采集层错误基类。"""


class RateLimitSignal(CollectorError):
    """来源限流信号：调用方应按 retry_after_seconds 退避，不得绕过限流。"""

    def __init__(self, source: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(f"rate limited by {source}")
        self.source = source
        self.retry_after_seconds = retry_after_seconds


class UnsupportedSource(CollectorError):
    """请求了当前没有适配器的来源类型。"""

    def __init__(self, kind: str) -> None:
        super().__init__(f"no adapter for source kind: {kind}")
        self.kind = kind
