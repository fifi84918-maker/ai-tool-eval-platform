"""Artifact 版本与对象存储引用。只存引用与摘要，绝不存正文/源码/二进制。"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ArtifactRef:
    """指向对象存储中一个对象的引用（不含内容）。"""

    bucket: str
    key: str
    sha256: str          # 内容摘要（hex），用于完整性校验与去重
    size_bytes: int
    summary: str | None  # 可公开的一行摘要；不得包含正文片段


@dataclass(frozen=True)
class ArtifactVersion:
    """某来源某版本的 Skill 内容档案（PRD 22.1）。内容变化必须生成新版本。"""

    artifact_id: str
    skill_id: str
    sha256: str                 # 整包内容哈希（去重层级 1）
    dir_hash: str | None        # 目录归一化哈希（去重层级 2）
    version_label: str | None   # 仓库 tag / commit / 平台版本号
    acquired_via: str           # 取得渠道说明（正常渠道，PRD 7.1）
    acquired_at: datetime
    storage_ref: ArtifactRef | None  # 临时测试副本引用；许可不允许留存时为 None
