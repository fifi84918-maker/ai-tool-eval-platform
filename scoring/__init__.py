"""Scoring engine for AI Skill evaluation.

Computes weighted scores across multiple dimensions and assigns grades.
"""

from scoring.engine import score_skill
from scoring.grades import GRADE_THRESHOLDS, Grade

__all__ = ["score_skill", "GRADE_THRESHOLDS", "Grade"]
