"""
Map Pro Success Calculator
==========================

Calculates success metrics and determines processing success.

Architecture: Universal success calculation - consistent criteria across all markets.
"""

from typing import Dict, Any, List

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


# Success thresholds
EXCELLENT_THRESHOLD = 0.95  # 95%
ACCEPTABLE_THRESHOLD = 0.90  # 90%

# Confidence thresholds
LOW_CONFIDENCE_THRESHOLD = 0.7

# Quality thresholds
LOW_QUALITY_THRESHOLD = 0.7

# Analysis limits
MAX_UNMAPPED_CONCEPTS_DISPLAY = 20
COMPLEX_CONCEPT_LENGTH_THRESHOLD = 40

# Recommendation prefixes
PREFIX_SUCCESS = "[SUCCESS]"
PREFIX_WARNING = "[WARNING]"
PREFIX_ERROR = "[ERROR]"
PREFIX_ACTION = "[ACTION]"
PREFIX_INFO = "[INFO]"

# Success levels
SUCCESS_LEVEL_EXCELLENT = 'EXCELLENT'
SUCCESS_LEVEL_ACCEPTABLE = 'ACCEPTABLE'
SUCCESS_LEVEL_FAILURE = 'FAILURE'

# Gap pattern types
PATTERN_MISSING_PREFIX = 'missing_prefix'
PATTERN_COMPLEX_EXTENSIONS = 'complex_extensions'
PATTERN_UNKNOWN_TERMS = 'unknown_business_terms'
PATTERN_NONE = 'none'


class SuccessCalculationError(Exception):
    """Raised when success calculation fails."""
    pass


class SuccessCalculator:
    """
    Calculates success metrics for mapping operations.
    
    Responsibilities:
    - Calculate mapping success rate
    - Determine if processing succeeded
    - Generate gap analysis
    - Create performance reports
    - Provide recommendations
    
    Success Criteria:
    - >=95%: SUCCESS (Excellent mapping)
    - 90-95%: WARNING (Acceptable but needs review)
    - <90%: FAILURE (Poor mapping quality)
    """
    
    def __init__(self):
        """Initialize success calculator."""
        self.logger = logger
        self.logger.info("Success calculator initialized")

    def calculate_success(
        self,
        resolved_facts: List[Dict[str, Any]],
        quality_report: Dict[str, Any],
        duplicate_report: Dict[str, Any] = None  # NEW PARAMETER
    ) -> Dict[str, Any]:
        """
        Calculate success metrics.
        
        UPDATED: Now includes duplicate analysis in success metrics.
        
        Args:
            resolved_facts: List of resolved facts (including metadata)
            quality_report: Quality assessment results
            duplicate_report: Duplicate detection results (optional)
            
        Returns:
            Success metrics dictionary with duplicate information
            
        Raises:
            SuccessCalculationError: If calculation fails
        """
        try:
            # Filter out metadata facts before counting
            mappable_facts = [
                f for f in resolved_facts 
                if not f.get('is_metadata', False)
            ]
            
            # Count only mappable facts
            total_facts = len(mappable_facts)
            mapped_facts = sum(1 for f in mappable_facts if not f.get('is_unmapped', False))
            unmapped_facts = total_facts - mapped_facts
            
            # Count metadata facts for reporting
            metadata_facts_count = len(resolved_facts) - len(mappable_facts)
            
            # Calculate success rate (only from mappable facts)
            success_rate = (mapped_facts / total_facts * 100) if total_facts > 0 else 0.0
            success_ratio = mapped_facts / total_facts if total_facts > 0 else 0.0
            
            # Determine success level
            success_level = self._determine_success_level(success_ratio)
            
            # Generate gap analysis
            gap_analysis = self._generate_gap_analysis(mappable_facts, quality_report)
            
            # Generate recommendations (NOW INCLUDES DUPLICATE INFO)
            recommendations = self._generate_recommendations(
                success_ratio,
                quality_report,
                gap_analysis,
                duplicate_report  # NEW: Pass duplicate info
            )
            
            success_metrics = {
                'total_facts': total_facts,
                'mapped_facts': mapped_facts,
                'unmapped_facts': unmapped_facts,
                'metadata_facts_excluded': metadata_facts_count,
                'total_facts_in_filing': len(resolved_facts),
                'success_rate': round(success_rate, 2),
                'success_ratio': round(success_ratio, 4),
                'success_level': success_level,
                'is_success': success_level in [SUCCESS_LEVEL_EXCELLENT, SUCCESS_LEVEL_ACCEPTABLE],
                'quality_score': quality_report.get('quality_score', 0.0),
                'gap_analysis': gap_analysis,
                'duplicate_analysis': duplicate_report or {},  # NEW: Include duplicate report
                'recommendations': recommendations
            }
            
            self.logger.info(
                f"Success calculation: {mapped_facts}/{total_facts} mappable facts "
                f"({success_rate:.1f}%) - {success_level}"
            )
            
            # NEW: Log duplicate info if present
            if duplicate_report and duplicate_report.get('has_critical_duplicates'):
                self.logger.warning(
                    f"[!] CRITICAL DUPLICATES DETECTED: "
                    f"{duplicate_report['severity_counts']['CRITICAL']} critical issue(s)"
                )
            
            return success_metrics
            
        except (KeyError, ValueError, TypeError) as e:
            self.logger.error(f"Success calculation failed: {e}", exc_info=True)
            raise SuccessCalculationError(f"Failed to calculate success metrics: {e}")
            
    def _determine_success_level(self, success_ratio: float) -> str:
        """
        Determine success level based on success ratio.
        
        Args:
            success_ratio: Ratio of mapped facts (0.0 to 1.0)
            
        Returns:
            Success level: EXCELLENT, ACCEPTABLE, or FAILURE
        """
        if success_ratio >= EXCELLENT_THRESHOLD:
            return SUCCESS_LEVEL_EXCELLENT
        elif success_ratio >= ACCEPTABLE_THRESHOLD:
            return SUCCESS_LEVEL_ACCEPTABLE
        else:
            return SUCCESS_LEVEL_FAILURE

    def _generate_gap_analysis(
        self,
        resolved_facts: List[Dict[str, Any]],
        quality_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate gap analysis identifying what's missing.
        
        Args:
            resolved_facts: List of resolved facts
            quality_report: Quality assessment results
            
        Returns:
            Gap analysis dictionary
        """
        unmapped_facts = [f for f in resolved_facts if f.get('is_unmapped', False)]
        
        # Analyze unmapped concepts
        unmapped_concepts = [f.get('concept', 'unknown') for f in unmapped_facts]
        
        # Identify patterns in unmapped concepts
        patterns = self._identify_unmapped_patterns(unmapped_concepts)
        
        # Calculate gap metrics
        total_unmapped = len(unmapped_concepts)
        gap_percentage = (total_unmapped / len(resolved_facts) * 100) if resolved_facts else 0.0
        
        gap_analysis = {
            'total_gaps': total_unmapped,
            'gap_percentage': round(gap_percentage, 2),
            'unmapped_concepts': unmapped_concepts[:MAX_UNMAPPED_CONCEPTS_DISPLAY],
            'patterns': {
                'missing_prefix_count': len(patterns[PATTERN_MISSING_PREFIX]),
                'complex_extensions_count': len(patterns[PATTERN_COMPLEX_EXTENSIONS]),
                'unknown_business_terms_count': len(patterns[PATTERN_UNKNOWN_TERMS])
            },
            'most_common_issue': self._identify_most_common_issue(patterns)
        }
        
        return gap_analysis
    
    def _identify_unmapped_patterns(self, unmapped_concepts: List[str]) -> Dict[str, List[str]]:
        """
        Identify patterns in unmapped concepts.
        
        Args:
            unmapped_concepts: List of unmapped concept names
            
        Returns:
            Dictionary mapping pattern types to concept lists
        """
        patterns = {
            PATTERN_MISSING_PREFIX: [],
            PATTERN_COMPLEX_EXTENSIONS: [],
            PATTERN_UNKNOWN_TERMS: []
        }
        
        for concept in unmapped_concepts:
            if ':' not in concept:
                patterns[PATTERN_MISSING_PREFIX].append(concept)
            elif len(concept) > COMPLEX_CONCEPT_LENGTH_THRESHOLD:
                patterns[PATTERN_COMPLEX_EXTENSIONS].append(concept)
            else:
                patterns[PATTERN_UNKNOWN_TERMS].append(concept)
        
        return patterns
    
    def _identify_most_common_issue(self, patterns: Dict[str, List[str]]) -> str:
        """
        Identify the most common issue in unmapped concepts.
        
        Args:
            patterns: Dictionary of pattern types to concept lists
            
        Returns:
            Most common pattern type
        """
        max_count = 0
        most_common = PATTERN_NONE
        
        for pattern_type, concepts in patterns.items():
            if len(concepts) > max_count:
                max_count = len(concepts)
                most_common = pattern_type
        
        return most_common

    def _generate_recommendations(
        self,
        success_ratio: float,
        quality_report: Dict[str, Any],
        gap_analysis: Dict[str, Any],
        duplicate_report: Dict[str, Any] = None
    ) -> List[str]:
        """
        Generate recommendations based on results.
        
        UPDATED: Now includes duplicate-based recommendations.
        
        Args:
            success_ratio: Success ratio (0.0 to 1.0)
            quality_report: Quality assessment results
            gap_analysis: Gap analysis results
            duplicate_report: Duplicate detection results (optional)
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Add duplicate recommendations FIRST (most critical)
        if duplicate_report:
            self._add_duplicate_recommendations(duplicate_report, recommendations)
        
        # Add success level recommendations
        self._add_success_level_recommendations(success_ratio, recommendations)
        
        # Add confidence recommendations
        self._add_confidence_recommendations(quality_report, recommendations)
        
        # Add gap analysis recommendations
        self._add_gap_recommendations(gap_analysis, recommendations)
        
        # Add completeness recommendations
        self._add_completeness_recommendations(quality_report, recommendations)
        
        # Add quality score recommendations
        self._add_quality_recommendations(quality_report, recommendations)
        
        return recommendations


    def _add_duplicate_recommendations(
        self,
        duplicate_report: Dict[str, Any],
        recommendations: List[str]
    ) -> None:
        """
        Add recommendations based on duplicate detection.
        
        Args:
            duplicate_report: Duplicate detection results
            recommendations: List to append recommendations to
        """
        if not duplicate_report:
            return
        
        severity_counts = duplicate_report.get('severity_counts', {})
        critical = severity_counts.get('CRITICAL', 0)
        major = severity_counts.get('MAJOR', 0)
        
        if critical > 0:
            recommendations.insert(0, 
                f"{PREFIX_ERROR} CRITICAL DATA INTEGRITY ISSUE: {critical} duplicate(s) "
                f"with material variance (>5%). Filing may contain erroneous or fraudulent data. "
                "RECOMMEND EXCLUSION from financial analysis."
            )
        elif major > 0:
            recommendations.insert(0,
                f"{PREFIX_WARNING} {major} major duplicate(s) with significant variance (1-5%). "
                "Manual review strongly recommended before using this data for analysis."
            )
        elif severity_counts.get('MINOR', 0) > 0:
            recommendations.append(
                f"{PREFIX_INFO} Minor duplicate variances detected - likely formatting/rounding. "
                "No action required."
            )
    
    def _add_success_level_recommendations(
        self,
        success_ratio: float,
        recommendations: List[str]
    ) -> None:
        """
        Add recommendations based on success level.
        
        Args:
            success_ratio: Success ratio (0.0 to 1.0)
            recommendations: List to append recommendations to
        """
        if success_ratio >= EXCELLENT_THRESHOLD:
            recommendations.append(
                f"{PREFIX_SUCCESS} Excellent mapping quality achieved (>=95%)"
            )
        elif success_ratio >= ACCEPTABLE_THRESHOLD:
            recommendations.append(
                f"{PREFIX_WARNING} Acceptable mapping quality (90-95%) - review unmapped concepts"
            )
        else:
            recommendations.append(
                f"{PREFIX_ERROR} Poor mapping quality (<90%) - investigation required"
            )
    
    def _add_confidence_recommendations(
        self,
        quality_report: Dict[str, Any],
        recommendations: List[str]
    ) -> None:
        """
        Add recommendations based on confidence levels.
        
        Args:
            quality_report: Quality assessment results
            recommendations: List to append recommendations to
        """
        avg_confidence = quality_report.get('average_confidence', 0.0)
        if avg_confidence < LOW_CONFIDENCE_THRESHOLD:
            recommendations.append(
                f"{PREFIX_WARNING} Low average confidence - consider reviewing mapping strategies"
            )
    
    def _add_gap_recommendations(
        self,
        gap_analysis: Dict[str, Any],
        recommendations: List[str]
    ) -> None:
        """
        Add recommendations based on gap analysis.
        
        Args:
            gap_analysis: Gap analysis results
            recommendations: List to append recommendations to
        """
        most_common_issue = gap_analysis.get('most_common_issue')
        
        if most_common_issue == PATTERN_MISSING_PREFIX:
            recommendations.append(
                f"{PREFIX_ACTION} Many concepts missing namespace prefix - enhance prefix detection"
            )
        elif most_common_issue == PATTERN_COMPLEX_EXTENSIONS:
            recommendations.append(
                f"{PREFIX_ACTION} Complex company extensions found - improve extension parsing"
            )
        elif most_common_issue == PATTERN_UNKNOWN_TERMS:
            recommendations.append(
                f"{PREFIX_ACTION} Unknown business terms - expand financial concept mappings"
            )
    
    def _add_completeness_recommendations(
        self,
        quality_report: Dict[str, Any],
        recommendations: List[str]
    ) -> None:
        """
        Add recommendations based on statement completeness.
        
        Args:
            quality_report: Quality assessment results
            recommendations: List to append recommendations to
        """
        completeness = quality_report.get('completeness', {})
        
        if not completeness.get('has_income_statement'):
            recommendations.append(f"{PREFIX_INFO} No Income Statement facts found")
        
        if not completeness.get('has_balance_sheet'):
            recommendations.append(f"{PREFIX_INFO} No Balance Sheet facts found")
        
        if not completeness.get('has_cash_flow'):
            recommendations.append(f"{PREFIX_INFO} No Cash Flow Statement facts found")
    
    def _add_quality_recommendations(
        self,
        quality_report: Dict[str, Any],
        recommendations: List[str]
    ) -> None:
        """
        Add recommendations based on overall quality score.
        
        Args:
            quality_report: Quality assessment results
            recommendations: List to append recommendations to
        """
        quality_score = quality_report.get('quality_score', 0.0)
        if quality_score < LOW_QUALITY_THRESHOLD:
            recommendations.append(
                f"{PREFIX_WARNING} Low quality score - multiple issues detected"
            )

    def generate_performance_report(
        self,
        success_metrics: Dict[str, Any],
        processing_time: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        UPDATED: Now includes metadata fact information.
        
        Args:
            success_metrics: Success metrics from calculate_success
            processing_time: Time taken to process (seconds)
            
        Returns:
            Performance report dictionary
        """
        try:
            facts_per_second = 0.0
            if processing_time > 0:
                facts_per_second = success_metrics['total_facts'] / processing_time
            
            report = {
                'summary': {
                    'success_level': success_metrics['success_level'],
                    'success_rate': success_metrics['success_rate'],
                    'total_facts': success_metrics['total_facts'],
                    'mapped_facts': success_metrics['mapped_facts'],
                    'unmapped_facts': success_metrics['unmapped_facts'],
                    'metadata_facts_excluded': success_metrics.get('metadata_facts_excluded', 0),  # NEW
                    'total_facts_in_filing': success_metrics.get('total_facts_in_filing', 0),  # NEW
                    'quality_score': success_metrics['quality_score']
                },
                'performance': {
                    'processing_time_seconds': round(processing_time, 2),
                    'facts_per_second': round(facts_per_second, 2)
                },
                'gaps': success_metrics['gap_analysis'],
                'recommendations': success_metrics['recommendations']
            }
            
            return report
            
        except (KeyError, ValueError, TypeError, ZeroDivisionError) as e:
            self.logger.error(f"Performance report generation failed: {e}", exc_info=True)
            return {
                'summary': {},
                'performance': {},
                'gaps': {},
                'recommendations': [f"{PREFIX_ERROR} Failed to generate report: {e}"]
            }


__all__ = ['SuccessCalculator']