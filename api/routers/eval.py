"""Evaluation API endpoints - clone repo and score."""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from analyzer.static_scan import scan_repository
from scoring import score_skill


router = APIRouter()


class EvalRequest(BaseModel):
    repo_url: str


class BatchEvalRequest(BaseModel):
    repo_urls: List[str]


class EvalResponse(BaseModel):
    repo_url: str
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
def evaluate_repo_url(request: EvalRequest):
    """Clone GitHub repo, scan, and return score.
    
    Args:
        request: Contains repo_url (GitHub URL)
        
    Returns:
        Score result with metrics breakdown, findings, and metadata
    """
    result = _clone_and_scan(request.repo_url)
    
    # Check if error occurred
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
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
