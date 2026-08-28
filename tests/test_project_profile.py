"""Tests for Project Profile API endpoints (V1A Task 29.4.4)."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_create_profile():
    """Test POST /api/v1/profiles creates a new profile."""
    payload = {
        "name": "test-project",
        "languages": ["python", "typescript"],
        "frameworks": ["fastapi", "react"],
        "domains": ["web", "api"],
        "team_size": 5,
        "security_requirement": "strict",
        "description": "Test project description"
    }
    
    response = client.post("/api/v1/profiles", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    assert "id" in data
    assert "created_at" in data
    assert data["name"] == "test-project"
    assert data["languages"] == ["python", "typescript"]
    assert data["frameworks"] == ["fastapi", "react"]
    assert data["domains"] == ["web", "api"]
    assert data["team_size"] == 5
    assert data["security_requirement"] == "strict"
    assert data["description"] == "Test project description"


def test_get_profiles():
    """Test GET /api/v1/profiles returns list including created profile."""
    # Create a profile first
    payload = {
        "name": "list-test-project",
        "languages": ["go"],
        "domains": ["cli"]
    }
    create_response = client.post("/api/v1/profiles", json=payload)
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]
    
    # Get list
    response = client.get("/api/v1/profiles")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check if our created profile is in the list
    profile_ids = [p["id"] for p in data]
    assert created_id in profile_ids


def test_get_profile_not_found():
    """Test GET /api/v1/profiles/{id} returns 404 for non-existent profile."""
    response = client.get("/api/v1/profiles/nonexistent-id-12345")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Profile not found"


def test_security_requirement_default():
    """Test security_requirement defaults to 'standard' when not provided."""
    payload = {
        "name": "default-security-project",
        "languages": ["python"]
    }
    
    response = client.post("/api/v1/profiles", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["security_requirement"] == "standard"
