"""Tests for evaluation history and comparison features."""

import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from db.models import Evaluation


def test_evaluation_saved_on_eval(client, db_session):
    """Evaluation should be saved to database after /eval."""
    # Count evaluations before
    count_before = db_session.query(Evaluation).count()
    
    # Create temp repo
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "README.md").write_text("# Test")
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            mock_run.return_value = MagicMock(returncode=0)
            
            response = client.post(
                "/api/v1/eval",
                json={"repo_url": "https://github.com/test/history-test"}
            )
            
            assert response.status_code == 200
    
    # Count evaluations after
    db_session.expire_all()  # Refresh session
    count_after = db_session.query(Evaluation).count()
    
    # Should have one more
    assert count_after == count_before + 1


def test_history_returns_list(client, db_session):
    """History endpoint should return list of evaluations."""
    # First, create an evaluation
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "README.md").write_text("# Test")
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=tmpdir):
            
            mock_run.return_value = MagicMock(returncode=0)
            
            client.post(
                "/api/v1/eval",
                json={"repo_url": "https://github.com/test/history-list"}
            )
    
    # Query history
    response = client.get("/api/v1/eval/history?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert "total" in data
    assert isinstance(data["results"], list)
    assert data["total"] >= 1
    
    # Check result structure
    if len(data["results"]) > 0:
        result = data["results"][0]
        assert "id" in result
        assert "repo_url" in result
        assert "score_total" in result
        assert "grade" in result
        assert "scanned_at" in result


def test_compare_two_results(client, db_session):
    """Compare endpoint should return multiple evaluation details."""
    # Create two evaluations
    eval_ids = []
    
    for i in range(2):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "README.md").write_text(f"# Test {i}")
            
            with patch("subprocess.run") as mock_run, \
                 patch("tempfile.mkdtemp", return_value=tmpdir):
                
                mock_run.return_value = MagicMock(returncode=0)
                
                response = client.post(
                    "/api/v1/eval",
                    json={"repo_url": f"https://github.com/test/compare-{i}"}
                )
                
                # Get the ID from database
                db_session.expire_all()
                latest = db_session.query(Evaluation).order_by(Evaluation.id.desc()).first()
                eval_ids.append(latest.id)
    
    # Compare
    ids_str = ",".join(str(id) for id in eval_ids)
    response = client.get(f"/api/v1/eval/compare?ids={ids_str}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert len(data["results"]) == 2
    
    # Check structure
    for result in data["results"]:
        assert "id" in result
        assert "repo_url" in result
        assert "metrics" in result
        assert "findings" in result
        assert "meta" in result


def test_compare_empty_returns_empty(client):
    """Compare with non-existent IDs should return empty results."""
    response = client.get("/api/v1/eval/compare?ids=999999,999998")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert len(data["results"]) == 0


def test_history_pagination(client):
    """History pagination should work correctly."""
    # Query with limit=1
    response = client.get("/api/v1/eval/history?limit=1&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert len(data["results"]) <= 1
    assert data["limit"] == 1
    assert data["offset"] == 0


def test_upload_saves_to_history(client, db_session):
    """ZIP upload should also save to history."""
    # Count before
    count_before = db_session.query(Evaluation).count()
    
    # Create and upload ZIP
    files = {"README.md": "# Upload Test"}
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)
    zip_buffer.seek(0)
    
    response = client.post(
        "/api/v1/eval/upload",
        files={"file": ("test.zip", zip_buffer, "application/zip")}
    )
    
    assert response.status_code == 200
    
    # Count after
    db_session.expire_all()
    count_after = db_session.query(Evaluation).count()
    
    # Should have one more
    assert count_after == count_before + 1
