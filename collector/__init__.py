"""collector：采集层 PoC。

只做来源发现与元数据归一（SourceRecord / ArtifactRef 构造）、去重键生成、
增量调度占位。不落库、不下载制品正文、不发真实网络请求（HTTP 客户端以
Protocol 注入，Phase 0 由测试 stub 提供）。
"""

from collector.errors import CollectorError, RateLimitSignal, UnsupportedSource
from collector.source import IndexClient, IndexPage, SourceAdapter, adapter_for

__all__ = [
    "CollectorError",
    "IndexClient",
    "IndexPage",
    "RateLimitSignal",
    "SourceAdapter",
    "UnsupportedSource",
    "adapter_for",
]
