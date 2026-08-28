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
    
    # Assign category_tags based on sample characteristics (Phase 1 MVP)
    category_mapping = {
        "S1-green": ("documentation",),  # doc-skill
        "S2-no-skillmd": ("development",),  # loose repo
        "S3-highrisk-perms": ("productivity",),  # cleaner-skill
        "S4-d008-rights": ("development",),  # unknown license
        "S5-secrets": ("security",),  # leaky-skill with secrets
    }
    category_tags = category_mapping.get(sample.sample_id, ())

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
        category_tags=category_tags,
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


class DatabaseSkillIndex:
    """Database-backed skill index using PostgreSQL.
    
    Implements the same interface as InMemorySkillIndex for drop-in replacement.
    Uses SkillRepository for all database operations with policy enforcement.
    """
    
    def __init__(self, session_factory=None):
        """Initialize database index.
        
        Args:
            session_factory: Optional SQLAlchemy sessionmaker.
                            If None, creates from db module.
        """
        if session_factory is None:
            from db import SessionLocal
            session_factory = SessionLocal
        
        self.session_factory = session_factory
    
    def search(self, query: str, limit: int = 10) -> tuple[SkillSummary, ...]:
        """Search skills in database.
        
        Args:
            query: Search query string
            limit: Max results
            
        Returns:
            Tuple of SkillSummary dicts
        """
        from db.repository import SkillRepository
        
        with self.session_factory() as session:
            repo = SkillRepository(session)
            skills, _ = repo.list_skills(query=query, limit=limit, offset=0)
            
            # Convert to SkillSummary TypedDict
            return tuple(
                SkillSummary(
                    skill_id=s["skill_id"],
                    canonical_name=s["canonical_name"],
                    entity_type=s["entity_type"],
                    status=s["status"],
                    source_kind=s["source_kind"],
                    origin_url=s["origin_url"],
                    description=s["description"],
                    evidence_grade=s["evidence_grade"],
                )
                for s in skills
            )
    
    def get(self, skill_id: str) -> SkillDetail | None:
        """Get skill detail from database.
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            SkillDetail dict or None
        """
        from db.repository import SkillRepository
        
        with self.session_factory() as session:
            repo = SkillRepository(session)
            skill = repo.get_skill(skill_id)
            
            if skill is None:
                return None
            
            # Convert to SkillDetail TypedDict
            summary = SkillSummary(
                skill_id=skill["skill_id"],
                canonical_name=skill["canonical_name"],
                entity_type=skill["entity_type"],
                status=skill["status"],
                source_kind=skill["source_kind"],
                origin_url=skill["origin_url"],
                description=skill["description"],
                evidence_grade=skill["evidence_grade"],
            )
            
            return SkillDetail(
                summary=summary,
                author=skill["author"],
                license_spdx=skill["license_spdx"],
                declared_permissions=tuple(skill["declared_permissions"]),
                category_tags=tuple(skill["category_tags"]),
                is_alive=skill["is_alive"],
                static_summary=skill["static_summary"],
                admission_reasons=tuple(skill["admission_reasons"]),
                warnings=tuple(skill["warnings"]),
            )
    
    def get_artifacts(self, skill_id: str) -> tuple[ArtifactRefDTO, ...] | None:
        """Get artifact references from database.
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            Tuple of ArtifactRefDTO or None
        """
        from db.repository import SkillRepository
        
        with self.session_factory() as session:
            repo = SkillRepository(session)
            refs = repo.get_artifact_references(skill_id)
            
            if not refs:
                return None
            
            return tuple(
                ArtifactRefDTO(
                    bucket=ref["bucket"],
                    key=ref["key"],
                    sha256=ref["sha256"],
                    size_bytes=ref["size_bytes"],
                    summary=ref["summary"],
                )
                for ref in refs
            )


def get_index_with_fallback():
    """Get skill index with automatic fallback to in-memory.
    
    Returns DatabaseSkillIndex if DATABASE_URL is set and connection succeeds,
    otherwise falls back to InMemorySkillIndex with warning.
    """
    import os
    import warnings
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        warnings.warn(
            "DATABASE_URL not set, using InMemorySkillIndex fallback",
            RuntimeWarning,
        )
        return InMemorySkillIndex()
    
    try:
        # Test database connection
        from db import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")  # type: ignore
        
        return DatabaseSkillIndex()
    except Exception as e:
        warnings.warn(
            f"Database connection failed ({e}), using InMemorySkillIndex fallback",
            RuntimeWarning,
        )
        return InMemorySkillIndex()
