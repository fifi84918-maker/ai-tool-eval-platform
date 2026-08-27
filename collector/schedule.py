"""增量调度占位：游标 dataclass + 纯函数 next_due。不持久化、无时钟副作用。"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from core.enums import SourceKind


@dataclass(frozen=True)
class SyncCursor:
    """一个来源的增量同步状态（内存态；持久化留给数据层）。"""

    source_kind: SourceKind
    last_seen_etag: str | None = None
    last_synced_at: datetime | None = None
    page_cursor: str | None = None


def next_due(
    cursor: SyncCursor,
    now: datetime,
    interval: timedelta = timedelta(hours=24),
) -> bool:
    """纯函数：该来源是否到期需要同步。now 由调用方注入，不读系统时钟。

    从未同步过（last_synced_at is None）视为到期。
    """
    if cursor.last_synced_at is None:
        return True
    return now - cursor.last_synced_at >= interval


def advanced(cursor: SyncCursor, *, synced_at: datetime, etag: str | None) -> SyncCursor:
    """纯函数：返回同步完成后的新游标（不修改原对象）。"""
    return SyncCursor(
        source_kind=cursor.source_kind,
        last_seen_etag=etag,
        last_synced_at=synced_at,
        page_cursor=None,
    )
