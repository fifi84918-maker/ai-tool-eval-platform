"""许可信号规则：从 SourceRecord 三个独立许可判断位 + SPDX 元数据输出原始信号。

不判定业务结论（LicenseClass 的最终赋值 / 是否阻断由消费方决定），
只把"有没有许可证、三个权利位各自状态"映射为 findings。
"""

from analyzer.rules import RuleFinding, RuleId, RuleOutcome
from core.schema.skill import SourceRecord


def check_license_signals(
    record: SourceRecord, license_spdx: str | None
) -> tuple[RuleFinding, ...]:
    findings: list[RuleFinding] = []

    if license_spdx:
        findings.append(
            RuleFinding(
                RuleId.LICENSE_PRESENT, RuleOutcome.PASS, f"license: {license_spdx}"
            )
        )
    else:
        findings.append(
            RuleFinding(
                RuleId.LICENSE_PRESENT,
                RuleOutcome.NEED_INFO,
                "no license identified; requires manual review",
            )
        )

    for rule_id, value, label in (
        (RuleId.LICENSE_TEST_RIGHTS, record.allow_internal_test, "internal test"),
        (
            RuleId.LICENSE_PUBLIC_RESULT_RIGHTS,
            record.allow_public_derived_result,
            "public derived result",
        ),
        (
            RuleId.LICENSE_RETAIN_RIGHTS,
            record.allow_retain_test_copy,
            "retain test copy",
        ),
    ):
        if value is True:
            findings.append(
                RuleFinding(rule_id, RuleOutcome.PASS, f"{label}: allowed")
            )
        elif value is False:
            # 权利被明确拒绝是限制标记；是否阻断由消费方决定
            findings.append(
                RuleFinding(rule_id, RuleOutcome.WARN, f"{label}: denied")
            )
        else:
            findings.append(
                RuleFinding(rule_id, RuleOutcome.NEED_INFO, f"{label}: undetermined")
            )

    return tuple(findings)
