"""流水线冒烟：stub client + 注入清单 + LocalSimRunner（确定性 RUN 步骤）。

不发真实网络、无隔离要求 —— 只验证阶段顺序、状态前后与报告字段。
注意：适配器产出的来源记录三权利位恒为 None（采集层不判许可），
因此全绿路径必须经 rights_override 注入"内部测试权利已确认"（D-008）。
"""

import sys

from core.enums import SourceKind
from core.state import SkillStatus
from orchestrator.pipeline import SkillReviewPipeline, run
from sandbox.dsl import StepKind, TaskPlan, TaskStep
from sandbox.runner import LocalSimRunner

GH_ITEM = {
    "full_name": "owner/skill-repo",
    "name": "skill-repo",
    "html_url": "https://github.com/owner/skill-repo",
    "description": "a public skill",
    "owner": {"login": "owner"},
    "default_branch": "main",
    "archived": False,
}

RIGHTS_OK = {"allow_internal_test": True}


class StubClient:
    def get_json(self, path, params=None):
        return {"items": [GH_ITEM]}


def _plan() -> TaskPlan:
    return TaskPlan(
        plan_id="smoke-plan",
        steps=(
            TaskStep(
                name="emit",
                kind=StepKind.RUN,
                argv=(sys.executable, "-c", "print('ok-123')"),
            ),
            TaskStep(
                name="exit0", kind=StepKind.ASSERT_EXIT_CODE, expect_exit_code=0
            ),
            TaskStep(
                name="marker",
                kind=StepKind.ASSERT_OUTPUT_CONTAINS,
                expect_substring="ok-123",
            ),
        ),
    )


def _pipeline(**overrides) -> SkillReviewPipeline:
    base = dict(
        pipeline_id="pl-1",
        source_kind=SourceKind.GITHUB,
        raw_item=GH_ITEM,
        client=StubClient(),
        sandbox_runner=LocalSimRunner(),
        sandbox_plan=_plan(),
        manifest_fields={"name": "skill-repo", "description": "d", "triggers": "t"},
        file_paths=["SKILL.md", "scripts/run.py"],
        declared_permissions=["file_read"],
        declared_deps=["pandas"],
        rights_override=RIGHTS_OK,
    )
    base.update(overrides)
    return SkillReviewPipeline(**base)


class TestPipelineSmoke:
    def test_full_green_path(self):
        report = run(_pipeline())
        # 阶段顺序
        assert [s.name for s in report.per_stage] == [
            "collect",
            "static_review",
            "admission",
            "sandbox",
        ]
        assert all(s.ok for s in report.per_stage)
        assert not any(s.skipped for s in report.per_stage)
        # 状态闭环：DISCOVERED → … → NEUTRAL_TESTED
        assert report.status_before is SkillStatus.DISCOVERED
        assert report.status_after is SkillStatus.NEUTRAL_TESTED
        # 报告字段
        assert report.skill_id and len(report.skill_id) == 64
        assert report.canonical_name == "skill-repo"
        assert report.sandbox_report is not None
        assert report.sandbox_report.all_assertions_passed is True
        # local-sim 非隔离必须被标记为 warning
        assert any("NOT isolated" in w for w in report.warnings)

    def test_secrets_hit_quarantines_and_skips_sandbox(self):
        report = run(
            _pipeline(
                manifest_fields={
                    "name": "x",
                    "description": "api_key = 'abcdefgh12345678'",
                }
            )
        )
        assert report.status_after is SkillStatus.QUARANTINED
        sandbox_stage = report.stage("sandbox")
        assert sandbox_stage is not None and sandbox_stage.skipped is True
        assert report.sandbox_report is None

    def test_d008_rights_unconfirmed_stops_at_static_reviewed(self):
        # 不注入权利确认：三权利位 None → 全 NEED_INFO → D-008 禁沙箱
        report = run(_pipeline(rights_override=None))
        assert any("D-008" in w for w in report.warnings)
        assert report.status_after is SkillStatus.STATIC_REVIEWED
        assert report.stage("sandbox").skipped is True
        assert report.sandbox_report is None

    def test_collect_failure_isolates_pipeline(self):
        report = run(_pipeline(raw_item={"bogus": True}))  # 缺 full_name → KeyError
        collect = report.stage("collect")
        assert collect is not None and collect.ok is False
        assert report.skill_id is None
        assert report.status_after is report.status_before  # 无事件可推进
        # 后续阶段全部跳过而非崩溃
        assert report.stage("static_review").skipped is True
        assert report.stage("admission").skipped is True
        assert report.stage("sandbox").skipped is True

    def test_replayable_same_input_same_shape(self):
        r1, r2 = run(_pipeline()), run(_pipeline())
        assert r1.status_after is r2.status_after
        assert [s.name for s in r1.per_stage] == [s.name for s in r2.per_stage]
        assert r1.skill_id == r2.skill_id
