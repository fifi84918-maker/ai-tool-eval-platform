"""Task 08 试评闭环测试：5 样本状态终点、报告可序列化/可重放、合规标记。"""

import json

from core.state import SkillStatus
from scripts.run_phase0_trial import build_trial_report, run_sample, to_trial_entry
from scripts.samples import SAMPLES


def _entry(sample_id: str) -> dict:
    sample = next(s for s in SAMPLES if s.sample_id == sample_id)
    return to_trial_entry(sample, run_sample(sample))


class TestSampleClosure:
    def test_green_sample_reaches_neutral_tested(self):
        entry = _entry("S1-green")
        assert entry["status_after"] == SkillStatus.NEUTRAL_TESTED.value
        assert entry["matched_expectation"] is True
        assert entry["sandbox"]["all_assertions_passed"] is True

    def test_structure_fail_still_proceeds(self):
        entry = _entry("S2-no-skillmd")
        assert entry["status_after"] == SkillStatus.NEUTRAL_TESTED.value
        assert any("downgraded to WARN" in r for r in entry["admission"]["reasons"])

    def test_highrisk_perms_warn_but_proceed(self):
        entry = _entry("S3-highrisk-perms")
        assert entry["status_after"] == SkillStatus.NEUTRAL_TESTED.value
        assert entry["static_summary"]["warn"] >= 1

    def test_d008_sample_stops_at_static_reviewed(self):
        entry = _entry("S4-d008-rights")
        assert entry["status_after"] == SkillStatus.STATIC_REVIEWED.value
        assert entry["sandbox"] is None
        assert any("D-008" in w for w in entry["warnings"])

    def test_secrets_sample_quarantined(self):
        entry = _entry("S5-secrets")
        assert entry["status_after"] == SkillStatus.QUARANTINED.value
        assert entry["sandbox"] is None


class TestTrialReport:
    def test_all_samples_match_expectation(self):
        trial = build_trial_report()
        assert trial["sample_count"] == len(SAMPLES) == 5
        assert trial["all_matched_expectation"] is True

    def test_json_serializable_and_replayable(self):
        t1, t2 = build_trial_report(), build_trial_report()
        s1, s2 = json.dumps(t1, ensure_ascii=False), json.dumps(t2, ensure_ascii=False)
        assert json.loads(s1)["sample_count"] == 5
        # 可重放：除时间戳外全等
        d1, d2 = json.loads(s1), json.loads(s2)
        d1.pop("generated_at"), d2.pop("generated_at")
        assert d1 == d2

    def test_non_isolated_flag_and_warning(self):
        trial = build_trial_report()
        assert trial["compliance"]["sandbox_non_isolated"] is True
        assert "not evidence" in trial["compliance"]["warning"]
        # 进过沙箱的样本必须带 non_isolated 与非隔离 warning
        for entry in trial["entries"]:
            if entry["sandbox"] is not None:
                assert entry["non_isolated"] is True
                assert entry["sandbox"]["isolated"] is False
                assert any("NOT isolated" in w for w in entry["warnings"])

    def test_no_abc_evidence_grades(self):
        trial = build_trial_report()
        assert set(trial["compliance"]["evidence_grades_allowed"]) == {"D", "U"}
        for entry in trial["entries"]:
            assert entry["evidence_grade_cap"] in ("D", "U")

    def test_no_artifact_content_in_report(self):
        # 脱敏检查：序列化文本不含样本 manifest 的密钥字面量与正文类字段
        text = json.dumps(build_trial_report(), ensure_ascii=False)
        assert "fake1234fake5678" not in text  # S5 构造假凭证不得进报告
        assert "script_text" not in text
        # ArtifactRef 占位哈希不出现真实内容摘要
        assert trial_has_no_content_keys(text)


def trial_has_no_content_keys(text: str) -> bool:
    return all(key not in text for key in ("skill_md_body", "source_code", "tarball_bytes"))
