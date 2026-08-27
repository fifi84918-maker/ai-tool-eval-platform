"""Evidence store placeholder tests."""

from compliance.evidence import EvidenceStore


class TestEvidencePlaceholder:
    """Validate EvidenceStore placeholder behavior."""

    def test_store_evidence_returns_dict_with_required_fields(self):
        """EvidenceStore.store_evidence returns dict with bucket/key/sha256/size_bytes."""
        store = EvidenceStore()
        
        evidence_ref = store.store_evidence(
            skill_id="test-skill-001",
            artifact_sha="abc123",
            evidence_dict={"test": "data"},
        )
        
        assert isinstance(evidence_ref, dict)
        assert "bucket" in evidence_ref
        assert "key" in evidence_ref
        assert "sha256" in evidence_ref
        assert "size_bytes" in evidence_ref

    def test_evidence_key_format(self):
        """Evidence key follows {skill_id}/{artifact_sha}.json format."""
        store = EvidenceStore()
        
        evidence_ref = store.store_evidence(
            skill_id="skill-abc",
            artifact_sha="sha-xyz",
            evidence_dict={},
        )
        
        assert evidence_ref["key"] == "skill-abc/sha-xyz.json"

    def test_store_evidence_returns_placeholder_not_real_content(self):
        """store_evidence returns placeholder (TODO_MINIO), not real content."""
        store = EvidenceStore()
        
        evidence_dict = {
            "assertions": ["secret1", "secret2"],
            "expected_output": "secret answer",
        }
        
        evidence_ref = store.store_evidence(
            skill_id="test-001",
            artifact_sha="abc",
            evidence_dict=evidence_dict,
        )
        
        # Should not contain actual evidence content
        assert "assertions" not in evidence_ref
        assert "expected_output" not in evidence_ref
        
        # Should be placeholder
        assert evidence_ref["sha256"] == "TODO_MINIO"
        assert evidence_ref["size_bytes"] == 0
