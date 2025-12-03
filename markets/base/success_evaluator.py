"""
Map Pro Market Success Evaluator
================================

Evaluates success of market operations and determines quality metrics.
Helps assess whether search results are complete and of sufficient quality.

Architecture: Evaluation component without market-specific thresholds.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timezone

from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


class SuccessLevel(str):
    """Success level constants."""
    EXCELLENT = "excellent"      # >90% success
    GOOD = "good"               # 70-90% success
    ACCEPTABLE = "acceptable"   # 50-70% success
    POOR = "poor"              # <50% success
    FAILED = "failed"          # Complete failure


class SuccessEvaluator:
    """
    Evaluates success and quality of market operations.
    
    Responsibilities:
    - Evaluate company search success
    - Evaluate filing discovery success
    - Calculate quality metrics
    - Determine if results are acceptable
    
    Does NOT handle:
    - Market-specific thresholds (markets define their own)
    - Error handling (error_classifier handles this)
    - Retry logic (recovery_manager handles this)
    """
    
    def __init__(self):
        """Initialize success evaluator."""
        # Default thresholds (markets can override)
        self.default_thresholds = {
            'excellent': 0.90,
            'good': 0.70,
            'acceptable': 0.50
        }
        
        logger.debug("Success evaluator initialized")
    
    def evaluate_company_search(
        self, 
        search_result: Optional[Dict[str, Any]],
        expected_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate company search result quality.
        
        Args:
            search_result: Company information returned from search
            expected_fields: Optional list of fields that should be present
            
        Returns:
            Evaluation dictionary with metrics and success level
        """
        if not search_result:
            return {
                'success': False,
                'success_level': SuccessLevel.FAILED,
                'completeness_score': 0.0,
                'missing_fields': expected_fields or [],
                'evaluation_timestamp': datetime.now(timezone.utc)
            }
        
        # Define critical fields that must be present
        critical_fields = ['market_entity_id', 'name']
        
        # Define optional but desirable fields
        desirable_fields = ['ticker', 'identifiers', 'jurisdiction', 'status']
        
        # Use provided expected fields or default to critical + desirable
        if expected_fields is None:
            expected_fields = critical_fields + desirable_fields
        
        # Check which fields are present
        present_fields = [field for field in expected_fields if field in search_result and search_result[field]]
        missing_fields = [field for field in expected_fields if field not in present_fields]
        
        # Calculate completeness score
        if expected_fields:
            completeness_score = len(present_fields) / len(expected_fields)
        else:
            completeness_score = 1.0
        
        # Check critical fields
        critical_missing = [field for field in critical_fields if field in missing_fields]
        
        if critical_missing:
            success_level = SuccessLevel.FAILED
            success = False
        else:
            success = True
            success_level = self._determine_success_level(completeness_score)
        
        return {
            'success': success,
            'success_level': success_level,
            'completeness_score': completeness_score,
            'present_fields': present_fields,
            'missing_fields': missing_fields,
            'critical_missing': critical_missing,
            'data_quality': self._assess_data_quality(search_result),
            'evaluation_timestamp': datetime.now(timezone.utc)
        }
    
    def evaluate_filing_discovery(
        self,
        filings_found: List[Dict[str, Any]],
        search_criteria: Optional[Dict[str, Any]] = None,
        expected_minimum: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate filing discovery result quality.
        
        Args:
            filings_found: List of filing information dictionaries
            search_criteria: Original search criteria
            expected_minimum: Optional minimum expected number of filings
            
        Returns:
            Evaluation dictionary with metrics and success level
        """
        filings_count = len(filings_found) if filings_found else 0
        
        # Basic success check
        if filings_count == 0:
            return {
                'success': False,
                'success_level': SuccessLevel.FAILED,
                'filings_count': 0,
                'completeness_score': 0.0,
                'quality_score': 0.0,
                'issues': ['No filings found'],
                'evaluation_timestamp': datetime.now(timezone.utc)
            }
        
        # Evaluate filing data quality
        quality_scores = []
        incomplete_filings = 0
        
        for filing in filings_found:
            quality = self._evaluate_filing_quality(filing)
            quality_scores.append(quality['quality_score'])
            
            if not quality['is_complete']:
                incomplete_filings += 1
        
        # Calculate average quality score
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Calculate completeness based on expected minimum
        if expected_minimum:
            completeness_score = min(filings_count / expected_minimum, 1.0)
        else:
            completeness_score = 1.0  # No expectation set
        
        # Overall success score (weighted average)
        overall_score = (completeness_score * 0.4) + (avg_quality_score * 0.6)
        
        success_level = self._determine_success_level(overall_score)
        
        # Identify issues
        issues = []
        if expected_minimum and filings_count < expected_minimum:
            issues.append(f"Found {filings_count} filings, expected at least {expected_minimum}")
        
        if incomplete_filings > 0:
            issues.append(f"{incomplete_filings} filings have incomplete data")
        
        if avg_quality_score < 0.7:
            issues.append(f"Average data quality below threshold: {avg_quality_score:.2f}")
        
        return {
            'success': True,
            'success_level': success_level,
            'filings_count': filings_count,
            'completeness_score': completeness_score,
            'quality_score': avg_quality_score,
            'overall_score': overall_score,
            'incomplete_filings': incomplete_filings,
            'issues': issues,
            'evaluation_timestamp': datetime.now(timezone.utc)
        }
    
    def _evaluate_filing_quality(self, filing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate quality of a single filing record.
        
        Args:
            filing: Filing information dictionary
            
        Returns:
            Quality assessment dictionary
        """
        required_fields = ['market_filing_id', 'filing_type', 'filing_date']
        desirable_fields = ['url', 'title', 'period_end', 'format']
        
        all_fields = required_fields + desirable_fields
        
        present_fields = [field for field in all_fields if field in filing and filing[field]]
        
        quality_score = len(present_fields) / len(all_fields)
        
        is_complete = all(field in filing and filing[field] for field in required_fields)
        
        return {
            'quality_score': quality_score,
            'is_complete': is_complete,
            'present_fields': present_fields,
            'missing_fields': [f for f in all_fields if f not in present_fields]
        }
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> str:
        """
        Assess overall data quality.
        
        Args:
            data: Data dictionary to assess
            
        Returns:
            Quality assessment: 'high', 'medium', 'low'
        """
        if not data:
            return 'low'
        
        # Count non-empty fields
        non_empty = sum(1 for v in data.values() if v is not None and v != '')
        total = len(data)
        
        if total == 0:
            return 'low'
        
        ratio = non_empty / total
        
        if ratio >= 0.8:
            return 'high'
        elif ratio >= 0.5:
            return 'medium'
        else:
            return 'low'
    
    def _determine_success_level(self, score: float) -> str:
        """
        Determine success level from score.
        
        Args:
            score: Score between 0.0 and 1.0
            
        Returns:
            Success level string
        """
        if score >= self.default_thresholds['excellent']:
            return SuccessLevel.EXCELLENT
        elif score >= self.default_thresholds['good']:
            return SuccessLevel.GOOD
        elif score >= self.default_thresholds['acceptable']:
            return SuccessLevel.ACCEPTABLE
        else:
            return SuccessLevel.POOR
    
    def is_acceptable_result(self, evaluation: Dict[str, Any]) -> bool:
        """
        Determine if result is acceptable for use.
        
        Args:
            evaluation: Evaluation dictionary from evaluate_* methods
            
        Returns:
            True if result is acceptable, False otherwise
        """
        if not evaluation.get('success', False):
            return False
        
        success_level = evaluation.get('success_level', SuccessLevel.FAILED)
        
        acceptable_levels = {
            SuccessLevel.EXCELLENT,
            SuccessLevel.GOOD,
            SuccessLevel.ACCEPTABLE
        }
        
        return success_level in acceptable_levels
    
    def generate_quality_report(
        self,
        company_evaluation: Optional[Dict[str, Any]] = None,
        filing_evaluation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive quality report.
        
        Args:
            company_evaluation: Optional company search evaluation
            filing_evaluation: Optional filing discovery evaluation
            
        Returns:
            Comprehensive quality report
        """
        report = {
            'report_timestamp': datetime.now(timezone.utc),
            'overall_success': True
        }
        
        if company_evaluation:
            report['company_search'] = {
                'success': company_evaluation.get('success', False),
                'success_level': company_evaluation.get('success_level'),
                'completeness': company_evaluation.get('completeness_score', 0.0),
                'quality': company_evaluation.get('data_quality', 'unknown')
            }
            
            if not company_evaluation.get('success', False):
                report['overall_success'] = False
        
        if filing_evaluation:
            report['filing_discovery'] = {
                'success': filing_evaluation.get('success', False),
                'success_level': filing_evaluation.get('success_level'),
                'count': filing_evaluation.get('filings_count', 0),
                'quality': filing_evaluation.get('quality_score', 0.0),
                'issues': filing_evaluation.get('issues', [])
            }
            
            if not filing_evaluation.get('success', False):
                report['overall_success'] = False
        
        return report


# Global success evaluator instance
success_evaluator = SuccessEvaluator()


# Convenience functions
def evaluate_company_search(
    search_result: Optional[Dict[str, Any]],
    expected_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Evaluate company search result quality."""
    return success_evaluator.evaluate_company_search(search_result, expected_fields)


def evaluate_filing_discovery(
    filings_found: List[Dict[str, Any]],
    search_criteria: Optional[Dict[str, Any]] = None,
    expected_minimum: Optional[int] = None
) -> Dict[str, Any]:
    """Evaluate filing discovery result quality."""
    return success_evaluator.evaluate_filing_discovery(filings_found, search_criteria, expected_minimum)


def is_acceptable_result(evaluation: Dict[str, Any]) -> bool:
    """Determine if result is acceptable for use."""
    return success_evaluator.is_acceptable_result(evaluation)