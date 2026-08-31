"""Skill State Machine for L2 Data Layer (V1A L2) - PRD Aligned.

States aligned with PRD/技术方案 3.1 节的 11 种准入状态。
"""

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel


# 11 admission states from PRD
SkillState = Literal[
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
    "REMOVED"
]


class StateTransition(BaseModel):
    """状态转换记录。"""
    from_state: str
    to_state: str
    reason: str
    at: datetime


# Allowed transitions (按 PRD 3.1 语义)
# STALE → ACQUIRED 是回归路径（环境过期重测），不是非法回退
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DISCOVERED": {"METADATA_ONLY", "ACQUIRED", "REMOVED"},
    "METADATA_ONLY": {"ACQUIRED", "REMOVED"},  # 后来取得副本可升级
    "ACQUIRED": {"STATIC_REVIEWED", "QUARANTINED", "STALE", "REMOVED"},
    "STATIC_REVIEWED": {"RUNNABLE", "QUARANTINED", "STALE", "REMOVED"},
    "QUARANTINED": {"STATIC_REVIEWED", "REMOVED"},  # 申诉/复审通过可解除隔离
    "RUNNABLE": {"NEUTRAL_TESTED", "STALE", "REMOVED"},
    "NEUTRAL_TESTED": {"NATIVE_TESTED", "VERIFIED", "STALE", "REMOVED"},
    "NATIVE_TESTED": {"VERIFIED", "STALE", "REMOVED"},
    "VERIFIED": {"STALE", "REMOVED"},
    "STALE": {"ACQUIRED", "REMOVED"},  # 过期触发回归：重新取副本重测
    "REMOVED": set(),  # 终态
}


def can_transition(from_state: str, to_state: str) -> bool:
    """检查状态转换是否允许。
    
    Args:
        from_state: 当前状态
        to_state: 目标状态
        
    Returns:
        是否允许转换
    """
    allowed = ALLOWED_TRANSITIONS.get(from_state, set())
    return to_state in allowed


def validate_transition(from_state: str, to_state: str) -> None:
    """验证状态转换，不允许则抛出异常。
    
    Args:
        from_state: 当前状态
        to_state: 目标状态
        
    Raises:
        ValueError: 不允许的转换
    """
    if not can_transition(from_state, to_state):
        raise ValueError(
            f"Invalid state transition: {from_state} → {to_state}. "
            f"Allowed from {from_state}: {ALLOWED_TRANSITIONS.get(from_state, set())}"
        )


def create_transition(from_state: str, to_state: str, reason: str) -> StateTransition:
    """创建状态转换记录（先验证）。
    
    Args:
        from_state: 当前状态
        to_state: 目标状态
        reason: 转换原因
        
    Returns:
        StateTransition 记录
        
    Raises:
        ValueError: 不允许的转换
    """
    validate_transition(from_state, to_state)
    
    return StateTransition(
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        at=datetime.now(timezone.utc)
    )
