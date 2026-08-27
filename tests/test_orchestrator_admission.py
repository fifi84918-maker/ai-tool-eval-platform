"""准入判定测试：Task 05 确认的映射 + D-008 红线。"""

from analyzer.pipeline import StaticReviewReport
from analyzer.rules import RuleFinding, RuleId, RuleOutcome
from core.state import StatusEvent
from orchestrator.admission import apply_admission

_RIGHTS = (
    RuleId.LICENSE_TEST_RIGHTS,
    RuleId.LICENSE_PUBLIC_RESULT_RIGHTS,
    RuleId.LICENSE_RETAIN_RIGHTS,
)


def _report(*findings: RuleFinding) -> StaticReviewReport:
    return StaticReviewReport(
        skill_id="s" * 64,
        artifact_ref_keys=("k",),
        findings=tuple(findings),
        summary={},
    )


def _rights(outcome: RuleOutcome = RuleOutcome.PASS) -> list[RuleFinding]:
    return [RuleFinding(r, outcome, "x") for r in _RIGHTS]


class TestAdmissionMapping:
    def test_secrets_fail_blocks_to_quarantine(self):
        decision = apply_admission(
            _report(
                RuleFinding(
                    RuleId.SECRET_METADATA_HEURISTIC, RuleOutcome.FAIL, "hit"
                ),
                *_rights(),
            )
        )
        assert decision.proceed_to_sandbox is False
        assert decision.target_status_event is StatusEvent.STATIC_BLOCKED

    def test_structure_fail_downgraded_and_proceeds(self):
        decision = apply_admission(
            _report(
                RuleFinding(
                    RuleId.STRUCT_SKILL_MD_PRESENT, RuleOutcome.FAIL, "missing"
                ),
                *_rights(),
            )
        )
        assert decision.proceed_to_sandbox is True
        assert decision.target_status_event is StatusEvent.STATIC_PASSED
        assert any("downgraded to WARN" in r for r in decision.reasons)

    def test_other_fail_needs_manual_review(self):
        decision = apply_admission(
            _report(
                RuleFinding(RuleId.DEPS_MANIFEST_FORMAT, RuleOutcome.FAIL, "bad"),
                *_rights(),
            )
        )
        assert decision.proceed_to_sandbox is False
        assert decision.target_status_event is None
        assert decision.needs_manual_review is True

    def test_secrets_fail_wins_over_other_fails(self):
        decision = apply_admission(
            _report(
                RuleFinding(RuleId.SECRET_METADATA_HEURISTIC, RuleOutcome.FAIL, "hit"),
                RuleFinding(RuleId.DEPS_MANIFEST_FORMAT, RuleOutcome.FAIL, "bad"),
            )
        )
        assert decision.target_status_event is StatusEvent.STATIC_BLOCKED

    def test_d008_all_rights_need_info_forbids_sandbox(self):
        decision = apply_admission(_report(*_rights(RuleOutcome.NEED_INFO)))
        assert decision.proceed_to_sandbox is False
        # 静态本身通过：仍发 STATIC_PASSED，只是不进动态
        assert decision.target_status_event is StatusEvent.STATIC_PASSED
        assert any("D-008" in r for r in decision.reasons)

    def test_one_right_confirmed_allows_sandbox(self):
        findings = _rights(RuleOutcome.NEED_INFO)
        findings[0] = RuleFinding(_RIGHTS[0], RuleOutcome.PASS, "allowed")
        decision = apply_admission(_report(*findings))
        assert decision.proceed_to_sandbox is True

    def test_clean_report_proceeds(self):
        decision = apply_admission(_report(*_rights()))
        assert decision.proceed_to_sandbox is True
        assert decision.needs_manual_review is False
