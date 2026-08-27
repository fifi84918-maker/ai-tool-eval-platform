"""共享数据形状（dataclass 定义，无行为、无校验、无序列化）。"""

from core.schema.artifact import ArtifactRef, ArtifactVersion
from core.schema.score import (
    BundleItem,
    BundleRecommendation,
    DimensionScore,
    ScoreRecord,
)
from core.schema.skill import Skill, SourceRecord
from core.schema.test_run import EvidenceRef, StepResult, TestRun

__all__ = [
    "ArtifactRef",
    "ArtifactVersion",
    "BundleItem",
    "BundleRecommendation",
    "DimensionScore",
    "EvidenceRef",
    "ScoreRecord",
    "Skill",
    "SourceRecord",
    "StepResult",
    "TestRun",
]
