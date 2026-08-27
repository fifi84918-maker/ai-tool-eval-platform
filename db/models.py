"""SQLAlchemy models for Skill entities."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Skill(Base):
    """Skill 实体表：对应 PRD 中的 Skill 核心元数据。
    
    Phase 1: 基础字段，不含 manifest 正文/二进制内容（PRD D-005）。
    """
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    
    # Source metadata
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status and lifecycle
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    evidence_grade: Mapped[str] = mapped_column(String(8), nullable=False)
    is_alive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Author and license
    author: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    license_spdx: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Declared metadata (JSON fields)
    declared_permissions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    category_tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Static analysis summary (counts only, no finding details - PRD D-005)
    static_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Admission and warnings
    admission_reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    warnings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Scoring (Task 18)
    score_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Skill(skill_id={self.skill_id!r}, canonical_name={self.canonical_name!r}, status={self.status!r})>"


class ArtifactReference(Base):
    """Artifact 引用表：只存储指针和摘要，不存储内容（PRD D-005）。"""
    __tablename__ = "artifact_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    
    # Object storage pointer
    bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Summary only, no content
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ArtifactReference(skill_id={self.skill_id!r}, key={self.key!r})>"
