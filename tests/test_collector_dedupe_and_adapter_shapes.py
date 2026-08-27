"""collector 契约测试：去重键稳定性 + 适配器返回形状。全部用 stub client，无网络。"""

from datetime import datetime, timedelta

import pytest

from collector.dedupe import (
    canonical_name_key,
    dedupe_keys,
    manifest_key,
    source_repo_key,
)
from collector.errors import UnsupportedSource
from collector.schedule import SyncCursor, advanced, next_due
from collector.source import IndexPage, adapter_for
from core.enums import SourceKind
from core.schema.artifact import ArtifactRef
from core.schema.skill import SourceRecord


class StubClient:
    """记录调用、返回预置 JSON 的 stub；不发任何网络请求。"""

    def __init__(self, payload):
        self.payload = payload
        self.calls: list[tuple[str, dict | None]] = []

    def get_json(self, path, params=None):
        self.calls.append((path, dict(params) if params else None))
        return self.payload


def _record(**overrides) -> SourceRecord:
    base = dict(
        source_kind=SourceKind.GITHUB,
        origin_url="https://github.com/owner/repo",
        source_object_id="owner/repo",
        author="owner",
        raw_name="My-Skill_Pack",
        raw_description="A test skill.",
        discovered_at=datetime(2026, 1, 1),
        last_synced_at=None,
        is_alive=True,
        allow_internal_test=None,
        allow_public_derived_result=None,
        allow_retain_test_copy=None,
    )
    base.update(overrides)
    return SourceRecord(**base)


class TestDedupeKeys:
    def test_source_repo_key(self):
        assert source_repo_key(_record()) == "github::owner/repo"

    def test_canonical_name_key_normalizes(self):
        assert canonical_name_key("My-Skill_Pack") == canonical_name_key("my skill.pack")
        assert canonical_name_key("Ａｂｃ") == canonical_name_key("abc")  # NFKC 全角

    def test_manifest_key_stable_and_sensitive(self):
        assert manifest_key(_record()) == manifest_key(_record())
        assert manifest_key(_record()) != manifest_key(
            _record(raw_description="Different.")
        )

    def test_dedupe_keys_shape(self):
        keys = dedupe_keys(_record())
        assert set(keys) == {
            "source_repo_key",
            "canonical_name_key",
            "manifest_key",
            "license_sig",
            "perm_scope_sig",
            "bundle_fingerprint",
        }
        # stub 项统一占位（Phase 0）
        assert keys["license_sig"].startswith("stub:")
        assert keys["perm_scope_sig"].startswith("stub:")
        assert keys["bundle_fingerprint"].startswith("stub:")


GH_ITEM = {
    "full_name": "owner/repo",
    "name": "repo",
    "html_url": "https://github.com/owner/repo",
    "description": "desc",
    "owner": {"login": "owner"},
    "default_branch": "main",
    "archived": False,
}

HF_ITEM = {
    "id": "org/skill-model",
    "author": "org",
    "sha": "abc123",
    "disabled": False,
}


class TestAdapterShapes:
    def test_github_shapes(self):
        adapter = adapter_for(SourceKind.GITHUB, StubClient({"items": [GH_ITEM]}))
        page = adapter.fetch_index()
        assert isinstance(page, IndexPage) and len(page.items) == 1

        record = adapter.fetch_metadata(GH_ITEM)
        assert isinstance(record, SourceRecord)
        assert record.source_kind is SourceKind.GITHUB
        assert record.source_object_id == "owner/repo"
        # 许可判断位不得在采集层判定
        assert record.allow_internal_test is None
        assert record.allow_public_derived_result is None
        assert record.allow_retain_test_copy is None

        refs = adapter.fetch_artifact_refs(GH_ITEM)
        assert len(refs) == 1 and isinstance(refs[0], ArtifactRef)
        assert refs[0].sha256 == "0" * 64  # 占位哈希，内容未下载
        assert refs[0].size_bytes == 0

    def test_hf_shapes(self):
        adapter = adapter_for(SourceKind.HUGGING_FACE, StubClient([HF_ITEM]))
        page = adapter.fetch_index()
        assert isinstance(page, IndexPage) and len(page.items) == 1

        record = adapter.fetch_metadata(HF_ITEM)
        assert record.source_kind is SourceKind.HUGGING_FACE
        assert record.origin_url == "https://huggingface.co/org/skill-model"
        assert record.allow_internal_test is None

        refs = adapter.fetch_artifact_refs(HF_ITEM)
        assert refs[0].sha256 == "0" * 64

    def test_unsupported_kinds_rejected(self):
        # PoC 只注册 GitHub/HF：其余来源类型（含创作者提交/三平台）走不出适配器
        for kind in (
            SourceKind.WORKBUDDY_MARKET,
            SourceKind.QIANWEN_OFFICE,
            SourceKind.DOUBAO_WORK,
            SourceKind.CREATOR_SUBMISSION,
        ):
            with pytest.raises(UnsupportedSource):
                adapter_for(kind, StubClient({}))


class TestSchedule:
    def test_never_synced_is_due(self):
        cursor = SyncCursor(source_kind=SourceKind.GITHUB)
        assert next_due(cursor, now=datetime(2026, 1, 1)) is True

    def test_interval_gate(self):
        synced = datetime(2026, 1, 1, 0, 0)
        cursor = SyncCursor(source_kind=SourceKind.GITHUB, last_synced_at=synced)
        assert next_due(cursor, now=synced + timedelta(hours=1)) is False
        assert next_due(cursor, now=synced + timedelta(hours=24)) is True

    def test_advanced_is_pure(self):
        cursor = SyncCursor(source_kind=SourceKind.GITHUB, page_cursor="3")
        new = advanced(cursor, synced_at=datetime(2026, 1, 2), etag='W/"x"')
        assert cursor.page_cursor == "3"  # 原对象未变
        assert new.last_seen_etag == 'W/"x"' and new.page_cursor is None
