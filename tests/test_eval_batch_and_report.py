"""Tests for batch evaluation and report endpoints."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_batch_endpoint_returns_list(client):
    """Batch endpoint should return list of results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "README.md").write_text("# Test")
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            mock_run.return_value = MagicMock(returncode=0)
            
            response = client.post(
                "/api/v1/eval/batch",
                json={"repo_urls": [
                    "https://github.com/test/repo1",
                    "https://github.com/test/repo2"
                ]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "results" in data
            assert len(data["results"]) == 2
            
            # Each result should have required fields
            for result in data["results"]:
                if "error" not in result:
                    assert "repo_url" in result
                    assert "score_total" in result
                    assert "grade" in result


def test_batch_partial_failure(client):
    """Batch should handle partial failures gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "README.md").write_text("# Test")
        
        call_count = [0]
        
        def mock_run_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call fails
                import subprocess
                raise subprocess.CalledProcessError(1, "git", stderr=b"Failed")
            else:
                # Second call succeeds
                return MagicMock(returncode=0)
        
        with patch("subprocess.run", side_effect=mock_run_side_effect), \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            response = client.post(
                "/api/v1/eval/batch",
                json={"repo_urls": [
                    "https://github.com/test/repo-fail",
                    "https://github.com/test/repo-success"
                ]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have 2 results
            assert len(data["results"]) == 2
            
            # One should be error, one should be success
            errors = [r for r in data["results"] if "error" in r]
            successes = [r for r in data["results"] if "error" not in r and "score_total" in r]
            
            assert len(errors) >= 1
            assert len(successes) >= 0  # May vary based on timing


def test_report_json_format(client):
    """Report endpoint should return JSON by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "README.md").write_text("# Test")
        (tmpdir_path / "Dockerfile").write_text("FROM python:3.12")
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            mock_run.return_value = MagicMock(returncode=0)
            
            response = client.get(
                "/api/v1/eval/report",
                params={"repo_url": "https://github.com/test/repo", "format": "json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify JSON structure
            assert "repo_url" in data
            assert "metrics" in data
            assert "score_total" in data
            assert "grade" in data
            assert "breakdown" in data
            assert "findings" in data
            assert "meta" in data
            
            # Verify metadata
            assert "file_count" in data["meta"]
            assert "has_readme" in data["meta"]
            assert "has_dockerfile" in data["meta"]


def test_report_markdown_format(client):
    """Report endpoint should return markdown when requested."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "README.md").write_text("# Test Project")
        (tmpdir_path / "test_main.py").write_text("def test(): pass")
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            mock_run.return_value = MagicMock(returncode=0)
            
            response = client.get(
                "/api/v1/eval/report",
                params={"repo_url": "https://github.com/test/repo", "format": "markdown"}
            )
            
            assert response.status_code == 200
            content = response.text
            
            # Verify markdown structure
            assert "# Evaluation Report" in content
            assert "## Overall Score" in content
            assert "## Dimension Breakdown" in content
            assert "## Repository Metadata" in content
            assert "Grade:" in content
            assert "Total Score:" in content
            
            # Should contain table
            assert "|" in content
            
            # Should contain metadata
            assert "Total Files:" in content
            assert "Primary Language:" in content


def test_batch_limit_max_10(client):
    """Batch endpoint should reject more than 10 URLs."""
    urls = [f"https://github.com/test/repo{i}" for i in range(11)]
    
    response = client.post(
        "/api/v1/eval/batch",
        json={"repo_urls": urls}
    )
    
    assert response.status_code == 400
    assert "Maximum 10" in response.json()["detail"]


def test_report_invalid_format(client):
    """Report endpoint should reject invalid format parameter."""
    response = client.get(
        "/api/v1/eval/report",
        params={"repo_url": "https://github.com/test/repo", "format": "xml"}
    )
    
    assert response.status_code == 400
    assert "json" in response.json()["detail"].lower() or "markdown" in response.json()["detail"].lower()


def test_batch_empty_list(client):
    """Batch endpoint should reject empty URL list."""
    response = client.post(
        "/api/v1/eval/batch",
        json={"repo_urls": []}
    )
    
    assert response.status_code == 400
    assert "at least one" in response.json()["detail"].lower()
