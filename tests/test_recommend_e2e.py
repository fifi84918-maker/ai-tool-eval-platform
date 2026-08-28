"""End-to-End Tests for Recommendation API (V1A Task 29.4.7)."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_e2e_create_profile_then_recommend_by_id():
    """Test end-to-end: create profile → recommend by ID → verify response."""
    # Step 1: Create a profile
    profile_payload = {
        "name": "e2e-test-project",
        "domains": ["documentation", "development"],
        "languages": ["python", "typescript"],
        "security_requirement": "standard"
    }
    
    create_response = client.post("/api/v1/profiles", json=profile_payload)
    assert create_response.status_code == 201
    
    profile_data = create_response.json()
    profile_id = profile_data["id"]
    
    # Step 2: Recommend by profile ID
    recommend_response = client.post(f"/api/v1/recommend/{profile_id}")
    assert recommend_response.status_code == 200
    
    rec_data = recommend_response.json()
    
    # Step 3: Verify response structure
    assert rec_data["profile_id"] == profile_id
    assert rec_data["profile_name"] == "e2e-test-project"
    assert rec_data["total"] > 0
    assert len(rec_data["items"]) > 0
    
    # Verify first bundle has skills (may be empty if index not initialized)
    first_bundle = rec_data["items"][0]
    assert "skills" in first_bundle
    assert isinstance(first_bundle["skills"], list)


def test_e2e_inline_recommend_then_history():
    """Test inline recommend → check history contains the recommendation."""
    # Step 1: Inline recommend
    payload = {
        "name": "inline-history-test",
        "domains": ["documentation"],
        "languages": ["python"],
        "security_requirement": "lax"
    }
    
    rec_response = client.post("/api/v1/recommend", json=payload)
    assert rec_response.status_code == 200
    
    rec_data = rec_response.json()
    assert rec_data["total"] > 0
    
    # Step 2: Get history
    history_response = client.get("/api/v1/recommend/history")
    assert history_response.status_code == 200
    
    history_data = history_response.json()
    assert history_data["total"] >= 1
    
    # Step 3: Verify last entry matches
    last_entry = history_data["items"][-1]
    assert last_entry["profile_name"] == "inline-history-test"
    assert "response" in last_entry
    assert last_entry["response"]["total"] > 0


def test_e2e_history_by_profile():
    """Test profile-specific history retrieval."""
    # Step 1: Create profile and recommend
    profile_payload = {
        "name": "history-lookup-test",
        "domains": ["development"],
        "languages": ["python"],
        "security_requirement": "standard"
    }
    
    create_response = client.post("/api/v1/profiles", json=profile_payload)
    assert create_response.status_code == 201
    profile_id = create_response.json()["id"]
    
    # Generate recommendation
    rec_response = client.post(f"/api/v1/recommend/{profile_id}")
    assert rec_response.status_code == 200
    
    # Step 2: Get history for this profile
    history_response = client.get(f"/api/v1/recommend/history/{profile_id}")
    assert history_response.status_code == 200
    
    history_data = history_response.json()
    assert history_data["total"] >= 1
    
    # All entries should match this profile_id
    for entry in history_data["items"]:
        assert entry["profile_id"] == profile_id
    
    # Step 3: Get history for non-existent profile → 404
    fake_response = client.get("/api/v1/recommend/history/nonexistent-id-99999")
    assert fake_response.status_code == 404
    assert "No recommendation history for profile" in fake_response.json()["detail"]


def test_e2e_strict_only_enterprise():
    """Test strict security returns only enterprise bundle."""
    payload = {
        "name": "strict-test",
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


def test_endpoint_no_prefix_clash():
    """Test that /api/v1/recommend/history doesn't clash with /{profile_id}."""
    # OPTIONS/GET to history endpoint should not 500
    response = client.get("/api/v1/recommend/history")
    assert response.status_code == 200  # Should work
    
    # Response should have expected structure
    data = response.json()
    assert "total" in data
    assert "items" in data
