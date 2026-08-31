"""Canonical Skill Schema for L2 Data Layer (V1A L2)."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel


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
    certification: str | None = None
    
    # State machine
    state: str  # SkillState, but use str here to avoid circular import
    state_history: list[dict] = []         # list of StateTransition dicts
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # References
    source_refs: list[str] = []            # SourceRecord.source_id list
    artifact_refs: list[str] = []          # ArtifactRecord.artifact_id list
    
    model_config = {"from_attributes": True}
