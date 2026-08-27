"""Task 08 试评样本（内嵌常量；如需 yaml 需先过依赖评审，标 TODO）。

5 个样本全部为**构造的公开元数据形状**（不发真实网络、不含任何 Skill
正文/脚本源码/密钥真值）；secrets 样本中的 api_key 字面量是特意构造的
启发式触发用假值，非真实凭证。
"""

import sys
from dataclasses import dataclass, field
from typing import Any

from core.enums import SourceKind
from core.state import SkillStatus
from sandbox.dsl import StepKind, TaskPlan, TaskStep


def make_deterministic_plan(plan_id: str, marker: str) -> TaskPlan:
    """确定性 RUN 步骤（python -c print + 断言），不跑任何外部制品。"""
    return TaskPlan(
        plan_id=plan_id,
        steps=(
            TaskStep(
                name="emit",
                kind=StepKind.RUN,
                argv=(sys.executable, "-c", f"print('{marker}')"),
            ),
            TaskStep(name="exit0", kind=StepKind.ASSERT_EXIT_CODE, expect_exit_code=0),
            TaskStep(
                name="marker",
                kind=StepKind.ASSERT_OUTPUT_CONTAINS,
                expect_substring=marker,
            ),
        ),
    )


def _gh_item(full_name: str, description: str) -> dict[str, Any]:
    owner, name = full_name.split("/")
    return {
        "full_name": full_name,
        "name": name,
        "html_url": f"https://github.com/{full_name}",
        "description": description,
        "owner": {"login": owner},
        "default_branch": "main",
        "archived": False,
    }


_RIGHTS_OK = {"allow_internal_test": True}


@dataclass(frozen=True)
class TrialSample:
    sample_id: str
    label: str                              # 样本设计意图（进报告）
    source_kind: SourceKind
    raw_item: dict[str, Any]
    manifest_fields: dict[str, Any] | None
    file_paths: tuple[str, ...] | None
    declared_permissions: tuple[str, ...] | None
    declared_deps: tuple[str, ...] | None
    rights_override: dict[str, bool] | None
    expected_final_status: SkillStatus      # 测试断言用
    plan_marker: str = "trial-ok"
    notes: tuple[str, ...] = field(default_factory=tuple)


SAMPLES: tuple[TrialSample, ...] = (
    TrialSample(
        sample_id="S1-green",
        label="结构合规正面样本：全绿至 NEUTRAL_TESTED",
        source_kind=SourceKind.GITHUB,
        raw_item=_gh_item("acme/doc-skill", "public documentation skill"),
        manifest_fields={"name": "doc-skill", "description": "d", "triggers": "t"},
        file_paths=("SKILL.md", "scripts/run.py"),
        declared_permissions=("file_read",),
        declared_deps=("pandas",),
        rights_override=_RIGHTS_OK,
        expected_final_status=SkillStatus.NEUTRAL_TESTED,
    ),
    TrialSample(
        sample_id="S2-no-skillmd",
        label="结构缺失样本：无 SKILL.md，structure FAIL 降级 WARN 继续",
        source_kind=SourceKind.GITHUB,
        raw_item=_gh_item("acme/loose-repo", "repo without SKILL.md"),
        manifest_fields={"name": "loose", "description": "d", "triggers": "t"},
        file_paths=("readme.md", "main.py"),
        declared_permissions=("file_read",),
        declared_deps=(),
        rights_override=_RIGHTS_OK,
        expected_final_status=SkillStatus.NEUTRAL_TESTED,
        notes=("structure FAIL -> WARN by Task 05 mapping",),
    ),
    TrialSample(
        sample_id="S3-highrisk-perms",
        label="高风险权限样本：declare delete/shell，WARN 继续",
        source_kind=SourceKind.HUGGING_FACE,
        raw_item={"id": "acme/cleaner-skill", "author": "acme", "sha": "abc1"},
        manifest_fields={"name": "cleaner", "description": "d", "triggers": "t"},
        file_paths=("SKILL.md",),
        declared_permissions=("file_delete", "shell_exec", "file_read"),
        declared_deps=(),
        rights_override=_RIGHTS_OK,
        expected_final_status=SkillStatus.NEUTRAL_TESTED,
        notes=("high-risk perms only WARN at admission; human confirm is runtime concern (D-012)",),
    ),
    TrialSample(
        sample_id="S4-d008-rights",
        label="D-008 样本：三权利位 None，禁入沙箱停 STATIC_REVIEWED",
        source_kind=SourceKind.GITHUB,
        raw_item=_gh_item("acme/unknown-license", "no license info"),
        manifest_fields={"name": "ul", "description": "d", "triggers": "t"},
        file_paths=("SKILL.md",),
        declared_permissions=("file_read",),
        declared_deps=(),
        rights_override=None,
        expected_final_status=SkillStatus.STATIC_REVIEWED,
    ),
    TrialSample(
        sample_id="S5-secrets",
        label="secrets 命中样本：元数据含凭证字面量（构造假值）→ QUARANTINED",
        source_kind=SourceKind.GITHUB,
        raw_item=_gh_item("acme/leaky-skill", "demo"),
        manifest_fields={
            "name": "leaky",
            # 构造的假凭证字面量，仅用于触发启发式；非真实密钥
            "description": "api_key = 'fake1234fake5678'",
        },
        file_paths=("SKILL.md",),
        declared_permissions=("file_read",),
        declared_deps=(),
        rights_override=_RIGHTS_OK,
        expected_final_status=SkillStatus.QUARANTINED,
    ),
)
