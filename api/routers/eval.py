"""Evaluation API endpoints - clone repo and score."""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from analyzer.static_scan import scan_repository
from scoring import score_skill
from db import SessionLocal
from db.models import Evaluation


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter()


def _skill_id_from_url(repo_url: str) -> str:
    """Generate skill_id from repository URL.
    
    Rules:
    - github.com/owner/repo → "github-owner-repo"
    - Other URLs → domain-path slugified
    
    Args:
        repo_url: Repository URL
        
    Returns:
        Generated skill_id string
        
    Examples:
        >>> _skill_id_from_url("https://github.com/acme/doc-skill")
        'github-acme-doc-skill'
        >>> _skill_id_from_url("https://gitlab.com/acme/project")
        'gitlab-acme-project'
    """
    url = repo_url.lower().strip().rstrip('/')
    
    # Remove protocol
    if url.startswith('https://'):
        url = url[8:]
    elif url.startswith('http://'):
        url = url[7:]
    
    # Parse domain and path
    parts = url.split('/')
    if len(parts) < 2:
        # Just domain, no path
        return parts[0].replace('.', '-')
    
    domain = parts[0].split('.')[0]  # github.com → github
    path_parts = parts[1:]
    
    # Join domain and path with hyphens
    return '-'.join([domain] + path_parts)


class EvalRequest(BaseModel):
    repo_url: str


class BatchEvalRequest(BaseModel):
    repo_urls: List[str]


class EvalResponse(BaseModel):
    repo_url: str
    skill_id: str  # Generated from repo_url for linking to skill detail page
    metrics: dict
    score_total: float
    grade: str
    breakdown: dict
    scanned_at: str
    findings: Optional[List[dict]] = None
    meta: Optional[dict] = None


class BatchEvalResponse(BaseModel):
    results: List[dict]  # Each is either EvalResponse dict or {"repo_url": ..., "error": ...}


def _clone_and_scan(repo_url: str) -> dict:
    """Clone repository and scan it. Returns result dict or error dict.
    
    Args:
        repo_url: GitHub repository URL
        
    Returns:
        Dictionary with evaluation results or error information
    """
    tmpdir = None
    try:
        # Validate GitHub URL
        if "github.com" not in repo_url.lower():
            return {"repo_url": repo_url, "error": "Only GitHub URLs are supported"}
        
        # Create temporary directory
        tmpdir = tempfile.mkdtemp(prefix="eval_")
        tmpdir_path = Path(tmpdir)
        
        # Clone repository
        try:
            subprocess.run(
                ["git", "clone", "--depth=1", repo_url, tmpdir],
                timeout=30,
                capture_output=True,
                check=True,
            )
        except subprocess.TimeoutExpired:
            return {"repo_url": repo_url, "error": "Repository clone timed out"}
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else "Clone failed"
            return {"repo_url": repo_url, "error": f"Failed to clone: {error_msg[:100]}"}
        except FileNotFoundError:
            return {"repo_url": repo_url, "error": "git command not found"}
        
        # Scan repository
        scan_result = scan_repository(tmpdir)
        
        # Score with engine
        score_result = score_skill(scan_result["metrics"])
        
        # Build response
        return {
            "repo_url": repo_url,
            "skill_id": _skill_id_from_url(repo_url),
            "metrics": scan_result["metrics"],
            "score_total": score_result["total"],
            "grade": score_result["grade"],
            "breakdown": score_result["breakdown"],
            "scanned_at": datetime.utcnow().isoformat() + "Z",
            "findings": scan_result["findings"],
            "meta": scan_result["meta"],
        }
        
    except Exception as e:
        return {"repo_url": repo_url, "error": str(e)}
        
    finally:
        # Cleanup
        if tmpdir and os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)


@router.post("", response_model=EvalResponse)
def evaluate_repo_url(request: EvalRequest, db: Session = Depends(get_db)):
    """Clone GitHub repo, scan, and return score.
    
    Args:
        request: Contains repo_url (GitHub URL)
        db: Database session
        
    Returns:
        Score result with metrics breakdown, findings, and metadata
    """
    result = _clone_and_scan(request.repo_url)
    
    # Check if error occurred
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Save to database
    evaluation = Evaluation(
        repo_url=result["repo_url"],
        score_total=result["score_total"],
        grade=result["grade"],
        metrics=result["metrics"],
        findings=result.get("findings", []),
        meta=result.get("meta", {}),
        scanned_at=datetime.fromisoformat(result["scanned_at"].replace("Z", "+00:00"))
    )
    db.add(evaluation)
    db.commit()
    
    return result


@router.post("/batch", response_model=BatchEvalResponse)
async def evaluate_batch(request: BatchEvalRequest):
    """Evaluate multiple repositories in parallel.
    
    Args:
        request: Contains repo_urls (list of GitHub URLs, max 10)
        
    Returns:
        List of evaluation results (successful and failed)
    """
    if len(request.repo_urls) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 repositories per batch")
    
    if not request.repo_urls:
        raise HTTPException(status_code=400, detail="At least one repository URL required")
    
    # Process in parallel with thread pool
    with ThreadPoolExecutor(max_workers=3) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, _clone_and_scan, url)
            for url in request.repo_urls
        ]
        results = await asyncio.gather(*futures)
    
    return BatchEvalResponse(results=results)


@router.get("/report")
async def get_evaluation_report(
    repo_url: str = Query(..., description="GitHub repository URL"),
    format: str = Query("json", description="Output format: json or markdown")
):
    """Generate evaluation report for a repository.
    
    Args:
        repo_url: GitHub repository URL
        format: Output format (json or markdown)
        
    Returns:
        Evaluation report in requested format
    """
    if format not in ["json", "markdown"]:
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'markdown'")
    
    # Execute scan
    result = _clone_and_scan(repo_url)
    
    # Check if error occurred
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Return JSON format
    if format == "json":
        return result
    
    # Generate markdown report
    md_lines = [
        f"# Evaluation Report: {repo_url}",
        "",
        f"**Scanned at:** {result['scanned_at']}",
        "",
        "## Overall Score",
        "",
        f"- **Grade:** {result['grade']}",
        f"- **Total Score:** {result['score_total']:.1f}/100",
        "",
        "## Dimension Breakdown",
        "",
        "| Dimension | Score | Weighted Contribution |",
        "|-----------|-------|----------------------|",
    ]
    
    for dim, score in result["breakdown"].items():
        dim_name = dim.capitalize()
        md_lines.append(f"| {dim_name} | {result['metrics'][dim]:.1f} | {score:.1f} |")
    
    md_lines.extend([
        "",
        "## Repository Metadata",
        "",
        f"- **Total Files:** {result['meta']['file_count']}",
        f"- **Primary Language:** {result['meta']['language'] or 'Unknown'}",
        f"- **Has README:** {'Yes' if result['meta']['has_readme'] else 'No'}",
        f"- **Has Tests:** {'Yes' if result['meta']['has_tests'] else 'No'}",
        f"- **Has CI:** {'Yes' if result['meta']['has_ci'] else 'No'}",
        f"- **Has Dockerfile:** {'Yes' if result['meta']['has_dockerfile'] else 'No'}",
        f"- **Has License:** {'Yes' if result['meta']['has_license'] else 'No'}",
        f"- **Has Security Policy:** {'Yes' if result['meta']['has_security_md'] else 'No'}",
        "",
    ])
    
    # Add findings if any
    if result["findings"]:
        md_lines.extend([
            "## Security Findings",
            "",
        ])
        
        for finding in result["findings"]:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(finding["severity"], "ℹ️")
            
            md_lines.append(f"- {severity_emoji} **{finding['severity'].upper()}**: {finding['message']}")
        
        md_lines.append("")
    else:
        md_lines.extend([
            "## Security Findings",
            "",
            "✅ No security issues detected.",
            "",
        ])
    
    md_lines.append("---")
    md_lines.append(f"*Generated by AI Skill Eval Platform*")
    
    markdown_content = "\n".join(md_lines)
    
    return PlainTextResponse(content=markdown_content, media_type="text/markdown")


@router.post("/upload", response_model=EvalResponse)
async def evaluate_zip_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Evaluate uploaded ZIP file.
    
    Args:
        file: Uploaded ZIP file (max 50MB)
        db: Database session
        
    Returns:
        Score result with metrics breakdown, findings, and metadata
    """
    # Validate file type
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    tmpdir = None
    zip_path = None
    
    try:
        # Create temporary directory
        tmpdir = tempfile.mkdtemp(prefix="upload_")
        tmpdir_path = Path(tmpdir)
        
        # Save uploaded file
        zip_path = tmpdir_path / "upload.zip"
        content = await file.read()
        
        # Check file size (50MB limit)
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
        
        zip_path.write_bytes(content)
        
        # Extract ZIP
        extract_dir = tmpdir_path / "extracted"
        extract_dir.mkdir()
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Check number of files (prevent zip bomb)
                file_list = zip_ref.namelist()
                if len(file_list) > 500:
                    raise HTTPException(status_code=400, detail="ZIP contains too many files (max 500)")
                
                # Extract
                zip_ref.extractall(extract_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract ZIP: {str(e)}")
        
        # Scan extracted content
        scan_result = scan_repository(str(extract_dir))
        
        # Score with engine
        score_result = score_skill(scan_result["metrics"])
        
        # Build result
        repo_url = f"uploaded:{file.filename}"
        result = EvalResponse(
            repo_url=repo_url,
            skill_id=_skill_id_from_url(repo_url),  # Generate skill_id for uploaded files too
            metrics=scan_result["metrics"],
            score_total=score_result["total"],
            grade=score_result["grade"],
            breakdown=score_result["breakdown"],
            scanned_at=datetime.utcnow().isoformat() + "Z",
            findings=scan_result["findings"],
            meta=scan_result["meta"],
        )
        
        # Save to database
        evaluation = Evaluation(
            repo_url=result.repo_url,
            score_total=result.score_total,
            grade=result.grade,
            metrics=result.metrics,
            findings=result.findings,
            meta=result.meta,
            scanned_at=datetime.fromisoformat(result.scanned_at.replace("Z", "+00:00"))
        )
        db.add(evaluation)
        db.commit()
        
        return result
        
    finally:
        # Cleanup
        if tmpdir and os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)


@router.get("/history")
def get_evaluation_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get evaluation history with pagination.
    
    Args:
        limit: Maximum number of results (1-100)
        offset: Offset for pagination
        db: Database session
        
    Returns:
        Paginated list of evaluations
    """
    # Query total count
    total = db.query(Evaluation).count()
    
    # Query evaluations ordered by scanned_at descending
    evaluations = db.query(Evaluation).order_by(
        Evaluation.scanned_at.desc()
    ).limit(limit).offset(offset).all()
    
    # Build response
    results = []
    for eval in evaluations:
        results.append({
            "id": eval.id,
            "repo_url": eval.repo_url,
            "score_total": eval.score_total,
            "grade": eval.grade,
            "scanned_at": eval.scanned_at.isoformat() + "Z"
        })
    
    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/compare")
def compare_evaluations(
    ids: str = Query(..., description="Comma-separated evaluation IDs (max 3)"),
    db: Session = Depends(get_db)
):
    """Compare multiple evaluations side by side.
    
    Args:
        ids: Comma-separated evaluation IDs (e.g., "1,2,3")
        db: Database session
        
    Returns:
        List of full evaluation records
    """
    # Parse IDs
    try:
        id_list = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Limit to 3
    if len(id_list) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 evaluations can be compared")
    
    # Query evaluations
    evaluations = db.query(Evaluation).filter(Evaluation.id.in_(id_list)).all()
    
    # Build response
    results = []
    for eval in evaluations:
        results.append({
            "id": eval.id,
            "repo_url": eval.repo_url,
            "score_total": eval.score_total,
            "grade": eval.grade,
            "metrics": eval.metrics,
            "findings": eval.findings or [],
            "meta": eval.meta or {},
            "scanned_at": eval.scanned_at.isoformat() + "Z"
        })
    
    return {"results": results}
