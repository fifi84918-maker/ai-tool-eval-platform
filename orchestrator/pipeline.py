"""SkillReviewPipeline：采集 → 静态检测 → 准入 → 沙箱 → 报告。

全部输入注入（stub client / 清单字段 / 运行器 / 任务计划），run() 为可
重放纯流程：同样输入产出同样报告。每阶段兜底捕获异常转入 StageResult，
不让单阶段崩溃中断整个流水线。状态推进只经 state_driver。
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from analyzer.pipeline import StaticReviewReport, static_review
from collector.source import IndexClient, RawItem, adapter_for
from core.enums import EntityType, LicenseClass, SourceKind
from core.ids import stable_skill_id
from core.schema.artifact import ArtifactRef
from core.schema.skill import Skill
from core.state import SkillStatus, StatusEvent
from orchestrator.admission import AdmissionDecision, apply_admission
from orchestrator.report import PipelineReport, StageResult
from orchestrator.state_driver import drive_status
from sandbox.dsl import TaskPlan
from sandbox.report import SandboxRunReport
from sandbox.runner import SandboxRunner

_STAGE_COLLECT = "collect"
_STAGE_STATIC = "static_review"
_STAGE_ADMISSION = "admission"
_STAGE_SANDBOX = "sandbox"


@dataclass(frozen=True)
class SkillReviewPipeline:
    """一次单 Skill 流水线的全部输入（纯数据 + 注入的协议实现）。"""

    pipeline_id: str
    source_kind: SourceKind
    raw_item: RawItem                      # 采集适配器的单条原始条目
    client: IndexClient                    # stub/真实客户端均可注入
    sandbox_runner: SandboxRunner          # LocalSimRunner / Docker…
    sandbox_plan: TaskPlan                 # 沙箱执行计划（我方编写的确定性计划）
    # 静态检测的注入输入（PoC 阶段元数据由调用方给）
    manifest_fields: Mapping[str, Any] | None = None
    file_paths: Sequence[str] | None = None
    declared_permissions: Sequence[str] | None = None
    declared_deps: Sequence[str | Mapping[str, Any]] | None = None
    status_before: SkillStatus = SkillStatus.DISCOVERED
    # 许可复核结论注入（模拟人工/许可服务在静态检测前的权利确认；
    # None = 不覆盖，沿用来源记录的三权利位）。键：allow_internal_test /
    # allow_public_derived_result / allow_retain_test_copy
    rights_override: Mapping[str, bool] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(pipeline: SkillReviewPipeline) -> PipelineReport:
    stages: list[StageResult] = []
    warnings: list[str] = []
    events: list[StatusEvent] = []

    skill: Skill | None = None
    artifact_refs: tuple[ArtifactRef, ...] = ()
    static_report: StaticReviewReport | None = None
    admission: AdmissionDecision | None = None
    sandbox_report: SandboxRunReport | None = None

    # ---- Stage 1: collect（适配器归一，不发真实网络：client 注入）----
    try:
        adapter = adapter_for(pipeline.source_kind, pipeline.client)
        record = adapter.fetch_metadata(pipeline.raw_item)
        if pipeline.rights_override is not None:
            record = replace(
                record,
                allow_internal_test=pipeline.rights_override.get(
                    "allow_internal_test", record.allow_internal_test
                ),
                allow_public_derived_result=pipeline.rights_override.get(
                    "allow_public_derived_result",
                    record.allow_public_derived_result,
                ),
                allow_retain_test_copy=pipeline.rights_override.get(
                    "allow_retain_test_copy", record.allow_retain_test_copy
                ),
            )
        artifact_refs = tuple(adapter.fetch_artifact_refs(pipeline.raw_item))
        skill = Skill(
            skill_id=stable_skill_id(
                record.source_kind.value, record.source_object_id
            ),
            canonical_name=record.raw_name,
            entity_type=EntityType.SKILL,
            status=pipeline.status_before,
            category_tags=(),
            license_class=LicenseClass.UNKNOWN,
            license_spdx=None,
            declared_permissions=frozenset(),
            sources=(record,),
        )
        events.append(StatusEvent.ARTIFACT_ACQUIRED)
        stages.append(
            StageResult(
                _STAGE_COLLECT,
                ok=True,
                detail=f"normalized {record.source_object_id}, "
                f"{len(artifact_refs)} artifact ref(s)",
            )
        )
    except Exception as exc:
        stages.append(
            StageResult(
                _STAGE_COLLECT, ok=False, error=f"{type(exc).__name__}: {exc}"
            )
        )

    # ---- Stage 2: static review ----
    if skill is not None:
        try:
            static_report = static_review(
                skill,
                artifact_refs,
                manifest_fields=pipeline.manifest_fields,
                file_paths=pipeline.file_paths,
                declared_permissions=pipeline.declared_permissions,
                declared_deps=pipeline.declared_deps,
            )
            stages.append(
                StageResult(
                    _STAGE_STATIC,
                    ok=True,
                    detail=f"{len(static_report.findings)} findings, "
                    f"summary={dict(static_report.summary)}",
                )
            )
        except Exception as exc:
            stages.append(
                StageResult(
                    _STAGE_STATIC, ok=False, error=f"{type(exc).__name__}: {exc}"
                )
            )
    else:
        stages.append(
            StageResult(_STAGE_STATIC, ok=True, skipped=True, detail="no skill")
        )

    # ---- Stage 3: admission（Task 05 确认映射）----
    if static_report is not None:
        try:
            admission = apply_admission(static_report)
            if admission.target_status_event is not None:
                events.append(admission.target_status_event)
            if admission.proceed_to_sandbox:
                events.append(StatusEvent.ADMISSION_PASSED)
            if admission.needs_manual_review:
                warnings.append("admission: needs manual review (kept at ACQUIRED)")
            warnings.extend(admission.reasons)
            stages.append(
                StageResult(
                    _STAGE_ADMISSION,
                    ok=True,
                    detail=f"proceed_to_sandbox={admission.proceed_to_sandbox}",
                )
            )
        except Exception as exc:
            stages.append(
                StageResult(
                    _STAGE_ADMISSION, ok=False, error=f"{type(exc).__name__}: {exc}"
                )
            )
    else:
        stages.append(
            StageResult(_STAGE_ADMISSION, ok=True, skipped=True, detail="no static report")
        )

    # ---- Stage 4: sandbox（仅准入通过）----
    if admission is not None and admission.proceed_to_sandbox:
        try:
            sandbox_report = pipeline.sandbox_runner.run(pipeline.sandbox_plan)
            if sandbox_report.isolated is False:
                warnings.append(
                    "sandbox runner is NOT isolated (local-sim, dev only); "
                    "results are shape-validation, not evidence"
                )
            events.append(StatusEvent.NEUTRAL_TEST_DONE)
            stages.append(
                StageResult(
                    _STAGE_SANDBOX,
                    ok=True,
                    detail=f"runner={sandbox_report.runner_name}, "
                    f"assertions={sandbox_report.all_assertions_passed}",
                )
            )
        except Exception as exc:
            stages.append(
                StageResult(
                    _STAGE_SANDBOX, ok=False, error=f"{type(exc).__name__}: {exc}"
                )
            )
    else:
        stages.append(
            StageResult(
                _STAGE_SANDBOX,
                ok=True,
                skipped=True,
                detail="admission did not clear sandbox",
            )
        )

    # ---- 状态推进（事件驱动；非法转移记录为 warning，不中断）----
    drive = drive_status(pipeline.status_before, events)
    warnings.extend(
        f"illegal transition ignored: {status.value} --{event.value}-->"
        for status, event in drive.rejected
    )

    return PipelineReport(
        pipeline_id=pipeline.pipeline_id,
        skill_id=skill.skill_id if skill else None,
        canonical_name=skill.canonical_name if skill else None,
        status_before=pipeline.status_before,
        status_after=drive.final_status,
        per_stage=tuple(stages),
        admission=admission,
        static_report=static_report,
        sandbox_report=sandbox_report,
        warnings=tuple(warnings),
    )
