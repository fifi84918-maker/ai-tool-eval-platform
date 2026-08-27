"""API endpoints integration tests."""

import json
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestSkillsAPI:
    """Test /api/v1/skills endpoints."""

    def test_search_skills_returns_200_and_list(self):
        """GET /api/v1/skills returns 200 with list of skills."""
        response = client.get("/api/v1/skills")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check structure
        first = data[0]
        assert "skill_id" in first
        assert "canonical_name" in first
        assert "evidence_grade" in first

    def test_search_skills_with_query_filters(self):
        """GET /api/v1/skills?q=hello filters results."""
        response = client.get("/api/v1/skills?q=doc")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should filter to matching skills
        if data:
            text = json.dumps(data, ensure_ascii=False).lower()
            assert "doc" in text

    def test_search_skills_pagination(self):
        """GET /api/v1/skills?limit=2&offset=1 paginates."""
        response = client.get("/api/v1/skills?limit=2&offset=0")
        assert response.status_code == 200
        page1 = response.json()
        
        response = client.get("/api/v1/skills?limit=2&offset=2")
        assert response.status_code == 200
        page2 = response.json()
        
        # Pages should be different (unless we have < 2 skills)
        if len(page1) == 2 and len(page2) > 0:
            assert page1[0]["skill_id"] != page2[0]["skill_id"]

    def test_get_skill_detail_returns_correct_skill_with_json_ld(self):
        """GET /api/v1/skills/{skill_id} returns detail with json_ld."""
        # First get a skill_id from search
        search_response = client.get("/api/v1/skills")
        skills = search_response.json()
        skill_id = skills[0]["skill_id"]
        
        response = client.get(f"/api/v1/skills/{skill_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["skill_id"] == skill_id
        assert "json_ld" in data
        if data["json_ld"]:
            assert data["json_ld"]["@context"] == "https://schema.org"
            assert data["json_ld"]["@type"] == "SoftwareApplication"

    def test_get_skill_nonexistent_returns_404(self):
        """GET /api/v1/skills/nonexistent returns 404."""
        response = client.get("/api/v1/skills/nonexistent-skill-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_openapi_json_returns_200_with_paths(self):
        """GET /openapi.json returns 200 with valid OpenAPI spec."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert "openapi" in spec
        assert "paths" in spec
        assert "/api/v1/skills" in spec["paths"]
        assert "/api/v1/skills/{skill_id}" in spec["paths"]

    def test_docs_returns_200(self):
        """GET /docs returns 200 (Swagger UI)."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_no_sensitive_data_leak_in_responses(self):
        """All endpoints do not leak sensitive data (D-005)."""
        # Test search
        response = client.get("/api/v1/skills")
        text = json.dumps(response.json(), ensure_ascii=False)
        assert "api_key" not in text
        assert "sk-" not in text
        assert "-----BEGIN" not in text
        assert "ghp_" not in text
        
        # Test detail
        search_response = client.get("/api/v1/skills")
        skills = search_response.json()
        if skills:
            skill_id = skills[0]["skill_id"]
            response = client.get(f"/api/v1/skills/{skill_id}")
            text = json.dumps(response.json(), ensure_ascii=False)
            assert "api_key" not in text
            assert "sk-" not in text
            assert "-----BEGIN" not in text
            assert "ghp_" not in text
            # Ensure evidence_grade is clamped to D/U
            detail = response.json()
            assert detail["summary"]["evidence_grade"] in ("D", "U")
