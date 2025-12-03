# File: map_pro/engines/mapper/summary_generator.py

"""
Summary Generator
=================

Generates summary statistics for validation results.
Handles calculation of percentages and aggregation logic.
"""

from typing import Dict, Any, List


class SummaryGenerator:
    """
    Generates summary statistics for validation results.
    
    Responsibility: Summary calculation and aggregation logic.
    """
    
    def __init__(self):
        """Initialize summary generator."""
        pass
    
    def generate_parsed_summary(
        self,
        total_facts: int,
        null_facts: List[Dict[str, Any]],
        nil_facts: List[Dict[str, Any]],
        explained_nulls: List[Dict[str, Any]],
        suspicious_nulls: List[Dict[str, Any]],
        critical_nulls_count: int
    ) -> Dict[str, Any]:
        """
        Generate summary for parsed facts validation.
        
        Args:
            total_facts: Total number of facts analyzed
            null_facts: List of null fact info dictionaries
            nil_facts: List of nil fact info dictionaries
            explained_nulls: List of explained null info dictionaries
            suspicious_nulls: List of suspicious null info dictionaries
            critical_nulls_count: Count of critical null values
            
        Returns:
            Summary dictionary with statistics
        """
        total_nulls = len(null_facts) + len(nil_facts)
        
        return {
            'total_facts': total_facts,
            'total_nulls': total_nulls,
            'nil_in_source': len(nil_facts),
            'explained_nulls': len(explained_nulls),
            'suspicious_nulls': len(suspicious_nulls),
            'critical_nulls': critical_nulls_count,
            'null_percentage': self._calculate_percentage(total_nulls, total_facts),
            'explanation_coverage': self._calculate_explanation_coverage(
                explained_nulls,
                null_facts
            )
        }
    
    def generate_mapped_summary(
        self,
        statements_analyzed: int,
        statements_with_nulls: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate summary for mapped statements validation.
        
        Args:
            statements_analyzed: Number of statements analyzed
            statements_with_nulls: List of statements containing nulls
            
        Returns:
            Summary dictionary
        """
        return {
            'statements_analyzed': statements_analyzed,
            'statements_with_nulls': len(statements_with_nulls)
        }
    
    # ========================================================================
    # CALCULATION METHODS
    # ========================================================================
    
    def _calculate_percentage(self, part: int, total: int) -> float:
        """
        Calculate percentage.
        
        Args:
            part: Numerator
            total: Denominator
            
        Returns:
            Percentage rounded to 2 decimal places
        """
        if total == 0:
            return 0.0
        return round(part / total * 100, 2)
    
    def _calculate_explanation_coverage(
        self,
        explained_nulls: List[Dict[str, Any]],
        null_facts: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate explanation coverage percentage.
        
        Args:
            explained_nulls: List of explained nulls
            null_facts: List of all null facts
            
        Returns:
            Coverage percentage
        """
        if not null_facts:
            return 100.0
        return round(len(explained_nulls) / len(null_facts) * 100, 2)