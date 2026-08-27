"""内存索引：从试评样本构建可查询的 Skill 集合。

TODO(真实数据源)：Phase 1 接 PostgreSQL 数据层后替换为 DB 索引；
搜索当前为名称/描述小写包含匹配，正式检索（分词/标签/评分排序）留 TODO。
"""

from dataclasses import dataclass, field

from mcp_server.models import ArtifactRefDTO, SkillDetail, SkillSummary
from mcp_server.policy import clamp_evidence_grade, scrub
from orchestrator.pipeline import run as run_pipeline
from orchestrator.pipeline import SkillReviewPipeline
from sandbox.runner import LocalSimRunner
from scripts.samples import SAMPLES, TrialSample, make_deterministic_plan


class _OfflineStubClient:
    def get_json(self, path, params=None):
        return {"items": []}


@dataclass(frozen=True)
class _IndexEntry:
    summary: SkillSummary
    
    detail: SkillDetail
    artifacts: tuple[ArtifactRefDTO, ...]
    search_blob: str = field(default="")


def _build_entry(sample: TrialSample) -> _IndexEntry:
    """跑一遍编排流水线取权威结论（状态/静态计数/准入），再投影 DTO。"""
    report = run_pipeline(
        SkillReviewPipeline(
            pipeline_id=f"mcp-index::{sample.sample_id}",
            source_kind=sample.source_kind,
            raw_item=sample.raw_item,
            client=_OfflineStubClient(),
            sandbox_runner=LocalSimRunner(),
            sandbox_plan=make_deterministic_plan(
                f"mcp-plan::{sample.sample_id}", sample.plan_marker
            ),
            manifest_fields=sample.manifest_fields,
            file_paths=sample.file_paths,
            declared_permissions=sample.declared_permissions,
            declared_deps=sample.declared_deps,
            rights_override=sample.rights_override,
        )
    )
    if report.skill_id is None:
        raise ValueError(f"sample {sample.sample_id} failed collect stage")

    # 描述取自公开来源元数据（raw_item），不含 manifest 正文
    description = (
        sample.raw_item.get("description")
        if isinstance(sample.raw_item.get("description"), str)
        else None
    )
    origin_url = sample.raw_item.get("html_url") or (
        f"https://huggingface.co/{sample.raw_item['id']}"
        if "id" in sample.raw_item
        else ""
    )
    grade = clamp_evidence_grade("D" if report.sandbox_report else None)

    summary = SkillSummary(
        skill_id=report.skill_id,
        canonical_name=report.canonical_name or sample.sample_id,
        entity_type="skill",
        status=report.status_after.value,
        source_kind=sample.source_kind.value,
        origin_url=origin_url,
        description=description,
        evidence_grade=grade,
    )
    detail = SkillDetail(
        summary=summary,
        author=(sample.raw_item.get("owner") or {}).get("login")
        or sample.raw_item.get("author"),
        license_spdx=None,
        declared_permissions=tuple(sample.declared_permissions or ()),
        category_tags=(),
        is_alive=True,
        static_summary=dict(report.static_report.summary)
        if report.static_report
        else None,
        admission_reasons=tuple(report.admission.reasons) if report.admission else (),
        warnings=tuple(report.warnings),
    )
    # ArtifactRef 直接从采集适配器投影（占位哈希，无内容）
    from collector.source import adapter_for

    adapter = adapter_for(sample.source_kind, _OfflineStubClient())
    artifacts = tuple(
        ArtifactRefDTO(
            bucket=ref.bucket,
            key=ref.key,
            sha256=ref.sha256,
            size_bytes=ref.size_bytes,
            summary=ref.summary,
        )
        for ref in adapter.fetch_artifact_refs(sample.raw_item)
    )
    blob = " ".join(
        filter(None, [summary["canonical_name"], description or "", summary["skill_id"]])
    ).lower()
    return _IndexEntry(summary=summary, detail=detail, artifacts=artifacts, search_blob=blob)


class InMemorySkillIndex:
    """公开样本内存索引。只含公开采集样本（D-002：无私有集合）。"""

    def __init__(self, samples: tuple[TrialSample, ...] = SAMPLES) -> None:
        self._entries: dict[str, _IndexEntry] = {}
        for sample in samples:
            entry = _build_entry(sample)
            self._entries[entry.summary["skill_id"]] = entry

    def search(self, query: str, limit: int = 10) -> tuple[SkillSummary, ...]:
        """从样本返回 SkillSummary，而不是 _IndexEntry。"""
        q = query.strip().lower()
        if not q:
            return tuple(e.summary for e in self._entries.values())[:limit]
        return tuple(
            e.summary for e in self._entries.values() if q in e.search_blob
        )[:limit]

    def get(self, skill_id: str) -> SkillDetail | None:
        """从样本中返回 SkillDetail，填充缺失字段。"""
        entry = self._entries.get(skill_id)
        return entry.detail if entry else None

    def get_artifacts(self, skill_id: str) -> tuple[ArtifactRefDTO, ...] | None:
        entry = self._entries.get(skill_id)
        return entry.artifacts if entry else None

    def __len__(self) -> int:
        return len(self._entries)
