"""Seed database with sample skills from scripts/samples.py.

For local development: provides visible data on first launch.
"""

import os
import sys
import warnings

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.samples import SAMPLES


def _trial_sample_to_skill_dict(sample) -> dict:
    """Convert TrialSample to skill dict for repository."""
    # Generate skill_id from sample_id
    skill_id = f"sample-{sample.sample_id}"
    
    # Extract metadata from raw_item
    raw = sample.raw_item
    origin_url = raw.get("html_url", raw.get("id", ""))
    description = raw.get("description", sample.label)
    
    # Build canonical skill dict
    return {
        "skill_id": skill_id,
        "canonical_name": sample.manifest_fields.get("name", sample.sample_id) if sample.manifest_fields else sample.sample_id,
        "source_kind": sample.source_kind.value,
        "origin_url": origin_url,
        "description": description,
        "status": sample.expected_final_status.value,
        "evidence_grade": "D",  # Default grade for samples
        "is_alive": True,
        "author": raw.get("owner", {}).get("login") if "owner" in raw else raw.get("author"),
        "license_spdx": None,
        "declared_permissions": list(sample.declared_permissions) if sample.declared_permissions else [],
        "category_tags": [],
        "static_summary": sample.label,
        "admission_reasons": [],
        "warnings": list(sample.notes) if sample.notes else [],
    }


def seed_samples():
    """Seed database with sample skills.
    
    Safely exits if DATABASE_URL not set or connection fails.
    """
    # Check DATABASE_URL
    if not os.environ.get("DATABASE_URL"):
        warnings.warn("DATABASE_URL not set, skipping seed", RuntimeWarning)
        print("WARNING: DATABASE_URL not set, skipping seed")
        return
    
    try:
        from db import get_db, engine
        from db.models import Base
        from db.repository import SkillRepository
    except Exception as e:
        warnings.warn(f"Failed to import DB modules: {e}", RuntimeWarning)
        print(f"WARNING: Failed to import DB modules: {e}")
        return
    
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        
        with get_db() as session:
            repo = SkillRepository(session)
            
            skill_count = 0
            artifact_count = 0
            
            for sample in SAMPLES:
                # Convert to skill dict and upsert
                skill_dict = _trial_sample_to_skill_dict(sample)
                repo.upsert_skill(skill_dict)
                skill_count += 1
                
                # Add artifact reference placeholder
                # Use skill_id from dict since we generate it
                repo.add_artifact_reference(
                    skill_id=skill_dict["skill_id"],
                    bucket="evidence",
                    key=f"{skill_dict['skill_id']}/placeholder",
                    sha256="0" * 64,
                    size_bytes=0,
                    summary=f"Placeholder artifact for {sample.sample_id}",
                )
                artifact_count += 1
            
            print(f"OK: Seeded {skill_count} skills from samples")
            if artifact_count > 0:
                print(f"OK: Added {artifact_count} artifact references")
    
    except Exception as e:
        warnings.warn(f"Failed to seed database: {e}", RuntimeWarning)
        print(f"WARNING: Failed to seed database: {e}")
        return


if __name__ == "__main__":
    seed_samples()
