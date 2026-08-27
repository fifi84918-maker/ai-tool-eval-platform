"""准入判定：把 StaticReviewReport 映射为准入决策。

实现 CLAUDE.md《准入判定规则（Task 05 评审确认）》：
- analyzer.has_fail 只是信号，不直接触发状态转移（映射在这里做）
- secrets FAIL → STATIC_BLOCKED（进 QUARANTINED）
- structure FAIL → 降级 WARN，允许继续到沙箱
- 其余 FAIL → NEED_REVIEW（人工复核；不发状态事件，停在 ACQUIRED）
- 三权利位全 NEED_INFO → 禁止进动态测试（D-008 合规红线；静态可通过）

优先级：secrets 阻断 > 其余 FAIL 人工复核 > D-008 禁沙箱 > 放行。
"""

from dataclasses import dataclass, field

from analyzer.pipeline import StaticReviewReport
from analyzer.rules import RuleId, RuleOutcome
from core.state import StatusEvent

_STRUCT_RULES = frozenset(
    {
        RuleId.STRUCT_SKILL_MD_PRESENT,
        RuleId.STRUCT_FRONTMATTER_FIELDS,
        RuleId.STRUCT_PORTABLE_PATHS,
        RuleId.STRUCT_PLACEHOLDERS,
    }
)
_RIGHTS_RULES = (
    RuleId.LICENSE_TEST_RIGHTS,
    RuleId.LICENSE_PUBLIC_RESULT_RIGHTS,
    RuleId.LICENSE_RETAIN_RIGHTS,
)


@dataclass(frozen=True)
class AdmissionDecision:
    """准入结论。target_status_event 是静态检测结果对应的状态事件
    （STATIC_BLOCKED / STATIC_PASSED / None=停在 ACQUIRED 待人工复核）；
    proceed_to_sandbox 决定是否追加 ADMISSION_PASSED 并进沙箱。"""

    proceed_to_sandbox: bool
    target_status_event: StatusEvent | None
    needs_manual_review: bool = False
    reasons: tuple[str, ...] = field(default_factory=tuple)


def apply_admission(report: StaticReviewReport) -> AdmissionDecision:
    findings = report.findings

    secrets_fail = any(
        f.rule_id is RuleId.SECRET_METADATA_HEURISTIC
        and f.outcome is RuleOutcome.FAIL
        for f in findings
    )
    structure_fails = [
        f
        for f in findings
        if f.rule_id in _STRUCT_RULES and f.outcome is RuleOutcome.FAIL
    ]
    other_fails = [
        f
        for f in findings
        if f.outcome is RuleOutcome.FAIL
        and f.rule_id not in _STRUCT_RULES
        and f.rule_id is not RuleId.SECRET_METADATA_HEURISTIC
    ]
    rights_findings = [f for f in findings if f.rule_id in _RIGHTS_RULES]
    rights_all_undetermined = bool(rights_findings) and all(
        f.outcome is RuleOutcome.NEED_INFO for f in rights_findings
    )

    if secrets_fail:
        return AdmissionDecision(
            proceed_to_sandbox=False,
            target_status_event=StatusEvent.STATIC_BLOCKED,
            reasons=("secrets heuristic FAIL -> STATIC_BLOCKED (quarantine)",),
        )

    if other_fails:
        return AdmissionDecision(
            proceed_to_sandbox=False,
            target_status_event=None,
            needs_manual_review=True,
            reasons=tuple(
                f"non-structure FAIL requires manual review: {f.rule_id.value}"
                for f in other_fails
            ),
        )

    reasons: list[str] = []
    if structure_fails:
        reasons.extend(
            f"structure FAIL downgraded to WARN: {f.rule_id.value}"
            for f in structure_fails
        )

    if rights_all_undetermined:
        reasons.append(
            "all three license rights NEED_INFO -> dynamic testing forbidden (D-008)"
        )
        return AdmissionDecision(
            proceed_to_sandbox=False,
            target_status_event=StatusEvent.STATIC_PASSED,
            reasons=tuple(reasons),
        )

    return AdmissionDecision(
        proceed_to_sandbox=True,
        target_status_event=StatusEvent.STATIC_PASSED,
        reasons=tuple(reasons),
    )
