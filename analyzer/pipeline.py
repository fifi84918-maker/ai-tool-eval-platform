"""静态检测流水线：纯函数组装各规则，产出 StaticReviewReport。

无 IO：所有输入（清单字段、路径列表、注入文本）由调用方提供。
单条规则崩溃不中断流水线，兜底为 PIPELINE_RULE_CRASH 的 NEED_INFO
finding（规则可预期失败应自行产出 FAIL/NEED_INFO，见 errors.py 说明）。
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from analyzer.deps_rule import check_deps
from analyzer.license_rule import check_license_signals
from analyzer.permissions_rule import check_permissions
from analyzer.rules import RuleFinding, RuleId, RuleOutcome
from analyzer.secrets_heuristic import check_secrets_heuristic
from analyzer.structure import check_structure
from core.schema.artifact import ArtifactRef
from core.schema.skill import Skill


@dataclass(frozen=True)
class StaticReviewReport:
    """一次静态检测的完整输出。消费方据此触发状态机事件与评分。"""

    skill_id: str
    artifact_ref_keys: tuple[str, ...]
    findings: tuple[RuleFinding, ...]
    summary: Mapping[str, int] = field(default_factory=dict)  # outcome.value -> count

    @property
    def has_fail(self) -> bool:
        return any(f.outcome is RuleOutcome.FAIL for f in self.findings)


def _summarize(findings: Sequence[RuleFinding]) -> dict[str, int]:
    counts: dict[str, int] = {outcome.value: 0 for outcome in RuleOutcome}
    for finding in findings:
        counts[finding.outcome.value] += 1
    return counts


def static_review(
    skill: Skill,
    artifact_refs: Sequence[ArtifactRef],
    manifest_fields: Mapping[str, Any] | None = None,
    file_paths: Sequence[str] | None = None,
    declared_permissions: Iterable[str] | None = None,
    declared_deps: Sequence[str | Mapping[str, Any]] | None = None,
    injected_texts: Iterable[tuple[str, str]] | None = None,
) -> StaticReviewReport:
    """对单个 Skill 的一个 Artifact（引用集）执行全部静态规则。"""
    rule_calls: tuple[tuple[str, Callable[[], tuple[RuleFinding, ...]]], ...] = (
        ("structure", lambda: check_structure(manifest_fields, file_paths)),
        (
            "license",
            lambda: tuple(
                finding
                for source in skill.sources
                for finding in check_license_signals(source, skill.license_spdx)
            )
            or check_license_signals_fallback(),
        ),
        ("permissions", lambda: check_permissions(declared_permissions)),
        (
            "secrets",
            lambda: check_secrets_heuristic(
                manifest_fields, file_paths, injected_texts
            ),
        ),
        ("deps", lambda: check_deps(declared_deps)),
    )

    findings: list[RuleFinding] = []
    for rule_name, call in rule_calls:
        try:
            findings.extend(call())
        except Exception as exc:  # 规则崩溃兜底：不中断、不吞掉
            findings.append(
                RuleFinding(
                    RuleId.PIPELINE_RULE_CRASH,
                    RuleOutcome.NEED_INFO,
                    f"rule '{rule_name}' crashed: {type(exc).__name__}: {exc}",
                )
            )

    return StaticReviewReport(
        skill_id=skill.skill_id,
        artifact_ref_keys=tuple(ref.key for ref in artifact_refs),
        findings=tuple(findings),
        summary=_summarize(findings),
    )


def check_license_signals_fallback() -> tuple[RuleFinding, ...]:
    """Skill 无来源记录时的许可信号兜底。"""
    return (
        RuleFinding(
            RuleId.LICENSE_PRESENT,
            RuleOutcome.NEED_INFO,
            "skill has no source records; license signals unavailable",
        ),
    )
