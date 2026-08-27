"""Seed database from Phase 0 trial report.

Reads reports/phase0_trial_report.json and populates PostgreSQL
with Skill entities and artifact references.
"""

import json
from pathlib import Path

from db import get_db
from db.repository import SkillRepository


def seed_from_trial_report(report_path: Path = Path("reports/phase0_trial_report.json")):
    """Seed database from trial report.
    
    Args:
        report_path: Path to trial report JSON file
    """
    if not report_path.exists():
        print(f"ERROR: {report_path} not found")
        print("Run scripts/run_phase0_trial.py first to generate the report")
        return
    
    # Load report
    report = json.loads(report_path.read_text(encoding="utf-8"))
    
    print(f"Seeding from trial report: {report['trial_id']}")
    print(f"Sample count: {report['sample_count']}")
    
    skill_count = 0
    artifact_count = 0
    
    with get_db() as session:
        repo = SkillRepository(session)
        
        for entry in report.get("entries", []):
            skill_id = entry.get("skill_id")
            if not skill_id:
                continue
            
            # Build skill dict
            skill_dict = {
                "skill_id": skill_id,
                "canonical_name": entry.get("label", "unknown"),
                "source_kind": entry.get("source_kind", "github"),
                "origin_url": entry.get("origin_url", ""),
                "description": entry.get("description"),
                "status": entry.get("status_after", "UNKNOWN"),
                "evidence_grade": entry.get("evidence_grade_cap", "U"),
                "is_alive": True,
                "author": None,
                "license_spdx": None,
                "declared_permissions": entry.get("declared_permissions", []),
                "category_tags": [],
                "static_summary": entry.get("static_summary"),
                "admission_reasons": entry.get("admission_reasons", []),
                "warnings": entry.get("warnings", []),
            }
            
            # Upsert skill
            repo.upsert_skill(skill_dict)
            skill_count += 1
            
            # Add artifact references (if any)
            for artifact in entry.get("artifacts", []):
                repo.add_artifact_reference(
                    skill_id=skill_id,
                    bucket=artifact.get("bucket", "artifacts"),
                    key=artifact.get("key", f"{skill_id}/artifact.json"),
                    sha256=artifact.get("sha256", ""),
                    size_bytes=artifact.get("size_bytes", 0),
                    summary=artifact.get("summary"),
                )
                artifact_count += 1
    
    print(f"✓ Seeded {skill_count} skills from trial report")
    print(f"✓ Added {artifact_count} artifact references")


if __name__ == "__main__":
    seed_from_trial_report()
