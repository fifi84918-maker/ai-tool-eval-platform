"""Rule engine types for recommendation system (V1A 29.2.2)."""

from pydantic import BaseModel


class RuleViolation(BaseModel):
    """规则违规记录。"""
    rule_id: str
    rule_name: str
    severity: str          # "block" | "warning" | "info"
    message: str


class RuleResult(BaseModel):
    """规则执行结果。"""
    passed: bool = True    # 是否有 block 级违规
    violations: list[RuleViolation] = []
    score_adjustment: float = 0.0
    filtered: bool = False # 是否被过滤掉
