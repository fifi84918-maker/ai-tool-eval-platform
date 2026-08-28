"""Tests for Tiered Bundles API (V1A Task 29.4.5)."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_three_tiers_exist():
    """Test GET /api/v1/bundles returns exactly 3 tiered bundles."""
    response = client.get("/api/v1/bundles")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Check tiers
    tiers = {item["tier"] for item in data["items"]}
    assert tiers == {"starter", "standard", "enterprise"}


def test_bundle_skill_ids_valid():
    """Test that all bundles have non-empty skill_ids with valid format."""
    # Get all bundles
    bundles_response = client.get("/api/v1/bundles")
    assert bundles_response.status_code == 200
    bundles = bundles_response.json()["items"]
    
    # For each bundle, get details and verify skill_ids format
    for bundle_summary in bundles:
        bundle_id = bundle_summary["bundle_id"]
        detail_response = client.get(f"/api/v1/bundles/{bundle_id}")
        assert detail_response.status_code == 200
        
        bundle_detail = detail_response.json()
        skill_ids = bundle_detail["skill_ids"]
        
        # Verify skill_ids is non-empty list of strings (hex format)
        assert isinstance(skill_ids, list)
        assert len(skill_ids) > 0
        
        for skill_id in skill_ids:
            assert isinstance(skill_id, str)
            assert len(skill_id) == 64  # SHA256 hex is 64 chars
            # Verify it's valid hex
            try:
                int(skill_id, 16)
            except ValueError:
                pytest.fail(f"skill_id {skill_id} is not valid hex")


def test_recommend_strict_returns_enterprise():
    """Test POST /api/v1/bundles/recommend with strict security returns only enterprise."""
    payload = {
        "name": "test-project",
        "languages": ["python"],
        "domains": ["development"],
        "security_requirement": "strict"
    }
    
    response = client.post("/api/v1/bundles/recommend", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only return enterprise tier
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["tier"] == "enterprise"


def test_recommend_lax_returns_all():
    """Test POST /api/v1/bundles/recommend with lax security returns all 3 tiers."""
    payload = {
        "name": "test-project",
        "languages": ["python"],
        "domains": ["development"],
        "security_requirement": "lax"
    }
    
    response = client.post("/api/v1/bundles/recommend", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return all 3 tiers
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    tiers = {item["tier"] for item in data["items"]}
    assert tiers == {"starter", "standard", "enterprise"}


def test_recommend_by_domain():
    """Test domain matching affects ranking (documentation domain → starter ranks higher)."""
    payload = {
        "name": "test-project",
        "languages": [],
        "domains": ["documentation"],  # Starter targets documentation
        "security_requirement": "lax"
    }
    
    response = client.post("/api/v1/bundles/recommend", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # All 3 should be returned
    assert data["total"] == 3
    
    # First item should be one that includes documentation in target_domains
    # (starter or standard both have documentation, but starter has fewer domains so higher % match)
    first_item = data["items"][0]
    assert first_item["tier"] in ("starter", "standard")  # Both include documentation


def test_bundle_not_found():
    """Test GET /api/v1/bundles/{id} returns 404 for non-existent bundle."""
    response = client.get("/api/v1/bundles/nonexistent-bundle-id")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Bundle not found"
