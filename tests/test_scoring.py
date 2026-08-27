"""Tests for scoring engine."""

import pytest

from scoring import score_skill, GRADE_THRESHOLDS, Grade
from scoring.grades import get_grade


class TestGradeMapping:
    """Test grade threshold mapping."""
    
    def test_perfect_score_gives_a(self):
        """Perfect score (100) maps to grade A."""
        result = score_skill({"test": 100.0}, {"test": 1.0})
        assert result["total"] == 100.0
        assert result["grade"] == "A"
    
    def test_boundary_90_gives_a(self):
        """Score of exactly 90 maps to grade A."""
        result = score_skill({"test": 90.0}, {"test": 1.0})
        assert result["total"] == 90.0
        assert result["grade"] == "A"
    
    def test_boundary_75_gives_b(self):
        """Score of exactly 75 maps to grade B."""
        result = score_skill({"test": 75.0}, {"test": 1.0})
        assert result["total"] == 75.0
        assert result["grade"] == "B"
    
    def test_boundary_60_gives_c(self):
        """Score of exactly 60 maps to grade C."""
        result = score_skill({"test": 60.0}, {"test": 1.0})
        assert result["total"] == 60.0
        assert result["grade"] == "C"
    
    def test_boundary_40_gives_d(self):
        """Score of exactly 40 maps to grade D."""
        result = score_skill({"test": 40.0}, {"test": 1.0})
        assert result["total"] == 40.0
        assert result["grade"] == "D"
    
    def test_zero_score_gives_u(self):
        """Score of 0 maps to grade U."""
        result = score_skill({"test": 0.0}, {"test": 1.0})
        assert result["total"] == 0.0
        assert result["grade"] == "U"
    
    def test_below_40_gives_u(self):
        """Score below 40 maps to grade U."""
        result = score_skill({"test": 39.9}, {"test": 1.0})
        assert result["total"] == 39.9
        assert result["grade"] == "U"


class TestScoringEngine:
    """Test scoring engine logic."""
    
    def test_empty_metrics_returns_u(self):
        """Empty metrics dictionary returns 0 score and U grade."""
        result = score_skill({})
        assert result["total"] == 0.0
        assert result["grade"] == "U"
        assert result["breakdown"] == {}
    
    def test_single_dimension_full_weight(self):
        """Single dimension with full weight returns its value."""
        result = score_skill({"accuracy": 85.0}, {"accuracy": 1.0})
        assert result["total"] == 85.0
        assert result["grade"] == "B"
        assert result["breakdown"]["accuracy"] == 85.0
    
    def test_equal_weights_default(self):
        """Default weights are equal across dimensions."""
        result = score_skill({"acc": 80.0, "speed": 60.0})
        # Equal weights: 0.5 each
        # Total: 80*0.5 + 60*0.5 = 70
        assert result["total"] == 70.0
        assert result["grade"] == "C"
        assert result["breakdown"]["acc"] == 40.0
        assert result["breakdown"]["speed"] == 30.0
    
    def test_custom_weights(self):
        """Custom weights override defaults."""
        metrics = {"accuracy": 90.0, "speed": 60.0}
        weights = {"accuracy": 0.7, "speed": 0.3}
        result = score_skill(metrics, weights)
        # Total: 90*0.7 + 60*0.3 = 63 + 18 = 81
        assert abs(result["total"] - 81.0) < 1e-6
        assert result["grade"] == "B"
        assert abs(result["breakdown"]["accuracy"] - 63.0) < 1e-6
        assert abs(result["breakdown"]["speed"] - 18.0) < 1e-6
    
    def test_weights_must_sum_to_one(self):
        """Weights that don't sum to 1.0 raise ValueError."""
        metrics = {"a": 50.0, "b": 50.0}
        weights = {"a": 0.4, "b": 0.4}  # Sum = 0.8
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            score_skill(metrics, weights)
    
    def test_missing_metric_in_weights(self):
        """Metric not in weights gets 0 contribution."""
        metrics = {"a": 100.0, "b": 100.0}
        weights = {"a": 1.0}  # b missing
        result = score_skill(metrics, weights)
        # Only 'a' contributes: 100*1.0 = 100
        assert result["total"] == 100.0
        assert result["breakdown"]["a"] == 100.0
        assert result["breakdown"]["b"] == 0.0
    
    def test_breakdown_structure(self):
        """Breakdown contains all dimensions with contributions."""
        metrics = {"acc": 90.0, "rel": 80.0, "sec": 70.0}
        result = score_skill(metrics)
        
        assert "breakdown" in result
        assert set(result["breakdown"].keys()) == {"acc", "rel", "sec"}
        
        # With equal weights (1/3 each)
        expected_total = (90 + 80 + 70) / 3
        assert abs(result["total"] - expected_total) < 1e-6
    
    def test_floating_point_precision(self):
        """Handles floating point arithmetic correctly."""
        metrics = {"a": 33.333, "b": 33.333, "c": 33.334}
        result = score_skill(metrics)
        
        # Equal weights: (33.333 + 33.333 + 33.334) / 3 = 33.333...
        assert 33.0 < result["total"] < 34.0
        assert result["grade"] == "U"
    
    def test_all_zeros_gives_u(self):
        """All zero metrics gives U grade."""
        metrics = {"a": 0.0, "b": 0.0, "c": 0.0}
        result = score_skill(metrics)
        assert result["total"] == 0.0
        assert result["grade"] == "U"


class TestGetGrade:
    """Test get_grade helper function."""
    
    def test_get_grade_boundaries(self):
        """Test all grade boundaries."""
        assert get_grade(100.0) == Grade.A
        assert get_grade(90.0) == Grade.A
        assert get_grade(89.9) == Grade.B
        assert get_grade(75.0) == Grade.B
        assert get_grade(74.9) == Grade.C
        assert get_grade(60.0) == Grade.C
        assert get_grade(59.9) == Grade.D
        assert get_grade(40.0) == Grade.D
        assert get_grade(39.9) == Grade.U
        assert get_grade(0.0) == Grade.U
