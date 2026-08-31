"""Benchmark Scorer for L4 (V1A L4).

Scores STATIC_REVIEWED skills using heuristic rules, fills benchmark_score,
and transitions to RUNNABLE.
"""

import json
from api.store import get_skill, list_artifacts, transition_state, put_skill, list_skills


def score_skill(skill_id: str) -> dict:
    """Score a skill and transition to RUNNABLE.
    
    Args:
        skill_id: Skill ID to score
        
    Returns:
        Score result dict
        
    Raises:
        ValueError: If skill not found or not in STATIC_REVIEWED state
    """
    # 1. Get skill
    skill = get_skill(skill_id)
    if skill is None:
        raise ValueError(f"Skill {skill_id} not found")
    if skill.state != "STATIC_REVIEWED":
        raise ValueError(f"Skill {skill_id} state={skill.state}, expected STATIC_REVIEWED")
    
    # 2. Calculate score (heuristic)
    score = 70.0  # Base score
    
    components = {
        "base": 70.0,
        "platform_bonus": 0.0,
        "license_bonus": 0.0,
        "description_bonus": 0.0,
        "domain_bonus": 0.0,
        "finding_penalty": 0.0,
    }
    
    # Platform bonus (github +10)
    if skill.platform == "github":
        score += 10.0
        components["platform_bonus"] = 10.0
    
    # License bonus (known license +10)
    if skill.license and skill.license != "UNKNOWN":
        score += 10.0
        components["license_bonus"] = 10.0
    
    # Description bonus (length > 50 chars +5)
    if skill.description and len(skill.description) > 50:
        score += 5.0
        components["description_bonus"] = 5.0
    
    # Domain coverage bonus (non-empty target_domains +5)
    if skill.target_domains:
        score += 5.0
        components["domain_bonus"] = 5.0
    
    # Finding penalty (read scan_report if exists)
    scan_artifacts = [a for a in list_artifacts(skill_id) if a.kind == "scan_report"]
    if scan_artifacts:
        report = json.loads(scan_artifacts[0].path_or_text)
        finding_count = report.get("finding_count", 0)
        penalty = finding_count * 2.0
        score -= penalty
        components["finding_penalty"] = -penalty
    
    # 3. Clamp to [0, 100]
    score = max(0.0, min(100.0, score))
    score = round(score, 2)
    
    # 4. Write benchmark_score
    skill.benchmark_score = score
    put_skill(skill)
    
    # 5. Transition to RUNNABLE
    transition_state(skill_id, "RUNNABLE", reason=f"Benchmark scored: {score:.1f}")
    
    # 6. Refresh skill
    skill = get_skill(skill_id)
    
    return {
        "skill_id": skill_id,
        "benchmark_score": skill.benchmark_score,
        "components": components,
        "decision": "RUNNABLE",
    }


def score_all_reviewed() -> list[dict]:
    """Score all STATIC_REVIEWED skills.
    
    Returns:
        List of score results
    """
    results = []
    for skill in list_skills(filter_by_state="STATIC_REVIEWED"):
        try:
            result = score_skill(skill.skill_id)
            results.append(result)
        except Exception as e:
            # Log error but continue
            results.append({
                "skill_id": skill.skill_id,
                "error": str(e),
            })
    return results
