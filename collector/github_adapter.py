"""GitHub 来源 PoC 适配器：repo 元数据 → SourceRecord + ArtifactRef。

只构造引用（archive tarball URL 作为 key），不下载任何内容。
TODO(PoC 后)：真实分页（Link header）、限流退避（X-RateLimit-*）、
代码搜索发现（SKILL.md / 已知结构）。当前 fetch_index 用注入 client 的
单次调用 + 简单游标占位。
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


class GitHubPoCAdapter(SourceAdapter):
    kind: ClassVar[SourceKind] = SourceKind.GITHUB

    def fetch_index(self, cursor: str | None = None) -> IndexPage:
        params = {"per_page": "100"}
        if cursor is not None:
            params["page"] = cursor
        payload: Any = self._client.get_json("/search/repositories", params)
        items = tuple(payload.get("items", ()))
        # TODO(PoC 后)：按 Link header 翻页；此处用页码 +1 占位
        next_cursor = str(int(cursor or "1") + 1) if items else None
        return IndexPage(items=items, next_cursor=next_cursor)

    def fetch_metadata(self, item: RawItem) -> SourceRecord:
        full_name: str = item["full_name"]  # "owner/repo"
        owner = item.get("owner") or {}
        return SourceRecord(
            source_kind=SourceKind.GITHUB,
            origin_url=item.get("html_url") or f"https://github.com/{full_name}",
            source_object_id=full_name,
            author=owner.get("login"),
            raw_name=item.get("name") or full_name.split("/")[-1],
            raw_description=item.get("description"),
            discovered_at=datetime.fromisoformat(item["_discovered_at"])
            if "_discovered_at" in item
            else datetime.min,
            last_synced_at=None,
            is_alive=not item.get("archived", False),
            allow_internal_test=None,
            allow_public_derived_result=None,
            allow_retain_test_copy=None,
        )

    def fetch_artifact_refs(self, item: RawItem) -> Sequence[ArtifactRef]:
        full_name: str = item["full_name"]
        ref = item.get("default_branch") or "HEAD"
        # archive tarball URL 仅作为引用 key；不发起下载
        return (
            ArtifactRef(
                bucket="external:github",
                key=f"https://api.github.com/repos/{full_name}/tarball/{ref}",
                sha256=_PENDING_SHA256,
                size_bytes=0,
                summary=f"github repo {full_name} @ {ref} (not fetched)",
            ),
        )
