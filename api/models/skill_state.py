"""Skill State Machine for L2 Data Layer (V1A L2)."""

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel


# 11 states
SkillState = Literal[
    "DISCOVERED",
    "ACQUIRED",
    "PARSED",
    "NORMALIZED",
    "STATIC_SCANNED",
    "SANDBOX_TESTED",
    "SCORED",
    "REVIEWED",
    "PUBLISHED",
    "DEPRECATED",
    "ERROR"
]


class StateTransition(BaseModel):
    """状态转换记录。"""
    from_state: str
    to_state: str
    reason: str
    at: datetime


# Allowed transitions (directed graph)
# Normal forward flow: DISCOVERED → ... → PUBLISHED
# ERROR can be entered from any non-terminal state
# DEPRECATED can only be entered from PUBLISHED
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DISCOVERED": {"ACQUIRED", "ERROR"},
    "ACQUIRED": {"PARSED", "ERROR"},
    "PARSED": {"NORMALIZED", "ERROR"},
    "NORMALIZED": {"STATIC_SCANNED", "ERROR"},
    "STATIC_SCANNED": {"SANDBOX_TESTED", "ERROR"},
    "SANDBOX_TESTED": {"SCORED", "ERROR"},
    "SCORED": {"REVIEWED", "ERROR"},
    "REVIEWED": {"PUBLISHED", "ERROR"},
    "PUBLISHED": {"DEPRECATED"},  # Terminal state, can only deprecate
    "DEPRECATED": set(),  # Terminal state, no transitions
    "ERROR": set(),  # Terminal state, no transitions
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
