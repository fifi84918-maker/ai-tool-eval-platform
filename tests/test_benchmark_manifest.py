"""Benchmark manifest validation tests."""

import json
from pathlib import Path


class TestBenchmarkManifest:
    """Validate benchmarks.manifest.json structure and leak prevention."""

    def test_manifest_json_parseable(self):
        """benchmarks.manifest.json is valid JSON."""
        manifest_path = Path("benchmarks.manifest.json")
        assert manifest_path.exists()
        
        content = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(content)
        
        assert isinstance(manifest, dict)
        assert "private_repo" in manifest
        assert "cases" in manifest
        assert isinstance(manifest["cases"], list)

    def test_manifest_no_assertion_bodies(self):
        """Manifest contains no assertion bodies, expected outputs, or scoring weights."""
        manifest_path = Path("benchmarks.manifest.json")
        content = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(content)
        
        # Check top-level keys
        assert "assertions" not in manifest
        assert "expected_output" not in manifest
        assert "scoring_weights" not in manifest
        
        # Check all cases
        for case in manifest.get("cases", []):
            assert "assertions" not in case
            assert "expected_output" not in case
            assert "scoring_weights" not in case
            # Only hashes and pointers allowed
            assert "sha256" in case or "TODO_AFTER_SYNC" in str(case)

    def test_manifest_points_to_private_repo(self):
        """Manifest private_repo points to correct GitHub repository."""
        manifest_path = Path("benchmarks.manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        
        assert "private_repo" in manifest
        repo_url = manifest["private_repo"]
        assert "github.com" in repo_url
        assert "fifi84918-maker/ai-skill" in repo_url

    def test_manifest_note_explains_isolation(self):
        """Manifest note explains that no assertion bodies are stored."""
        manifest_path = Path("benchmarks.manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        
        assert "note" in manifest
        note = manifest["note"].lower()
        assert any(phrase in note for phrase in [
            "no assertion bodies",
            "no assertion",
            "only pointers",
            "only hashes",
        ])
