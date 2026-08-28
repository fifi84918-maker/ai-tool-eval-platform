"""Built-in rules for recommendation system (V1A 29.2.2)."""

from dataclasses import dataclass
from api.rules.types import RuleResult, RuleViolation
from api.schemas import ProjectProfileBase, BundleOut


@dataclass
class SecurityTierMismatchRule:
    """R001: security_tier_mismatch - 安全级别不匹配过滤规则。"""
    rule_id: str = "R001"
    rule_name: str = "security_tier_mismatch"
    
    def check(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """检查 bundle 安全级别是否满足 profile 要求。"""
        security_req = profile.security_requirement.lower()
        
        # 安全级别映射
        tier_to_level = {
            "starter": "lax",
            "standard": "standard",
            "enterprise": "strict"
        }
        bundle_level = tier_to_level.get(bundle.tier, "standard")
        
        # 级别优先级
        level_priority = {"lax": 1, "standard": 2, "strict": 3}
        
        # 如果 bundle 级别低于要求，过滤
        if level_priority.get(bundle_level, 1) < level_priority.get(security_req, 1):
            return RuleResult(
                filtered=True,
                violations=[RuleViolation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity="block",
                    message=f"Bundle 安全级别 {bundle_level} 不满足 {security_req} 要求"
                )]
            )
        
        return RuleResult()


@dataclass
class HighRiskSkillInStrictRule:
    """R002: high_risk_skill_in_strict - 严格模式下包含高风险 skill。"""
    rule_id: str = "R002"
    rule_name: str = "high_risk_skill_in_strict"
    
    def check(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """检查 strict 模式下是否包含 block 级 skill。
        
        Note: Enterprise bundles with security_level="strict" are exempt,
        as they explicitly include security audit capabilities.
        """
        if profile.security_requirement.lower() != "strict":
            return RuleResult()
        
        # Exempt enterprise bundles marked as strict (they include security audit)
        if bundle.tier == "enterprise" and bundle.security_level == "strict":
            return RuleResult()
        
        # 已知高风险 skill（S5-secrets/leaky-skill）
        HIGH_RISK_SKILLS = {
            "c2025e6a6d0d23aa57da5beb1fd95ceb65cc6c52e4caaca6ed0a213508ea7dd7"  # leaky-skill
        }
        
        has_high_risk = any(sid in HIGH_RISK_SKILLS for sid in bundle.skill_ids)
        
        if has_high_risk:
            return RuleResult(
                filtered=True,
                violations=[RuleViolation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity="block",
                    message="严格安全模式下不允许使用高风险 skill"
                )]
            )
        
        return RuleResult()


@dataclass
class DomainOverlapRule:
    """R003: domain_overlap - 领域重叠打分规则。"""
    rule_id: str = "R003"
    rule_name: str = "domain_overlap"
    
    def check(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """计算领域重叠得分。"""
        overlap = set(profile.domains) & set(bundle.target_domains)
        score_adjustment = len(overlap) * 10.0
        
        violations = []
        for domain in overlap:
            violations.append(RuleViolation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity="info",
                message=f"覆盖领域：{domain}"
            ))
        
        return RuleResult(
            score_adjustment=score_adjustment,
            violations=violations
        )


@dataclass
class LanguageOverlapRule:
    """R004: language_overlap - 语言重叠打分规则。"""
    rule_id: str = "R004"
    rule_name: str = "language_overlap"
    
    def check(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """计算语言重叠得分。"""
        overlap = set(profile.languages) & set(bundle.required_languages)
        score_adjustment = len(overlap) * 5.0
        
        violations = []
        for lang in overlap:
            violations.append(RuleViolation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity="info",
                message=f"匹配语言：{lang}"
            ))
        
        return RuleResult(
            score_adjustment=score_adjustment,
            violations=violations
        )


@dataclass
class DuplicateCapabilityRule:
    """R005: duplicate_capability - 重复能力检测规则。"""
    rule_id: str = "R005"
    rule_name: str = "duplicate_capability"
    
    def check(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """检测 bundle 内 skill 是否有重复领域（简化版：检查同名 domain）。"""
        # 简化实现：如果 target_domains 中有重复元素，发出警告
        domains = bundle.target_domains
        if len(domains) != len(set(domains)):
            return RuleResult(
                violations=[RuleViolation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity="warning",
                    message="Bundle 内存在重复的目标领域"
                )]
            )
        
        return RuleResult()


@dataclass
class PermissionAggregationRule:
    """R006: permission_aggregation - 权限聚合检测规则。"""
    rule_id: str = "R006"
    rule_name: str = "permission_aggregation"
    
    def check(self, profile: ProjectProfileBase, bundle: BundleOut) -> RuleResult:
        """检测 bundle 权限是否超限（简化版：enterprise 在 lax 下警告）。"""
        # 简化实现：enterprise bundle 包含更多 skill，在 lax 模式下提示权限警告
        if bundle.tier == "enterprise" and profile.security_requirement.lower() == "lax":
            return RuleResult(
                violations=[RuleViolation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity="warning",
                    message="Enterprise bundle 包含大量 skill，建议审查权限需求"
                )]
            )
        
        return RuleResult()


# 导出内置规则列表
BUILTIN_RULES = [
    SecurityTierMismatchRule(),
    HighRiskSkillInStrictRule(),
    DomainOverlapRule(),
    LanguageOverlapRule(),
    DuplicateCapabilityRule(),
    PermissionAggregationRule(),
]
