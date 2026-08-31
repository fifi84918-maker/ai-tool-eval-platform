"""Ingest Pipeline Orchestrator for L5 (V1A L5).

Orchestrates L1 → L3 → L4 pipeline: discover → fetch → scan → score.
"""

from api.adapters.github import GitHubAdapter, FakeGitHubFetcher
from api.scanners.static_scan import static_scan_skill
from api.scorer.benchmark import score_skill
from api.store import get_skill


def run_pipeline(query: str, limit: int = 5, fetcher=None) -> dict:
    """Run complete ingestion pipeline.
    
    Pipeline stages:
    1. L1 discover: query → SourceRecord + DISCOVERED skills
    2. L1 fetch: DISCOVERED → ACQUIRED (with skill_md)
    3. L3 scan: ACQUIRED → STATIC_REVIEWED or QUARANTINED
    4. L4 score: STATIC_REVIEWED → RUNNABLE (skip QUARANTINED)
    
    Args:
        query: Search query
        limit: Maximum skills to process
        fetcher: Optional custom fetcher (defaults to FakeGitHubFetcher)
        
    Returns:
        Pipeline report dict with counts and results
    """
    adapter = GitHubAdapter(fetcher=fetcher or FakeGitHubFetcher())
    
    report = {
        "query": query,
        "discovered": 0,
        "acquired": 0,
        "reviewed": 0,
        "quarantined": 0,
        "runnable": 0,
        "errors": [],
        "skills": [],
    }
    
    # Stage 1: Discover (L1)
    try:
        sources = adapter.discover(query, limit=limit)
        report["discovered"] = len(sources)
    except Exception as e:
        report["errors"].append({"stage": "discover", "error": str(e)})
        return report
    
    # Process each source through pipeline
    for source in sources:
        skill_id = None
        
        try:
            # Stage 2: Fetch (L1)
            skill, artifacts = adapter.fetch(source)
            skill_id = skill.skill_id
            report["acquired"] += 1
            
            # Stage 3: Scan (L3)
            scan_result = static_scan_skill(skill_id)
            
            if scan_result["decision"] == "QUARANTINED":
                # Quarantined skills skip scoring
                report["quarantined"] += 1
                
                # Add to skills list (without score)
                skill = get_skill(skill_id)
                report["skills"].append({
                    "skill_id": skill_id,
                    "name": skill.name,
                    "benchmark_score": None,
                    "state": "QUARANTINED",
                })
            else:
                # STATIC_REVIEWED
                report["reviewed"] += 1
                
                # Stage 4: Score (L4)
                score_result = score_skill(skill_id)
                report["runnable"] += 1
                
                # Add to skills list (with score)
                skill = get_skill(skill_id)
                report["skills"].append({
                    "skill_id": skill_id,
                    "name": skill.name,
                    "benchmark_score": skill.benchmark_score,
                    "state": "RUNNABLE",
                })
        
        except Exception as e:
            # Error isolation: one failure doesn't stop the pipeline
            report["errors"].append({
                "source": source.platform_skill_id,
                "skill_id": skill_id,
                "error": str(e),
            })
    
    return report
