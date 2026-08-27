"""Phase 0 试评闭环脚本（Task 08）。

对 scripts/samples.py 的 5 个构造样本逐个执行
collector→analyzer→admission→sandbox(LocalSimRunner) 流水线，
产出可审计 TrialReport(JSON) 写入 reports/ 并打印脱敏摘要。

合规声明：
- 不发真实网络（stub client）、不下载/输出任何 Skill 正文；
- LocalSimRunner 非隔离：non_isolated=true，结果只做形状验证，
  不构成测试证据；证据等级一律不高于 D/U（本报告不产生 A/B/C）。
"""

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# 允许 `python scripts/run_phase0_trial.py` 直跑（仓库根不在 sys.path 时）
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.enums import EvidenceGrade  # noqa: E402
from orchestrator.pipeline import SkillReviewPipeline, run  # noqa: E402
from orchestrator.report import PipelineReport  # noqa: E402
from sandbox.runner import LocalSimRunner  # noqa: E402
from scripts.samples import SAMPLES, TrialSample, make_deterministic_plan  # noqa: E402

_NON_ISOLATED_WARNING = "results are shape-validation, not evidence"


class _StubClient:
    """离线 stub：任何请求返回空页（本脚本不调用 fetch_index）。"""

    def get_json(self, path, params=None):
        return {"items": []}


def run_sample(sample: TrialSample) -> PipelineReport:
    pipeline = SkillReviewPipeline(
        pipeline_id=f"phase0-trial::{sample.sample_id}",
        source_kind=sample.source_kind,
        raw_item=sample.raw_item,
        client=_StubClient(),
        sandbox_runner=LocalSimRunner(),
        sandbox_plan=make_deterministic_plan(
            f"plan::{sample.sample_id}", sample.plan_marker
        ),
        manifest_fields=sample.manifest_fields,
        file_paths=sample.file_paths,
        declared_permissions=sample.declared_permissions,
        declared_deps=sample.declared_deps,
        rights_override=sample.rights_override,
    )
    return run(pipeline)


def to_trial_entry(sample: TrialSample, report: PipelineReport) -> dict:
    """单样本报告条目（脱敏：不含 manifest 原文/正文，只有结论与计数）。"""
    non_isolated = report.sandbox_report is None or not report.sandbox_report.isolated
    return {
        "sample_id": sample.sample_id,
        "label": sample.label,
        "skill_id": report.skill_id,
        "canonical_name": report.canonical_name,
        "status_before": report.status_before.value,
        "status_after": report.status_after.value,
        "expected_final_status": sample.expected_final_status.value,
        "matched_expectation": report.status_after is sample.expected_final_status,
        "stages": [
            {
                "name": s.name,
                "ok": s.ok,
                "skipped": s.skipped,
                "error": s.error,
            }
            for s in report.per_stage
        ],
        "static_summary": dict(report.static_report.summary)
        if report.static_report
        else None,
        "admission": {
            "proceed_to_sandbox": report.admission.proceed_to_sandbox,
            "needs_manual_review": report.admission.needs_manual_review,
            "reasons": list(report.admission.reasons),
        }
        if report.admission
        else None,
        "sandbox": {
            "runner": report.sandbox_report.runner_name,
            "isolated": report.sandbox_report.isolated,
            "all_assertions_passed": report.sandbox_report.all_assertions_passed,
        }
        if report.sandbox_report
        else None,
        "non_isolated": non_isolated,
        # 本次试评不构成证据：动态跑过也只记 D（仅形状验证），未跑记 U
        "evidence_grade_cap": (
            EvidenceGrade.D.value if report.sandbox_report else EvidenceGrade.U.value
        ),
        "bundle_hint": None,  # D-010：Bundle 聚合属 Phase 1，字段预留
        "warnings": list(report.warnings),
        "notes": list(sample.notes),
    }


def build_trial_report() -> dict:
    entries = []
    for sample in SAMPLES:
        report = run_sample(sample)
        entries.append(to_trial_entry(sample, report))
    return {
        "trial_id": "phase0-trial-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "compliance": {
            "no_artifact_content_fetched": True,
            "no_real_network": True,
            "sandbox_non_isolated": True,
            "warning": _NON_ISOLATED_WARNING,
            "evidence_grades_allowed": [EvidenceGrade.D.value, EvidenceGrade.U.value],
        },
        "sample_count": len(entries),
        "all_matched_expectation": all(e["matched_expectation"] for e in entries),
        "entries": entries,
    }


def main() -> int:
    trial = build_trial_report()

    reports_dir = _REPO_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / "phase0_trial_report.json"
    out_path.write_text(
        json.dumps(trial, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"TrialReport -> {out_path}")
    print(f"samples: {trial['sample_count']}, "
          f"all_matched: {trial['all_matched_expectation']}")
    for entry in trial["entries"]:
        print(
            f"  {entry['sample_id']:<22} {entry['status_before']} -> "
            f"{entry['status_after']:<17} "
            f"expected={entry['expected_final_status']:<17} "
            f"{'OK' if entry['matched_expectation'] else 'MISMATCH'}"
        )
    return 0 if trial["all_matched_expectation"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
