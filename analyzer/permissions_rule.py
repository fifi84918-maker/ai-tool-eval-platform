"""权限声明规则：声明的权限字符串集对照 core.enums.PermScope。

输出未知声明、高风险声明、零声明三类信号；不决策是否拒绝（D-012 的
人工确认与准入判断在消费方/治理层）。
"""

from collections.abc import Iterable

from analyzer.rules import RuleFinding, RuleId, RuleOutcome
from core.enums import PermScope

# 高风险权限：删除、执行、支付、审批、对外发送/发布、凭证（PRD D-012 语义）
HIGH_RISK_SCOPES: frozenset[PermScope] = frozenset(
    {
        PermScope.FILE_DELETE,
        PermScope.SHELL_EXEC,
        PermScope.MESSAGING_SEND,
        PermScope.CONTENT_PUBLISH,
        PermScope.PAYMENT,
        PermScope.APPROVAL,
        PermScope.CREDENTIALS,
    }
)


def check_permissions(declared: Iterable[str] | None) -> tuple[RuleFinding, ...]:
    """declared 为清单中声明的权限字符串（如 x-permissions 列表）；
    None 表示清单不可得。"""
    findings: list[RuleFinding] = []

    if declared is None:
        return (
            RuleFinding(
                RuleId.PERM_NONE_DECLARED,
                RuleOutcome.NEED_INFO,
                "no permission declaration available",
            ),
        )

    declared_list = [d.strip().lower() for d in declared if d and d.strip()]
    known_values = {scope.value for scope in PermScope}

    unknown = sorted(d for d in declared_list if d not in known_values)
    if unknown:
        findings.append(
            RuleFinding(
                RuleId.PERM_UNKNOWN_SCOPE,
                RuleOutcome.WARN,
                f"unknown permission scopes declared: {', '.join(unknown)}",
            )
        )
    else:
        findings.append(
            RuleFinding(
                RuleId.PERM_UNKNOWN_SCOPE,
                RuleOutcome.PASS,
                "all declared scopes recognized",
            )
        )

    high_risk = sorted(
        d for d in declared_list if d in known_values and PermScope(d) in HIGH_RISK_SCOPES
    )
    findings.append(
        RuleFinding(
            RuleId.PERM_HIGH_RISK,
            RuleOutcome.WARN if high_risk else RuleOutcome.PASS,
            f"high-risk scopes declared: {', '.join(high_risk)}"
            if high_risk
            else "no high-risk scopes declared",
        )
    )

    if not declared_list:
        findings.append(
            RuleFinding(
                RuleId.PERM_NONE_DECLARED,
                RuleOutcome.INFO,
                "empty permission declaration (zero scopes)",
            )
        )

    return tuple(findings)
