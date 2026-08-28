"""Rule engine for recommendation system (V1A 29.2.2)."""

from typing import Protocol
from api.rules.types import RuleResult
from api.schemas import ProjectProfileBase, BundleOut


class Rule(Protocol):
    """规则接口（Protocol）。"""
    rule_id: str
    rule_name: str
    
    def check(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """检查规则，返回结果。"""
        ...


class RuleEngine:
    """规则引擎：执行所有规则并汇总结果。"""
    
    def __init__(self, rules: list[Rule]):
        """初始化规则引擎。
        
        Args:
            rules: 规则列表
        """
        self.rules = rules
    
    def evaluate(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """评估 bundle 对 profile 的匹配度。
        
        Args:
            profile: 项目画像
            bundle: Bundle 候选
            
        Returns:
            汇总的规则结果
        """
        # 汇总结果
        all_violations = []
        total_score_adjustment = 0.0
        is_filtered = False
        
        # 执行所有规则
        for rule in self.rules:
            result = rule.check(profile, bundle)
            
            # 收集违规
            all_violations.extend(result.violations)
            
            # 累加分数调整
            total_score_adjustment += result.score_adjustment
            
            # 如果被过滤，标记（任一规则过滤即过滤）
            if result.filtered:
                is_filtered = True
        
        # 判断是否通过（无 block 级违规）
        has_block = any(v.severity == "block" for v in all_violations)
        passed = not has_block
        
        return RuleResult(
            passed=passed,
            violations=all_violations,
            score_adjustment=total_score_adjustment,
            filtered=is_filtered,
        )
