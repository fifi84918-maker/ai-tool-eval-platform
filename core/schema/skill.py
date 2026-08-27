"""Canonical Skill 与来源记录形状（PRD 22.1：Skill 与 ArtifactVersion 分离）。"""

from dataclasses import dataclass, field
from datetime import datetime

from core.enums import EntityType, LicenseClass, PermScope, SourceKind
from core.state import SkillStatus


@dataclass(frozen=True)
class SourceRecord:
    """一条来源记录（PRD 11.2）。一个 Skill 保留全部来源关系。"""

    source_kind: SourceKind
    origin_url: str
    source_object_id: str
    author: str | None
    raw_name: str
    raw_description: str | None
    discovered_at: datetime
    last_synced_at: datetime | None
    is_alive: bool
    # 三个独立的许可判断位（PRD 11.2），未判定时为 None
    allow_internal_test: bool | None
    allow_public_derived_result: bool | None
    allow_retain_test_copy: bool | None


@dataclass(frozen=True)
class Skill:
    """跨版本、跨来源归一后的逻辑 Skill。"""

    skill_id: str                      # 平台内稳定 ID（core.ids.stable_skill_id）
    canonical_name: str
    entity_type: EntityType            # 三类分开建模不混口径（D-011）
    status: SkillStatus                # 有且只有一个当前主状态（PRD 6.3）
    category_tags: tuple[str, ...]
    license_class: LicenseClass
    license_spdx: str | None           # SPDX 标识；未识别为 None 且 class=UNKNOWN
    declared_permissions: frozenset[PermScope]
    sources: tuple[SourceRecord, ...] = field(default_factory=tuple)
    created_at: datetime | None = None
    status_changed_at: datetime | None = None
