"""core：跨模块共享契约（类型/枚举/状态机/ID 纯函数）。

零业务逻辑、零 IO、零 ORM。collector / analyzer / sandbox / scoring / backend
均只依赖本包中的类型定义与纯函数。
"""

from core.enums import (
    BundleTier,
    EntityType,
    EvidenceGrade,
    LicenseClass,
    PermScope,
    ScoreDimension,
    SourceKind,
)
from core.state import SkillStatus, StatusEvent, transition

__all__ = [
    "BundleTier",
    "EntityType",
    "EvidenceGrade",
    "LicenseClass",
    "PermScope",
    "ScoreDimension",
    "SourceKind",
    "SkillStatus",
    "StatusEvent",
    "transition",
]
