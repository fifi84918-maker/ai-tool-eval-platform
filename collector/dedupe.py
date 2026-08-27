"""六层去重键生成（PRD 7.4 去重层级的采集侧键）。纯函数，无 IO。

层级对应：
1. 文件 SHA-256 完全相同         → 制品内容层，采集层不可得（内容未下载），
                                    由制品获取环节用真实哈希计算；此处不提供。
2. 目录归一化哈希                → 同上，core.ids.dir_hash 留给制品环节。
3-6 的采集侧可得键在本模块：
   source_repo_key      来源+repo_id（同源精确去重）
   canonical_name_key   归一化名称（同名不同来源，层级 5）
   manifest_key         元数据摘要哈希（名称+描述+作者的近似去重底座）
   license_sig          许可证签名 —— TODO(Phase 0 后)：stub，返回占位
   perm_scope_sig       权限范围签名 —— TODO(Phase 0 后)：stub，返回占位
   bundle_fingerprint   Fork/镜像谱系指纹 —— TODO(Phase 0 后)：stub，返回占位
"""

import unicodedata

from core.ids import sha256_hex
from core.schema.skill import SourceRecord

_STUB_SIG = "stub:" + "0" * 16


def source_repo_key(record: SourceRecord) -> str:
    """来源类型 + 来源对象 ID：同一来源内的精确身份键。"""
    return f"{record.source_kind.value}::{record.source_object_id}"


def canonical_name_key(raw_name: str) -> str:
    """归一化名称键（层级 5 同名识别）：NFKC、casefold、压缩分隔符。"""
    name = unicodedata.normalize("NFKC", raw_name).casefold()
    for sep in ("_", "-", " ", "."):
        name = name.replace(sep, "")
    return name


def manifest_key(record: SourceRecord) -> str:
    """元数据摘要哈希：仅名称/描述/作者等元数据，不涉制品内容。"""
    payload = "\x00".join(
        (
            canonical_name_key(record.raw_name),
            (record.raw_description or "").strip().casefold(),
            (record.author or "").casefold(),
        )
    )
    return sha256_hex(payload)


def license_sig(record: SourceRecord) -> str:
    """TODO(Phase 0 后)：许可证签名。需先取得制品/许可元数据，当前 stub。"""
    return _STUB_SIG


def perm_scope_sig(record: SourceRecord) -> str:
    """TODO(Phase 0 后)：权限范围签名。依赖静态检测产出，当前 stub。"""
    return _STUB_SIG


def bundle_fingerprint(record: SourceRecord) -> str:
    """TODO(Phase 0 后)：Fork/镜像/上游谱系指纹（层级 6）。当前 stub。"""
    return _STUB_SIG


def dedupe_keys(record: SourceRecord) -> dict[str, str]:
    """一次产出全部采集侧去重键（含 stub 项，键名稳定）。"""
    return {
        "source_repo_key": source_repo_key(record),
        "canonical_name_key": canonical_name_key(record.raw_name),
        "manifest_key": manifest_key(record),
        "license_sig": license_sig(record),
        "perm_scope_sig": perm_scope_sig(record),
        "bundle_fingerprint": bundle_fingerprint(record),
    }
