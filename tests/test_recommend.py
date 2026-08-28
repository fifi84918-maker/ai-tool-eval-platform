"""Tests for Recommendation Generation API (V1A Task 29.4.6)."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_recommend_inline_profile():
    """Test POST /api/v1/recommend with inline profile."""
    payload = {
        "name": "test-project",
        "domains": ["documentation"],
        "languages": ["python"],
        "security_requirement": "lax"
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return all 3 tiers (lax security)
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Starter should rank first (documentation domain matches better)
    first_item = data["items"][0]
    assert first_item["tier"] == "starter"
    
    # Skills field should exist (may be empty if index not initialized)
    assert "skills" in first_item
    assert isinstance(first_item["skills"], list)


def test_recommend_by_profile_id():
    """Test POST /api/v1/recommend/{profile_id} with stored profile."""
    # Create a profile first
    profile_payload = {
        "name": "stored-project",
        "domains": ["development", "productivity"],
        "languages": ["python", "typescript"],
        "security_requirement": "standard"
    }
    create_response = client.post("/api/v1/profiles", json=profile_payload)
    assert create_response.status_code == 201
    
    profile_id = create_response.json()["id"]
    profile_name = create_response.json()["name"]
    
    # Recommend based on stored profile
    response = client.post(f"/api/v1/recommend/{profile_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Profile info should be filled
    assert data["profile_id"] == profile_id
    assert data["profile_name"] == profile_name
    
    # Should return 2 tiers (standard security: enterprise + standard)
    assert data["total"] == 2
    assert len(data["items"]) == 2
    
    # Items should have skills field
    assert all("skills" in item for item in data["items"])


def test_recommend_strict_filters():
    """Test strict security requirement filters to only enterprise."""
    payload = {
        "name": "strict-project",
        "domains": ["security"],
        "languages": ["python"],
        "security_requirement": "strict"
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only return enterprise tier
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["tier"] == "enterprise"


def test_recommend_match_reasons():
    """Test that match_reasons are generated and contain Chinese text."""
    payload = {
        "name": "test-project",
        "domains": ["documentation", "development"],
        "languages": ["python"],
        "security_requirement": "lax"
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # First item should have match reasons
    first_item = data["items"][0]
    assert "match_reasons" in first_item
    assert len(first_item["match_reasons"]) > 0
    
    # Should contain Chinese text (security requirement)
    reasons_text = " ".join(first_item["match_reasons"])
    assert "安全要求" in reasons_text
    
    # Should mention matched domains
    assert any("覆盖领域" in reason or "匹配语言" in reason for reason in first_item["match_reasons"])


def test_recommend_profile_not_found():
    """Test POST /api/v1/recommend/{id} returns 404 for non-existent profile."""
    response = client.post("/api/v1/recommend/nonexistent-profile-id-12345")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Profile not found"


def test_recommend_skills_expanded():
    """Test that skills field exists and has expected structure."""
    payload = {
        "name": "test-project",
        "domains": ["documentation"],
        "languages": ["python"],
        "security_requirement": "lax"
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Get first bundle
    first_bundle = data["items"][0]
    assert "skills" in first_bundle
    assert isinstance(first_bundle["skills"], list)
    
    # If skills are loaded, verify structure
    if len(first_bundle["skills"]) > 0:
        first_skill = first_bundle["skills"][0]
        
        # Should have required fields
        assert "skill_id" in first_skill
        assert "name" in first_skill
        
        # Should have optional fields with correct types
        assert "grade" in first_skill
        assert "score_total" in first_skill
        assert "metrics" in first_skill
        assert isinstance(first_skill["metrics"], dict)
