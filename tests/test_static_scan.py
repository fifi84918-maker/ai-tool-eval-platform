"""Tests for static repository scanner."""

import tempfile
from pathlib import Path

import pytest

from analyzer.static_scan import scan_repository


def test_scan_empty_directory_returns_baseline_scores():
    """Empty directory should return baseline scores."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = scan_repository(tmpdir)
        
        assert "metrics" in result
        assert "findings" in result
        assert "meta" in result
        
        # Check all dimensions present
        assert "accuracy" in result["metrics"]
        assert "reliability" in result["metrics"]
        assert "security" in result["metrics"]
        assert "performance" in result["metrics"]
        
        # Empty repo should have low accuracy
        assert result["metrics"]["accuracy"] < 30


def test_scan_readme_boosts_accuracy():
    """README file should boost accuracy score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create README
        (tmpdir_path / "README.md").write_text("# Test Project")
        
        result = scan_repository(tmpdir)
        
        # Should have higher accuracy than empty
        assert result["metrics"]["accuracy"] >= 15
        assert result["meta"]["has_readme"] is True


def test_scan_tests_boost_accuracy():
    """Test files should boost accuracy score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test files
        (tmpdir_path / "test_main.py").write_text("def test_foo(): pass")
        (tmpdir_path / "test_utils.py").write_text("def test_bar(): pass")
        
        result = scan_repository(tmpdir)
        
        assert result["metrics"]["accuracy"] >= 25
        assert result["meta"]["has_tests"] is True


def test_scan_env_file_lowers_security():
    """Presence of .env file should lower security score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create .env file
        (tmpdir_path / ".env").write_text("SECRET_KEY=abc123")
        
        result = scan_repository(tmpdir)
        
        # Security should be reduced
        assert result["metrics"]["security"] < 100
        
        # Should have finding
        assert len(result["findings"]) > 0
        security_findings = [f for f in result["findings"] if f["dimension"] == "security"]
        assert len(security_findings) > 0


def test_scan_hardcoded_secret_lowers_security():
    """Hardcoded secret patterns should lower security score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create file with hardcoded secret
        (tmpdir_path / "config.py").write_text("""
API_KEY = "sk-1234567890abcdefghijklmnopqrst"
""")
        
        result = scan_repository(tmpdir)
        
        # Security should be reduced
        assert result["metrics"]["security"] < 100
        
        # Should have critical finding
        critical_findings = [f for f in result["findings"] if f["severity"] == "critical"]
        assert len(critical_findings) > 0


def test_scan_lockfile_boosts_reliability():
    """Lock files should boost reliability score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create package.json and lock file
        (tmpdir_path / "package.json").write_text('{"name": "test"}')
        (tmpdir_path / "package-lock.json").write_text('{"lockfileVersion": 2}')
        
        result = scan_repository(tmpdir)
        
        # Reliability should be boosted
        assert result["metrics"]["reliability"] >= 40


def test_scan_dockerfile_boosts_performance():
    """Dockerfile should boost performance score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create Dockerfile
        (tmpdir_path / "Dockerfile").write_text("FROM python:3.12")
        
        result = scan_repository(tmpdir)
        
        # Performance should be boosted
        assert result["metrics"]["performance"] >= 40
        assert result["meta"]["has_dockerfile"] is True


def test_scan_detects_language():
    """Should detect primary language by file extensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create Python files
        (tmpdir_path / "main.py").write_text("print('hello')")
        (tmpdir_path / "utils.py").write_text("def foo(): pass")
        (tmpdir_path / "test.py").write_text("def test(): pass")
        
        result = scan_repository(tmpdir)
        
        assert result["meta"]["language"] == "Python"


def test_scan_ignores_node_modules():
    """Should ignore files in node_modules directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create node_modules
        node_modules = tmpdir_path / "node_modules"
        node_modules.mkdir()
        
        # Create many files in node_modules
        for i in range(100):
            (node_modules / f"file{i}.js").write_text("module.exports = {};")
        
        # Create one file outside
        (tmpdir_path / "index.js").write_text("console.log('hello');")
        
        result = scan_repository(tmpdir)
        
        # Should only count the one file outside node_modules
        assert result["meta"]["file_count"] == 1


def test_scan_score_in_range():
    """All scores should be in valid range (0-100) and grade should be valid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a well-structured repo
        (tmpdir_path / "README.md").write_text("# Project")
        (tmpdir_path / "test_main.py").write_text("def test(): pass")
        (tmpdir_path / "Dockerfile").write_text("FROM python:3.12")
        (tmpdir_path / "package.json").write_text('{"name": "test"}')
        (tmpdir_path / ".gitignore").write_text("node_modules/")
        
        result = scan_repository(tmpdir)
        
        # All metrics should be in range
        for key, value in result["metrics"].items():
            assert 0 <= value <= 100, f"{key} = {value} out of range"
        
        # Meta fields should be present
        assert "file_count" in result["meta"]
        assert "language" in result["meta"]
        assert isinstance(result["meta"]["has_readme"], bool)
        assert isinstance(result["meta"]["has_tests"], bool)


def test_scan_comprehensive_repository():
    """Test comprehensive repository with many features."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create complete repository structure
        (tmpdir_path / "README.md").write_text("# Awesome Project\n\nFull documentation")
        (tmpdir_path / "LICENSE").write_text("MIT License")
        (tmpdir_path / "SECURITY.md").write_text("# Security Policy")
        (tmpdir_path / ".gitignore").write_text("node_modules/\n*.pyc")
        
        # Code files
        (tmpdir_path / "main.py").write_text("def main() -> None:\n    pass")
        (tmpdir_path / "utils.py").write_text("def helper(x: int) -> int:\n    return x * 2")
        
        # Tests
        (tmpdir_path / "test_main.py").write_text("def test_main(): assert True")
        (tmpdir_path / "test_utils.py").write_text("def test_helper(): assert True")
        
        # CI
        ci_dir = tmpdir_path / ".github" / "workflows"
        ci_dir.mkdir(parents=True)
        (ci_dir / "ci.yml").write_text("name: CI")
        
        # Docker
        (tmpdir_path / "Dockerfile").write_text("FROM python:3.12")
        (tmpdir_path / "docker-compose.yml").write_text("version: '3'")
        
        # Dependency management
        (tmpdir_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        (tmpdir_path / "uv.lock").write_text("# lock file")
        
        result = scan_repository(tmpdir)
        
        # Should have high scores across the board
        assert result["metrics"]["accuracy"] >= 70
        assert result["metrics"]["reliability"] >= 70
        assert result["metrics"]["security"] >= 80
        assert result["metrics"]["performance"] >= 60
        
        # Metadata should reflect structure
        assert result["meta"]["has_readme"] is True
        assert result["meta"]["has_tests"] is True
        assert result["meta"]["has_ci"] is True
        assert result["meta"]["has_dockerfile"] is True
        assert result["meta"]["has_license"] is True
        assert result["meta"]["has_security_md"] is True
        assert result["meta"]["language"] == "Python"
        assert result["meta"]["file_count"] >= 10
