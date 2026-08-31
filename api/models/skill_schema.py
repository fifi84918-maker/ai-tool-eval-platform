"""Canonical Skill Schema for L2 Data Layer (V1A L2)."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# Platform types
PlatformType = Literal[
    "github",
    "doubao",
    "workbuddy",
    "qianwen",
    "feishu",
    "dingtalk",
    "wecom",
    "manual"
]

# Security levels
SecurityLevel = Literal["strict", "standard", "lax"]

# V1E: skill lifecycle status
SkillStatus = Literal[
    "DISCOVERED",
    "METADATA_ONLY",
    "ACQUIRED",
    "STATIC_REVIEWED",
    "QUARANTINED",
    "RUNNABLE",
    "NEUTRAL_TESTED",
    "NATIVE_TESTED",
    "VERIFIED",
    "STALE",
    "REMOVED",
]

# V1E: entity type
EntityType = Literal["SKILL", "CONNECTOR_MCP", "EXPERT"]


class CanonicalSkill(BaseModel):
    """Canonical Skill 主表模型。
    
    代表一个经过规范化的技能，包含完整的生命周期状态。
    """
    skill_id: str                          # SHA256 hex (64 chars)
    name: str
    description: str
    platform: PlatformType
    platform_skill_id: str | None = None
    underlying_model: str | None = None    # 底层模型（如 "gpt-4"）
    license: str | None = None
    security_level: SecurityLevel = "standard"
    high_risk: bool = False
    target_domains: list[str] = []
    required_languages: list[str] = []
    cost_info: dict | None = None
    benchmark_score: float | None = None   # L4 再填
    dynamic_score: float | None = None    # V1D 动态检查评分（opt-in）
    certification: str | None = None
    
    # State machine (legacy — used by L1-L4 pipeline)
    state: str  # SkillState, but use str here to avoid circular import
    state_history: list[dict] = []         # list of StateTransition dicts

    # V1E: admission fields
    status: str = "DISCOVERED"             # SkillStatus enum value
    entity_type: str = "SKILL"             # EntityType enum value
    risk_flags: list[dict] = Field(
        default_factory=list,
        description="[{rule, severity, detail}] from static checks",
    )
    status_changed_at: datetime | None = None
    canonical_name: str | None = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # References
    source_refs: list[str] = []            # SourceRecord.source_id list
    artifact_refs: list[str] = []          # ArtifactRecord.artifact_id list
    
    model_config = {"from_attributes": True}
