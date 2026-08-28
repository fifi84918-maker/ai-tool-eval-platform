"""Evaluation API endpoints - clone repo and score."""

import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from scoring import score_skill


router = APIRouter()


class EvalRequest(BaseModel):
    repo_url: str


class EvalResponse(BaseModel):
    repo_url: str
    metrics: dict
    score_total: float
    grade: str
    breakdown: dict
    scanned_at: str


def extract_metrics(repo_path: Path) -> dict:
    """Extract heuristic metrics from cloned repo.
    
    Returns dict with accuracy, reliability, security, performance (0-100 each).
    """
    metrics = {
        "accuracy": 0.0,
        "reliability": 0.0,
        "security": 0.0,
        "performance": 0.0,
    }
    
    # Accuracy: documentation + tests + CI
    if (repo_path / "README.md").exists() or (repo_path / "SKILL.md").exists():
        metrics["accuracy"] += 20
    
    # Check for test files
    test_patterns = ["test_*.py", "*_test.py", "*.test.js", "*.test.ts", "test/*.py"]
    has_tests = any(repo_path.rglob(pattern) for pattern in test_patterns)
    if has_tests:
        metrics["accuracy"] += 20
    
    # Check for CI
    if (repo_path / ".github" / "workflows").exists():
        workflows = list((repo_path / ".github" / "workflows").glob("*.yml"))
        workflows += list((repo_path / ".github" / "workflows").glob("*.yaml"))
        if workflows:
            metrics["accuracy"] += 10
    
    # Baseline for having basic structure
    metrics["accuracy"] += 50
    
    # Reliability: package management + lockfiles + .gitignore
    if (repo_path / "package.json").exists() or (repo_path / "pyproject.toml").exists():
        metrics["reliability"] += 30
    
    # Check for lock files
    lock_files = ["package-lock.json", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock", "uv.lock"]
    if any((repo_path / lf).exists() for lf in lock_files):
        metrics["reliability"] += 20
    
    if (repo_path / ".gitignore").exists():
        metrics["reliability"] += 10
    
    # Baseline
    metrics["reliability"] += 40
    
    # Security: check for .env, hardcoded secrets, SECURITY.md
    metrics["security"] = 100  # Start at max, deduct for issues
    
    if (repo_path / ".env").exists():
        metrics["security"] -= 30
    
    # Simple pattern matching for hardcoded secrets
    secret_patterns = [r'secret\s*=\s*["\']', r'password\s*=\s*["\']', 
                       r'token\s*=\s*["\']', r'api_key\s*=\s*["\']']
    
    code_files = list(repo_path.rglob("*.py")) + list(repo_path.rglob("*.js")) + list(repo_path.rglob("*.ts"))
    secret_count = 0
    for file_path in code_files[:100]:  # Limit scan to first 100 files
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for pattern in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    secret_count += 1
                    break
        except Exception:
            continue
    
    metrics["security"] -= min(secret_count * 20, 60)
    
    if (repo_path / "SECURITY.md").exists():
        metrics["security"] += 20
    
    metrics["security"] = max(0, min(100, metrics["security"]))
    
    # Performance: Dockerfile + cache config + dependency count
    if (repo_path / "Dockerfile").exists():
        metrics["performance"] += 20
    
    # Check for cache configs
    cache_files = [".dockerignore", ".npmrc", ".yarnrc", "pyproject.toml"]
    if any((repo_path / cf).exists() for cf in cache_files):
        metrics["performance"] += 15
    
    # Check dependency count
    if (repo_path / "requirements.txt").exists():
        try:
            lines = (repo_path / "requirements.txt").read_text().strip().split("\n")
            non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]
            if len(non_empty) < 20:
                metrics["performance"] += 20
            else:
                metrics["performance"] += 10
        except Exception:
            metrics["performance"] += 10
    
    # Baseline
    metrics["performance"] += 45
    
    return metrics


@router.post("", response_model=EvalResponse)
def evaluate_repo_url(request: EvalRequest):
    """Clone GitHub repo, extract metrics, and return score.
    
    Args:
        request: Contains repo_url (GitHub URL)
        
    Returns:
        Score result with metrics breakdown
    """
    repo_url = request.repo_url
    
    # Validate GitHub URL
    if "github.com" not in repo_url.lower():
        raise HTTPException(status_code=400, detail="Only GitHub URLs are supported")
    
    tmpdir = None
    try:
        # Create temporary directory
        tmpdir = tempfile.mkdtemp(prefix="eval_")
        tmpdir_path = Path(tmpdir)
        
        # Clone repository
        try:
            result = subprocess.run(
                ["git", "clone", "--depth=1", repo_url, tmpdir],
                timeout=30,
                capture_output=True,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=408, detail="Repository clone timed out")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else "Clone failed"
            raise HTTPException(status_code=400, detail=f"Failed to clone repository: {error_msg}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="git command not found")
        
        # Extract metrics
        metrics = extract_metrics(tmpdir_path)
        
        # Score with engine
        score_result = score_skill(metrics)
        
        # Build response
        return EvalResponse(
            repo_url=repo_url,
            metrics=metrics,
            score_total=score_result["total"],
            grade=score_result["grade"],
            breakdown=score_result["breakdown"],
            scanned_at=datetime.utcnow().isoformat() + "Z",
        )
        
    finally:
        # Cleanup
        if tmpdir and os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
