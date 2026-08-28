"""Repository pattern for Skill database operations."""

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import Skill, ArtifactReference, SourceRecord, ArtifactVersion, LicenseAssessment
from mcp_server.policy import scrub, clamp_evidence_grade


class SkillRepository:
    """Repository for Skill CRUD operations with policy enforcement.
    
    All queries apply policy.scrub() for D-005 compliance (no content/source leakage).
    Evidence grades are clamped to D/U (D-008 compliance).
    """
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
    
    def get_skill(self, skill_id: str) -> Optional[dict]:
        """Get skill by skill_id.
        
        Args:
            skill_id: Unique skill identifier
            
        Returns:
            Scrubbed skill dict or None if not found
        """
        skill = self.session.query(Skill).filter_by(skill_id=skill_id).first()
        if skill is None:
            return None
        
        return self._to_dict_scrubbed(skill)
    
    def list_skills(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "score",
    ) -> tuple[list[dict], int]:
        """List skills with optional query filter, pagination, and sorting.
        
        Args:
            query: Optional search query (matches canonical_name or description)
            limit: Max results to return
            offset: Number of results to skip
            sort_by: Sort order - "score" (score_total desc) or "recent" (updated_at desc)
            
        Returns:
            Tuple of (skill list, total count)
        """
        q = self.session.query(Skill)
        
        # Apply query filter
        if query:
            search_pattern = f"%{query.lower()}%"
            q = q.filter(
                or_(
                    Skill.canonical_name.ilike(search_pattern),
                    Skill.description.ilike(search_pattern),
                )
            )
        
        # Apply sorting
        if sort_by == "recent":
            q = q.order_by(Skill.updated_at.desc())
        else:  # default to "score"
            # Sort by score_total descending, with nulls last
            q = q.order_by(Skill.score_total.desc().nullslast())
        
        # Get total count before pagination
        total = q.count()
        
        # Apply pagination
        results = q.limit(limit).offset(offset).all()
        
        # Convert to scrubbed dicts
        skills = [self._to_dict_scrubbed(skill) for skill in results]
        
        return skills, total
    
    def upsert_skill(self, skill_dict: dict) -> dict:
        """Insert or update skill from canonical dict.
        
        Args:
            skill_dict: Skill data (from core/models.py CanonicalSkill or similar)
            
        Returns:
            Scrubbed skill dict after upsert
        """
        skill_id = skill_dict["skill_id"]
        
        # Check if skill exists
        existing = self.session.query(Skill).filter_by(skill_id=skill_id).first()
        
        if existing:
            # Update existing
            for key, value in skill_dict.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            skill = existing
        else:
            # Insert new
            skill = Skill(**skill_dict)
            self.session.add(skill)
        
        self.session.commit()
        self.session.refresh(skill)
        
        return self._to_dict_scrubbed(skill)
    
    def add_artifact_reference(
        self,
        skill_id: str,
        bucket: str,
        key: str,
        sha256: str,
        size_bytes: int,
        summary: Optional[str] = None,
    ) -> dict:
        """Add artifact reference pointer (no content stored - PRD D-005).
        
        Args:
            skill_id: Associated skill ID
            bucket: Object storage bucket
            key: Object storage key
            sha256: Artifact SHA256 hash
            size_bytes: Artifact size in bytes
            summary: Optional summary text (no content)
            
        Returns:
            Scrubbed artifact reference dict
        """
        ref = ArtifactReference(
            skill_id=skill_id,
            bucket=bucket,
            key=key,
            sha256=sha256,
            size_bytes=size_bytes,
            summary=summary,
        )
        
        self.session.add(ref)
        self.session.commit()
        self.session.refresh(ref)
        
        return scrub({
            "skill_id": ref.skill_id,
            "bucket": ref.bucket,
            "key": ref.key,
            "sha256": ref.sha256,
            "size_bytes": ref.size_bytes,
            "summary": ref.summary,
        })
    
    def get_artifact_references(self, skill_id: str) -> list[dict]:
        """Get all artifact references for a skill.
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            List of scrubbed artifact reference dicts
        """
        refs = self.session.query(ArtifactReference).filter_by(skill_id=skill_id).all()
        
        return [
            scrub({
                "bucket": ref.bucket,
                "key": ref.key,
                "sha256": ref.sha256,
                "size_bytes": ref.size_bytes,
                "summary": ref.summary,
            })
            for ref in refs
        ]
    
    def _to_dict_scrubbed(self, skill: Skill) -> dict:
        """Convert Skill ORM object to scrubbed dict.
        
        Args:
            skill: Skill ORM instance
            
        Returns:
            Scrubbed dict with clamped evidence grade
        """
        skill_dict = {
            "skill_id": skill.skill_id,
            "canonical_name": skill.canonical_name,
            "entity_type": "skill",
            "source_kind": skill.source_kind,
            "origin_url": skill.origin_url,
            "description": skill.description,
            "status": skill.status,
            "evidence_grade": clamp_evidence_grade(skill.evidence_grade),
            "is_alive": skill.is_alive,
            "author": skill.author,
            "license_spdx": skill.license_spdx,
            "declared_permissions": skill.declared_permissions or [],
            "category_tags": skill.category_tags or [],
            "static_summary": skill.static_summary,
            "admission_reasons": skill.admission_reasons or [],
            "warnings": skill.warnings or [],
            "score_total": getattr(skill, "score_total", None),
            "grade": getattr(skill, "grade", None),
        }
        
        return scrub(skill_dict)


class SourceRepository:
    """Repository for SourceRecord operations (V1A PRD 22.1)."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_id(self, source_id: str) -> Optional[SourceRecord]:
        """Get source record by ID."""
        return self.session.query(SourceRecord).filter_by(id=source_id).first()
    
    def get_by_platform_object(self, platform: str, platform_object_id: str) -> Optional[SourceRecord]:
        """Get source record by platform and platform_object_id."""
        return self.session.query(SourceRecord).filter_by(
            platform=platform,
            platform_object_id=platform_object_id
        ).first()
    
    def upsert_by_platform(
        self, 
        platform: str, 
        platform_object_id: str, 
        **fields
    ) -> SourceRecord:
        """Insert or update source record by platform+platform_object_id.
        
        Args:
            platform: Platform identifier (e.g., 'github', 'huggingface')
            platform_object_id: Platform-specific object ID
            **fields: Additional fields to set/update
            
        Returns:
            SourceRecord instance after upsert
        """
        existing = self.get_by_platform_object(platform, platform_object_id)
        
        if existing:
            # Update existing record
            for key, value in fields.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            self.session.flush()
            return existing
        else:
            # Create new record
            source_id = fields.pop("id", f"{platform}::{platform_object_id}")
            new_record = SourceRecord(
                id=source_id,
                platform=platform,
                platform_object_id=platform_object_id,
                **fields
            )
            self.session.add(new_record)
            self.session.flush()
            return new_record
    
    def list_acquired(self, limit: int = 100) -> list[SourceRecord]:
        """List source records with acquired=True."""
        return self.session.query(SourceRecord).filter_by(acquired=True).limit(limit).all()


class ArtifactVersionRepository:
    """Repository for ArtifactVersion operations (V1A PRD 22.1)."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_id(self, artifact_id: str) -> Optional[ArtifactVersion]:
        """Get artifact version by ID."""
        return self.session.query(ArtifactVersion).filter_by(id=artifact_id).first()
    
    def get_by_content_hash(self, content_hash: str) -> Optional[ArtifactVersion]:
        """Get artifact version by content hash."""
        return self.session.query(ArtifactVersion).filter_by(content_hash=content_hash).first()
    
    def add(self, artifact_version: ArtifactVersion) -> ArtifactVersion:
        """Add new artifact version.
        
        Args:
            artifact_version: ArtifactVersion instance to add
            
        Returns:
            Added ArtifactVersion instance
        """
        self.session.add(artifact_version)
        self.session.flush()
        return artifact_version
    
    def list_by_source(self, source_id: str, limit: int = 100) -> list[ArtifactVersion]:
        """List artifact versions for a given source."""
        return self.session.query(ArtifactVersion).filter_by(source_id=source_id).limit(limit).all()


class LicenseRepository:
    """Repository for LicenseAssessment operations (V1A PRD 22.1)."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_id(self, assessment_id: str) -> Optional[LicenseAssessment]:
        """Get license assessment by ID."""
        return self.session.query(LicenseAssessment).filter_by(id=assessment_id).first()
    
    def get_by_artifact_version(self, artifact_version_id: str) -> Optional[LicenseAssessment]:
        """Get license assessment for an artifact version."""
        return self.session.query(LicenseAssessment).filter_by(
            artifact_version_id=artifact_version_id
        ).first()
    
    def add(self, assessment: LicenseAssessment) -> LicenseAssessment:
        """Add new license assessment.
        
        Args:
            assessment: LicenseAssessment instance to add
            
        Returns:
            Added LicenseAssessment instance
        """
        self.session.add(assessment)
        self.session.flush()
        return assessment
    
    def list_needs_review(self, limit: int = 100) -> list[LicenseAssessment]:
        """List assessments that need human review."""
        return self.session.query(LicenseAssessment).filter_by(
            needs_human_review=True
        ).limit(limit).all()
