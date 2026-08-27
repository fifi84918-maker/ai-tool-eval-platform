"""Hugging Face 来源 PoC 适配器：Hub repo/model 元数据 → SourceRecord + ArtifactRef。

只做 repo card / revision 级别引用，不下载权重、数据集或任何文件内容。
TODO(PoC 后)：Hub 分页游标、限流退避、Spaces/datasets 类型区分。
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, ClassVar

from core.enums import SourceKind
from core.schema.artifact import ArtifactRef
from core.schema.skill import SourceRecord

from collector.source import IndexPage, RawItem, SourceAdapter

_PENDING_SHA256 = "0" * 64
"""占位哈希：内容未获取，真实 SHA-256 由后续取得制品的环节计算。"""


class HFPoCAdapter(SourceAdapter):
    kind: ClassVar[SourceKind] = SourceKind.HUGGING_FACE

    def fetch_index(self, cursor: str | None = None) -> IndexPage:
        params = {"limit": "100"}
        if cursor is not None:
            params["cursor"] = cursor
        payload: Any = self._client.get_json("/api/models", params)
        items = tuple(payload) if isinstance(payload, list) else tuple(
            payload.get("items", ())
        )
        # TODO(PoC 后)：读取响应 Link/cursor 头；此处无更多页即止
        return IndexPage(items=items, next_cursor=None)

    def fetch_metadata(self, item: RawItem) -> SourceRecord:
        repo_id: str = item["id"]  # "org/name" 或 "name"
        author = item.get("author") or (
            repo_id.split("/")[0] if "/" in repo_id else None
        )
        return SourceRecord(
            source_kind=SourceKind.HUGGING_FACE,
            origin_url=f"https://huggingface.co/{repo_id}",
            source_object_id=repo_id,
            author=author,
            raw_name=repo_id.split("/")[-1],
            raw_description=item.get("cardData", {}).get("summary")
            if isinstance(item.get("cardData"), dict)
            else None,
            discovered_at=datetime.fromisoformat(item["_discovered_at"])
            if "_discovered_at" in item
            else datetime.min,
            last_synced_at=None,
            is_alive=not item.get("disabled", False),
            allow_internal_test=None,
            allow_public_derived_result=None,
            allow_retain_test_copy=None,
        )

    def fetch_artifact_refs(self, item: RawItem) -> Sequence[ArtifactRef]:
        repo_id: str = item["id"]
        revision = item.get("sha") or "main"
        return (
            ArtifactRef(
                bucket="external:huggingface",
                key=f"https://huggingface.co/{repo_id}/tree/{revision}",
                sha256=_PENDING_SHA256,
                size_bytes=0,
                summary=f"hf repo {repo_id} @ {revision} (not fetched)",
            ),
        )
