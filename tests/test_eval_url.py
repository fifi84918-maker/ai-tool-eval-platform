"""Tests for evaluation URL endpoint."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_valid_github_url_returns_score():
    """Valid GitHub URL triggers clone and returns score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create mock repo structure
        (tmpdir_path / "README.md").write_text("# Test Repo")
        (tmpdir_path / "package.json").write_text('{"name": "test"}')
        (tmpdir_path / ".gitignore").write_text("node_modules/")
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            mock_run.return_value = MagicMock(returncode=0)
            
            response = client.post(
                "/api/v1/eval",
                json={"repo_url": "https://github.com/test/repo"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "repo_url" in data
            assert "score_total" in data
            assert "grade" in data
            assert "breakdown" in data
            assert "metrics" in data
            assert data["grade"] in ["A", "B", "C", "D", "U"]


def test_invalid_url_returns_400():
    """Non-GitHub URL returns 400 error."""
    response = client.post(
        "/api/v1/eval",
        json={"repo_url": "https://gitlab.com/test/repo"}
    )
    
    assert response.status_code == 400
    assert "github" in response.json()["detail"].lower()


def test_clone_failure_returns_400():
    """Clone failure returns 400 with error message."""
    import subprocess
    
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr=b"Repository not found"
        )
        
        response = client.post(
            "/api/v1/eval",
            json={"repo_url": "https://github.com/nonexistent/repo"}
        )
        
        assert response.status_code == 400
        assert "clone" in response.json()["detail"].lower()


def test_metrics_extraction_logic():
    """Metrics extraction correctly scores repo features."""
    from api.routers.eval import extract_metrics
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create comprehensive repo structure
        (tmpdir_path / "README.md").write_text("# Documentation")
        (tmpdir_path / "test_main.py").write_text("def test_foo(): pass")
        (tmpdir_path / ".github" / "workflows").mkdir(parents=True)
        (tmpdir_path / ".github" / "workflows" / "ci.yml").write_text("name: CI")
        (tmpdir_path / "package.json").write_text('{"name": "test"}')
        (tmpdir_path / "package-lock.json").write_text("{}")
        (tmpdir_path / ".gitignore").write_text("node_modules/")
        (tmpdir_path / "Dockerfile").write_text("FROM node:14")
        (tmpdir_path / "SECURITY.md").write_text("# Security Policy")
        
        metrics = extract_metrics(tmpdir_path)
        
        # Verify metrics are in valid range
        assert 0 <= metrics["accuracy"] <= 100
        assert 0 <= metrics["reliability"] <= 100
        assert 0 <= metrics["security"] <= 100
        assert 0 <= metrics["performance"] <= 100
        
        # High-quality repo should score well
        assert metrics["accuracy"] >= 80
        assert metrics["reliability"] >= 80


def test_response_schema():
    """Response contains all required fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "README.md").write_text("# Test")
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            mock_run.return_value = MagicMock(returncode=0)
            
            response = client.post(
                "/api/v1/eval",
                json={"repo_url": "https://github.com/test/repo"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check all required fields
            assert "repo_url" in data
            assert "metrics" in data
            assert "score_total" in data
            assert "grade" in data
            assert "breakdown" in data
            assert "scanned_at" in data
            
            # Validate types
            assert isinstance(data["score_total"], (int, float))
            assert isinstance(data["grade"], str)
            assert isinstance(data["metrics"], dict)
            assert isinstance(data["breakdown"], dict)
            
            # Validate metrics structure
            assert "accuracy" in data["metrics"]
            assert "reliability" in data["metrics"]
            assert "security" in data["metrics"]
            assert "performance" in data["metrics"]


def test_clone_timeout_returns_408():
    """Clone timeout returns 408 error."""
    import subprocess
    
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
        
        response = client.post(
            "/api/v1/eval",
            json={"repo_url": "https://github.com/test/repo"}
        )
        
        assert response.status_code == 408
        detail = response.json()["detail"].lower()
        assert "timeout" in detail or "timed out" in detail
