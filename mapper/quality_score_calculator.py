# File: map_pro/engines/mapper/quality_score_calculator.py

"""
Quality Score Calculator
=========================

Calculates quality scores and grades for null value validation.
Extracted from complex quality report generation logic.
"""

from typing import Dict, Any

from .null_validation_constants import (
    SCORE_EXCELLENT_THRESHOLD,
    SCORE_GOOD_THRESHOLD,
    SCORE_ACCEPTABLE_THRESHOLD,
    SCORE_POOR_THRESHOLD,
    PENALTY_SUSPICIOUS_NULL,
    PENALTY_CRITICAL_NULL,
    BONUS_HIGH_EXPLANATION_COVERAGE,
    HIGH_EXPLANATION_THRESHOLD,
    GRADE_EXCELLENT,
    GRADE_GOOD,
    GRADE_ACCEPTABLE,
    GRADE_POOR,
    GRADE_CRITICAL
)


class QualityScoreCalculator:
    """
    Calculates quality scores and determines quality grades.
    
    Responsibility: Score calculation and grade determination logic.
    """
    
    def __init__(self):
        """Initialize quality score calculator."""
        self.base_score = 100.0
    
    def calculate_quality_score(
        self,
        suspicious_count: int,
        critical_count: int,
        explanation_coverage: float
    ) -> float:
        """
        Calculate overall quality score (0-100).
        
        Args:
            suspicious_count: Number of suspicious null values
            critical_count: Number of critical null values
            explanation_coverage: Percentage of nulls with explanations
            
        Returns:
            Quality score between 0.0 and 100.0
        """
        score = self.base_score
        
        # Apply penalties
        score -= self._calculate_penalty(suspicious_count, critical_count)
        
        # Apply bonuses
        score += self._calculate_bonus(explanation_coverage)
        
        # Ensure score stays within bounds
        return self._normalize_score(score)
    
    def determine_grade(self, score: float) -> str:
        """
        Determine quality grade based on score.
        
        Args:
            score: Quality score (0-100)
            
        Returns:
            Quality grade string
        """
        if score >= SCORE_EXCELLENT_THRESHOLD:
            return GRADE_EXCELLENT
        elif score >= SCORE_GOOD_THRESHOLD:
            return GRADE_GOOD
        elif score >= SCORE_ACCEPTABLE_THRESHOLD:
            return GRADE_ACCEPTABLE
        elif score >= SCORE_POOR_THRESHOLD:
            return GRADE_POOR
        else:
            return GRADE_CRITICAL
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _calculate_penalty(self, suspicious_count: int, critical_count: int) -> float:
        """Calculate total penalty from null counts."""
        suspicious_penalty = suspicious_count * PENALTY_SUSPICIOUS_NULL
        critical_penalty = critical_count * PENALTY_CRITICAL_NULL
        return suspicious_penalty + critical_penalty
    
    def _calculate_bonus(self, explanation_coverage: float) -> float:
        """Calculate bonus for high explanation coverage."""
        if explanation_coverage > HIGH_EXPLANATION_THRESHOLD:
            return BONUS_HIGH_EXPLANATION_COVERAGE
        return 0.0
    
    def _normalize_score(self, score: float) -> float:
        """Normalize score to be between 0.0 and 100.0."""
        return max(0.0, min(100.0, score))