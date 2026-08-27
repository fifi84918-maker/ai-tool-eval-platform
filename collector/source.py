"""SourceAdapter 抽象与注入式客户端协议。

适配器不自己发网络请求：所有远端读取经由注入的 IndexClient 完成。
Phase 0 不提供任何真实 HTTP 实现，测试注入 stub。
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol

from core.enums import SourceKind
from core.schema.artifact import ArtifactRef
from core.schema.skill import SourceRecord

from collector.errors import UnsupportedSource

RawItem = Mapping[str, Any]
"""来源 API 返回的单条原始元数据（未归一化）。"""


class IndexClient(Protocol):
    """最小客户端协议：按路径+参数取 JSON。真实实现（含限流/重试）留待后续；
    实现方遇到限流应抛 RateLimitSignal，不得绕过。"""

    def get_json(self, path: str, params: Mapping[str, str] | None = None) -> Any: ...


@dataclass(frozen=True)
class IndexPage:
    """一页发现结果：原始条目 + 翻页游标（None = 无更多）。"""

    items: tuple[RawItem, ...]
    next_cursor: str | None = None
    etag: str | None = None
    raw_meta: Mapping[str, Any] = field(default_factory=dict)


class SourceAdapter(ABC):
    """来源适配器：发现（fetch_index）→ 归一（fetch_metadata）→
    制品引用（fetch_artifact_refs，仅引用，不拉内容）。"""

    kind: ClassVar[SourceKind]

    def __init__(self, client: IndexClient) -> None:
        self._client = client

    @abstractmethod
    def fetch_index(self, cursor: str | None = None) -> IndexPage:
        """返回一页候选条目；分页/增量语义由各来源自行定义。"""

    @abstractmethod
    def fetch_metadata(self, item: RawItem) -> SourceRecord:
        """把一条原始条目归一为 SourceRecord（core 契约）。
        三个许可判断位一律置 None：许可判定属分析层，不在采集层做。"""

    @abstractmethod
    def fetch_artifact_refs(self, item: RawItem) -> Sequence[ArtifactRef]:
        """返回制品引用列表。只构造指针（URL/key/占位哈希），绝不下载内容。"""


def adapter_for(kind: SourceKind, client: IndexClient) -> SourceAdapter:
    """按来源类型取适配器；无适配器的类型抛 UnsupportedSource。

    Phase 0 PoC 仅支持 GITHUB / HUGGING_FACE；三家平台市场与创作者提交
    走各自后续任务，不在此注册。
    """
    # 延迟导入避免环路
    from collector.github_adapter import GitHubPoCAdapter
    from collector.hf_adapter import HFPoCAdapter

    registry: dict[SourceKind, type[SourceAdapter]] = {
        SourceKind.GITHUB: GitHubPoCAdapter,
        SourceKind.HUGGING_FACE: HFPoCAdapter,
    }
    adapter_cls = registry.get(kind)
    if adapter_cls is None:
        raise UnsupportedSource(kind.value)
    return adapter_cls(client)
