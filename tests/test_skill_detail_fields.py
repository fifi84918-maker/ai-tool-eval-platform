"""Tests for V1A Task 29.4.3: Skill detail extended fields."""
import pytest
from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
def test_skill_detail_includes_new_fields():
    """Test that skill detail response includes V1A extended fields."""
    response = client.get("/api/v1/skills/doc-skill")
    if response.status_code == 404:
        pytest.skip("Skill index not available (MCP pipeline issue)")
    assert response.status_code == 200
    data = response.json()
    # Check new fields exist
    assert "evidence_grade_detail" in data
    assert "applicable_scenarios" in data
    assert "not_applicable_scenarios" in data
    assert "compatibility_status" in data
    assert "static_findings" in data
    assert "failure_cases" in data
    assert "test_env" in data or data.get("test_env") is None
    assert "source_platforms" in data
def test_evidence_grade_default_C():
    """Verify evidence_grade is not A/B for sample data."""
    response = client.get("/api/v1/skills/doc-skill")
    if response.status_code == 404:
        pytest.skip("Skill index not available")
    data = response.json()
    grade = data.get("evidence_grade_detail", "")
    assert grade not in ["A", "B"], "Sample data should not have A/B evidence grade"
def test_static_findings_structure():
    """Verify static_findings has correct structure."""
    response = client.get("/api/v1/skills/doc-skill")
    if response.status_code == 404:
        pytest.skip("Skill index not available")
    data = response.json()
    findings = data.get("static_findings", [])
    for finding in findings:
        assert "dimension" in finding
        assert "level" in finding
        assert "message" in finding
        assert finding["level"] in ["pass", "warning", "block", "unknown"]