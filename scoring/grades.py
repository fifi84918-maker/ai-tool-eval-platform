"""Grade thresholds and constants for skill scoring."""

from enum import Enum


class Grade(str, Enum):
    """Skill grade levels."""
    A = "A"  # Excellent: >= 90
    B = "B"  # Good: >= 75
    C = "C"  # Acceptable: >= 60
    D = "D"  # Poor: >= 40
    U = "U"  # Unacceptable: < 40


# Grade thresholds (inclusive lower bounds)
GRADE_THRESHOLDS = {
    Grade.A: 90.0,
    Grade.B: 75.0,
    Grade.C: 60.0,
    Grade.D: 40.0,
    Grade.U: 0.0,
}


def get_grade(score: float) -> Grade:
    """Map numeric score to grade.
    
    Args:
        score: Numeric score (0-100)
        
    Returns:
        Grade enum value
    """
    if score >= GRADE_THRESHOLDS[Grade.A]:
        return Grade.A
    elif score >= GRADE_THRESHOLDS[Grade.B]:
        return Grade.B
    elif score >= GRADE_THRESHOLDS[Grade.C]:
        return Grade.C
    elif score >= GRADE_THRESHOLDS[Grade.D]:
        return Grade.D
    else:
        return Grade.U
