"""Tests for Bundle data model and API endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from mcp_server.index import BUNDLE_SAMPLES, InMemoryBundleIndex, InMemorySkillIndex


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def bundle_index():
    """Bundle index fixture."""
    return InMemoryBundleIndex()


@pytest.fixture
def skill_index():
    """Skill index fixture."""
    return InMemorySkillIndex()


def test_bundle_samples_exist():
    """Test that at least 3 bundle samples exist."""
    assert len(BUNDLE_SAMPLES) >= 3, f"Expected at least 3 bundle samples, got {len(BUNDLE_SAMPLES)}"


def test_bundle_skill_ids_valid(bundle_index, skill_index):
    """Test that all bundle skill_ids reference existing skills."""
    all_skill_ids = {entry.summary["skill_id"] for entry in skill_index._entries.values()}
    
    for bundle in bundle_index.bundles():
        bundle_id = bundle["bundle_id"]
        skill_ids = bundle["skill_ids"]
        
        for skill_id in skill_ids:
            assert skill_id in all_skill_ids, (
                f"Bundle {bundle_id} references non-existent skill: {skill_id}"
            )


def test_bundle_api_list(client):
    """Test GET /api/v1/bundles returns 200 and list structure."""
    response = client.get("/api/v1/bundles")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    
    # Check at least 3 bundles returned
    assert len(data["items"]) >= 3
    
    # Check each item has required fields (no skill_ids in summary)
    for item in data["items"]:
        assert "bundle_id" in item
        assert "name" in item
        assert "description" in item
        assert "category" in item
        assert "skill_ids" not in item  # Should not be in summary


def test_bundle_api_list_search(client):
    """Test bundle search functionality."""
    # Search for "安全" should match "安全审计套装"
    response = client.get("/api/v1/bundles?q=安全")
    assert response.status_code == 200
    data = response.json()
    
    # Should find at least one bundle
    assert len(data["items"]) >= 1
    
    # Check that results contain the search term
    found = any("安全" in item["name"] or "安全" in item["description"] for item in data["items"])
    assert found, "Search results should contain bundles matching '安全'"


def test_bundle_api_detail(client):
    """Test GET /api/v1/bundles/{bundle_id} returns correct structure."""
    # Use tiered bundle
    bundle_id = "bundle-starter"
    
    response = client.get(f"/api/v1/bundles/{bundle_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check complete bundle structure
    assert data["bundle_id"] == bundle_id
    assert "name" in data
    assert "description" in data
    assert "category" in data
    assert "skill_ids" in data  # Should be present in detail
    assert "tags" in data
    assert "tier" in data
    
    # Check types
    assert isinstance(data["skill_ids"], list)
    assert isinstance(data["tags"], list)
    
    # Check skill_ids is not empty
    assert len(data["skill_ids"]) > 0


def test_bundle_api_detail_not_found(client):
    """Test GET /api/v1/bundles/{bundle_id} returns 404 for non-existent bundle."""
    response = client.get("/api/v1/bundles/nonexistent-bundle-id")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_bundle_index_search():
    """Test InMemoryBundleIndex search functionality."""
    index = InMemoryBundleIndex()
    
    # Search all
    all_bundles = index.search_bundles("")
    assert len(all_bundles) >= 3
    
    # Search with query
    results = index.search_bundles("文档")
    assert len(results) >= 1
    
    # Verify results contain search term
    for bundle in results:
        assert "文档" in bundle["name"] or "文档" in bundle["description"]


def test_bundle_index_get():
    """Test InMemoryBundleIndex get_bundle method."""
    index = InMemoryBundleIndex()
    
    bundle_id = BUNDLE_SAMPLES[0]["bundle_id"]
    bundle = index.get_bundle(bundle_id)
    
    assert bundle is not None
    assert bundle["bundle_id"] == bundle_id
    
    # Test non-existent
    none_bundle = index.get_bundle("non-existent-id")
    assert none_bundle is None


def test_bundle_categories_match_existing():
    """Test that bundle categories use existing category slugs."""
    # Categories from the web frontend categories page
    valid_categories = {
        "documentation",
        "development",
        "security",
        "productivity",
        "automation",
        "data-science",
        "communication",
        "utilities",
    }
    
    for bundle in BUNDLE_SAMPLES:
        category = bundle["category"]
        assert category in valid_categories, (
            f"Bundle {bundle['bundle_id']} uses invalid category: {category}"
        )


def test_bundles_by_skill(client):
    """Test GET /api/v1/bundles/by-skill/{skill_id} returns correct bundle list."""
    # Use a skill that is in multiple tiered bundles
    # doc-skill (219c93e5...) is in bundle-starter, bundle-standard, and bundle-enterprise
    skill_id = "219c93e5365609e6060c9afe1d88571324b4fff1a518f16f75353b0cab159733"
    
    response = client.get(f"/api/v1/bundles/by-skill/{skill_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    
    # Should find at least one bundle
    assert len(data["items"]) > 0
    
    # Verify the bundle contains this skill (should be in all three tiers)
    bundle_ids = [item["bundle_id"] for item in data["items"]]
    assert "bundle-starter" in bundle_ids or "bundle-standard" in bundle_ids or "bundle-enterprise" in bundle_ids
    
    # Check item structure (should be summary format, no skill_ids)
    for item in data["items"]:
        assert "bundle_id" in item
        assert "name" in item
        assert "description" in item
        assert "category" in item
        assert "skill_ids" not in item


def test_bundles_by_skill_not_found(client):
    """Test GET /api/v1/bundles/by-skill/{skill_id} returns empty list for non-existent skill."""
    # Use a non-existent skill_id
    skill_id = "nonexistent-skill-id-12345"
    
    response = client.get(f"/api/v1/bundles/by-skill/{skill_id}")
    
    # Should return 200 with empty list, not 404
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 0
    assert data["total"] == 0


def test_bundles_by_skill_multiple_results(client):
    """Test that a skill in multiple bundles returns all of them."""
    # Use loose-repo (0766e96c...) which is in all three tiered bundles
    skill_id = "0766e96cdeb4121ba7aeac64bcc1fe4a0ab46563a70805f0d2d0767b19eb8e31"
    
    response = client.get(f"/api/v1/bundles/by-skill/{skill_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should find multiple bundles (all three tiers)
    assert len(data["items"]) >= 2
    
    bundle_ids = [item["bundle_id"] for item in data["items"]]
    # Should be in at least 2 of the tiered bundles
    assert "bundle-starter" in bundle_ids
    assert "bundle-standard" in bundle_ids or "bundle-enterprise" in bundle_ids
