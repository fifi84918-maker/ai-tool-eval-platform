"""Core scoring engine logic.

Computes weighted scores across multiple dimensions.
"""

from typing import Dict, Optional

from scoring.grades import get_grade


def score_skill(
    metrics: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> Dict:
    """Compute weighted score for a skill.
    
    Args:
        metrics: Dictionary of dimension scores (0-100 per dimension)
        weights: Optional custom weights per dimension (default: equal weights)
                Must sum to 1.0 if provided
                
    Returns:
        Dictionary with:
            - total: Weighted total score (0-100)
            - grade: Grade string (A/B/C/D/U)
            - breakdown: Per-dimension weighted contributions
            
    Examples:
        >>> score_skill({"accuracy": 90, "speed": 80})
        {"total": 85.0, "grade": "B", "breakdown": {"accuracy": 45.0, "speed": 40.0}}
        
        >>> score_skill({"accuracy": 95}, {"accuracy": 1.0})
        {"total": 95.0, "grade": "A", "breakdown": {"accuracy": 95.0}}
    """
    # Handle empty metrics
    if not metrics:
        return {
            "total": 0.0,
            "grade": "U",
            "breakdown": {},
        }
    
    # Default weights: equal distribution
    if weights is None:
        weight_value = 1.0 / len(metrics)
        weights = {dim: weight_value for dim in metrics.keys()}
    
    # Validate weights sum to 1.0 (with floating point tolerance)
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")
    
    # Compute weighted contributions
    breakdown = {}
    total = 0.0
    
    for dimension, value in metrics.items():
        # Handle missing weight (default to 0)
        weight = weights.get(dimension, 0.0)
        contribution = value * weight
        breakdown[dimension] = contribution
        total += contribution
    
    # Ensure total is within bounds [0, 100]
    total = max(0.0, min(100.0, total))
    
    # Map to grade
    grade = get_grade(total)
    
    return {
        "total": total,
        "grade": grade.value,
        "breakdown": breakdown,
    }
