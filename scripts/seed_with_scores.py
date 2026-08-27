"""Seed database with sample skills including computed scores.

Computes scores using scoring engine and writes to DB.
"""

import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import update, text
from scripts.samples import SAMPLES
from scoring import score_skill


# Metrics mapping for each sample (aligned with run_scoring.py)
SAMPLE_METRICS = {
    "S1-green": {
        "accuracy": 92.0,
        "reliability": 88.0,
        "security": 85.0,
        "performance": 90.0,
    },
    "S2-no-skillmd": {
        "accuracy": 78.0,
        "reliability": 72.0,
        "security": 65.0,
        "performance": 80.0,
    },
    "S3-highrisk-perms": {
        "accuracy": 85.0,
        "reliability": 80.0,
        "security": 55.0,
        "performance": 82.0,
    },
    "S4-d008-rights": {
        "accuracy": 70.0,
        "reliability": 65.0,
        "security": 60.0,
        "performance": 68.0,
    },
    "S5-secrets": {
        "accuracy": 45.0,
        "reliability": 40.0,
        "security": 20.0,
        "performance": 35.0,
    },
}


def _trial_sample_to_skill_dict(sample) -> dict:
    """Convert TrialSample to skill dict for repository."""
    skill_id = f"sample-{sample.sample_id}"
    raw = sample.raw_item
    origin_url = raw.get("html_url", raw.get("id", ""))
    description = raw.get("description", sample.label)
    
    return {
        "skill_id": skill_id,
        "canonical_name": sample.manifest_fields.get("name", sample.sample_id) if sample.manifest_fields else sample.sample_id,
        "source_kind": sample.source_kind.value,
        "origin_url": origin_url,
        "description": description,
        "status": sample.expected_final_status.value,
        "evidence_grade": "D",
        "is_alive": True,
        "author": raw.get("owner", {}).get("login") if "owner" in raw else raw.get("author"),
        "license_spdx": None,
        "declared_permissions": list(sample.declared_permissions) if sample.declared_permissions else [],
        "category_tags": [],
        "static_summary": sample.label,
        "admission_reasons": [],
        "warnings": list(sample.notes) if sample.notes else [],
    }


def seed_with_scores():
    """Seed database with sample skills and computed scores."""
    # Check DATABASE_URL
    if not os.environ.get("DATABASE_URL"):
        warnings.warn("DATABASE_URL not set, skipping seed", RuntimeWarning)
        print("WARNING: DATABASE_URL not set, skipping seed")
        return
    
    try:
        from db import get_db, engine
        from db.models import Base, Skill
        from db.repository import SkillRepository
    except Exception as e:
        warnings.warn(f"Failed to import DB modules: {e}", RuntimeWarning)
        print(f"WARNING: Failed to import DB modules: {e}")
        return
    
    try:
        # Ensure tables exist
        Base.metadata.create_all(engine)
        
        # Run migration to add score columns if needed
        from db.migration_add_score import add_score_columns
        add_score_columns()
        
        print()
        print("=" * 60)
        print("Seeding Skills with Scores")
        print("=" * 60)
        print()
        
        with get_db() as session:
            repo = SkillRepository(session)
            
            for sample in SAMPLES:
                # Convert to skill dict and upsert base fields
                skill_dict = _trial_sample_to_skill_dict(sample)
                repo.upsert_skill(skill_dict)
                
                # Get metrics for this sample
                metrics = SAMPLE_METRICS.get(sample.sample_id, {})
                
                if metrics:
                    # Compute score
                    score_result = score_skill(metrics)
                    
                    # Update skill with score
                    session.execute(
                        update(Skill)
                        .where(Skill.skill_id == skill_dict["skill_id"])
                        .values(
                            score_total=score_result["total"],
                            grade=score_result["grade"],
                        )
                    )
                    session.commit()
                    
                    print(f"{skill_dict['canonical_name']:20} | {score_result['total']:6.2f} | {score_result['grade']}")
                else:
                    print(f"{skill_dict['canonical_name']:20} | {'N/A':6} | N/A")
                
                # Add artifact reference placeholder
                repo.add_artifact_reference(
                    skill_id=skill_dict["skill_id"],
                    bucket="evidence",
                    key=f"{skill_dict['skill_id']}/placeholder",
                    sha256="0" * 64,
                    size_bytes=0,
                    summary=f"Placeholder artifact for {sample.sample_id}",
                )
        
        print()
        print("=" * 60)
        print(f"OK: Seeded {len(SAMPLES)} skills with scores")
        print("=" * 60)
    
    except Exception as e:
        warnings.warn(f"Failed to seed database: {e}", RuntimeWarning)
        print(f"WARNING: Failed to seed database: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    seed_with_scores()
