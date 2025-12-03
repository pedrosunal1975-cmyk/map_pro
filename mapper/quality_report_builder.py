# File: map_pro/engines/mapper/quality_report_builder.py

"""
Quality Report Builder
======================

Builds comprehensive quality reports from validation results.
Extracted from complex report generation logic.
"""

from typing import Dict, Any, List

from .quality_score_calculator import QualityScoreCalculator
from .null_validation_constants import (
    MSG_CRITICAL_NULLS,
    MSG_SUSPICIOUS_NULLS,
    MSG_LOW_COVERAGE,
    MSG_NIL_IN_SOURCE,
    MSG_EXPLAINED_NULLS,
    SUSPICIOUS_NULL_WARNING_THRESHOLD,
    LOW_EXPLANATION_COVERAGE_THRESHOLD,
    GRADE_UNKNOWN
)


class QualityReportBuilder:
    """
    Builds comprehensive quality reports for null value validation.
    
    Responsibility: Report assembly and formatting logic.
    """
    
    def __init__(self):
        """Initialize quality report builder."""
        self.score_calculator = QualityScoreCalculator()
    
    def build_quality_report(
        self,
        parsed_validation: Dict[str, Any],
        mapped_validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build comprehensive null quality report.
        
        Args:
            parsed_validation: Parsed facts validation results
            mapped_validation: Mapped statements validation results
            
        Returns:
            Comprehensive quality report dictionary
        """
        # Extract summary data
        parsed_summary = parsed_validation.get('summary', {})
        
        # Create base report structure
        report = self._create_base_report(parsed_summary, mapped_validation)
        
        # Calculate quality score and grade
        score = self._calculate_score(parsed_summary)
        report['overall_quality_score'] = score
        report['data_quality_grade'] = self.score_calculator.determine_grade(score)
        
        # Add issues, warnings, and info
        self._add_critical_issues(report, parsed_summary)
        self._add_warnings(report, parsed_summary)
        self._add_info_messages(report, parsed_summary)
        
        # Set action required flag
        report['action_required'] = bool(report['critical_issues'])
        
        return report
    
    # ========================================================================
    # REPORT SECTION GENERATORS
    # ========================================================================
    
    def _create_base_report(
        self,
        parsed_summary: Dict[str, Any],
        mapped_validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create base report structure."""
        return {
            'overall_quality_score': 0.0,
            'parsed_facts_analysis': parsed_summary,
            'mapped_statements_analysis': {
                'statements_analyzed': mapped_validation.get('statements_analyzed', 0),
                'statements_with_nulls': len(mapped_validation.get('statements_with_nulls', []))
            },
            'data_quality_grade': GRADE_UNKNOWN,
            'action_required': False,
            'critical_issues': [],
            'warnings': [],
            'info': []
        }
    
    def _calculate_score(self, parsed_summary: Dict[str, Any]) -> float:
        """Calculate quality score from parsed summary."""
        suspicious_count = parsed_summary.get('suspicious_nulls', 0)
        critical_count = parsed_summary.get('critical_nulls', 0)
        explanation_coverage = parsed_summary.get('explanation_coverage', 0.0)
        
        return self.score_calculator.calculate_quality_score(
            suspicious_count,
            critical_count,
            explanation_coverage
        )
    
    def _add_critical_issues(
        self,
        report: Dict[str, Any],
        parsed_summary: Dict[str, Any]
    ) -> None:
        """Add critical issues to report."""
        critical_count = parsed_summary.get('critical_nulls', 0)
        
        if critical_count > 0:
            report['critical_issues'].append(
                MSG_CRITICAL_NULLS.format(count=critical_count)
            )
    
    def _add_warnings(
        self,
        report: Dict[str, Any],
        parsed_summary: Dict[str, Any]
    ) -> None:
        """Add warnings to report."""
        suspicious_count = parsed_summary.get('suspicious_nulls', 0)
        explanation_coverage = parsed_summary.get('explanation_coverage', 0.0)
        
        # Warning for suspicious nulls
        if suspicious_count > SUSPICIOUS_NULL_WARNING_THRESHOLD:
            report['warnings'].append(
                MSG_SUSPICIOUS_NULLS.format(count=suspicious_count)
            )
        
        # Warning for low explanation coverage
        if explanation_coverage < LOW_EXPLANATION_COVERAGE_THRESHOLD:
            report['warnings'].append(
                MSG_LOW_COVERAGE.format(coverage=explanation_coverage)
            )
    
    def _add_info_messages(
        self,
        report: Dict[str, Any],
        parsed_summary: Dict[str, Any]
    ) -> None:
        """Add informational messages to report."""
        nil_count = parsed_summary.get('nil_in_source', 0)
        explained_count = parsed_summary.get('explained_nulls', 0)
        
        # Info about nil values
        if nil_count > 0:
            report['info'].append(
                MSG_NIL_IN_SOURCE.format(count=nil_count)
            )
        
        # Info about explained nulls
        if explained_count > 0:
            report['info'].append(
                MSG_EXPLAINED_NULLS.format(count=explained_count)
            )


class RecommendationGenerator:
    """
    Generates recommendations based on validation results.
    
    Responsibility: Recommendation generation logic.
    """
    
    def __init__(self):
        """Initialize recommendation generator."""
        pass
    
    def generate_recommendations(
        self,
        validation_report: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations based on validation results.
        
        Args:
            validation_report: Statement validation report
            
        Returns:
            List of recommendation strings
        """
        statements_with_nulls = validation_report.get('statements_with_nulls', [])
        
        if not statements_with_nulls:
            from .null_validation_constants import MSG_SUCCESS_NO_NULLS
            return [MSG_SUCCESS_NO_NULLS]
        
        recommendations = []
        
        # Add recommendations for high null percentages
        recommendations.extend(
            self._generate_high_null_recommendations(statements_with_nulls)
        )
        
        # Add recommendations for missing source facts
        recommendations.extend(
            self._generate_missing_source_recommendations(statements_with_nulls)
        )
        
        return recommendations
    
    # ========================================================================
    # RECOMMENDATION GENERATORS
    # ========================================================================
    
    def _generate_high_null_recommendations(
        self,
        statements_with_nulls: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for high null percentages."""
        from .null_validation_constants import (
            HIGH_NULL_PERCENTAGE_THRESHOLD,
            MSG_WARNING_HIGH_NULL_PCT
        )
        
        recommendations = []
        
        for stmt in statements_with_nulls:
            if stmt['null_percentage'] > HIGH_NULL_PERCENTAGE_THRESHOLD:
                recommendations.append(
                    MSG_WARNING_HIGH_NULL_PCT.format(
                        statement_type=stmt['statement_type'],
                        null_pct=stmt['null_percentage']
                    )
                )
        
        return recommendations
    
    def _generate_missing_source_recommendations(
        self,
        statements_with_nulls: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for missing source facts."""
        from .null_validation_constants import MSG_ACTION_MISSING_SOURCES
        
        recommendations = []
        
        for stmt in statements_with_nulls:
            missing_sources = self._count_missing_sources(stmt['null_items'])
            
            if missing_sources > 0:
                recommendations.append(
                    MSG_ACTION_MISSING_SOURCES.format(
                        count=missing_sources,
                        statement_type=stmt['statement_type']
                    )
                )
        
        return recommendations
    
    def _count_missing_sources(self, null_items: List[Dict[str, Any]]) -> int:
        """Count null items without source facts."""
        return sum(1 for item in null_items if not item.get('has_source_fact', False))