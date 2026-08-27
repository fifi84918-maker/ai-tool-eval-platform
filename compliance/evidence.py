"""Evidence storage placeholder for Phase 1.

This module provides a stub interface for storing Skill evaluation evidence.
Phase 1: Returns bucket/key pointers only (MinIO not implemented yet).
Phase 2: Full MinIO SDK integration with presigned URLs.

SECURITY NOTE (PRD D-005):
During evaluation, the scoring Agent receives ONLY evidence_ref (bucket/key/sha256).
The Agent NEVER receives raw assertion bodies, expected outputs, or scoring weights.
This ensures the evaluation is fair and prevents answer leakage.
"""

from typing import Any


class EvidenceStore:
    """Phase 1 placeholder for evidence storage.
    
    Real implementation will use MinIO SDK to store evidence in object storage
    and return presigned URLs for time-limited access.
    
    Design:
    - store_evidence() accepts skill_id, artifact_sha256, and evidence dict
    - Returns evidence_ref with bucket/key/sha256/size_bytes
    - Actual evidence content stored in MinIO (Phase 2)
    - Scoring Agent gets evidence_ref only, not raw assertions
    """
    
    def store_evidence(
        self,
        skill_id: str,
        artifact_sha: str,
        evidence_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Store evaluation evidence and return reference pointer.
        
        Phase 1: Returns placeholder reference only.
        Phase 2: Will upload to MinIO and return presigned URL.
        
        Args:
            skill_id: Unique skill identifier
            artifact_sha: SHA256 of the artifact being evaluated
            evidence_dict: Evidence data (assertions, results, logs)
            
        Returns:
            Evidence reference with bucket/key/sha256/size_bytes.
            Agent receives ONLY this reference, not the raw evidence content.
        """
        # Phase 1 placeholder: return bucket/key structure without actual storage
        evidence_ref = {
            "bucket": "evidence",
            "key": f"{skill_id}/{artifact_sha}.json",
            "sha256": "TODO_MINIO",
            "size_bytes": 0,
        }
        
        # TODO Phase 2: Implement actual MinIO upload
        # import minio
        # client = minio.Minio(...)
        # client.put_object(bucket, key, data, length)
        # return presigned_url with expiry
        
        return evidence_ref
