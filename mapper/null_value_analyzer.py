# File: map_pro/engines/mapper/null_value_analyzer.py

"""
Null Value Analyzer
===================

Analyzes null values in parsed facts and mapped statements.
Handles the core analysis logic separated from validation orchestration.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict

from .null_validation_constants import (
    SUSPICION_NONE,
    SUSPICION_LOW,
    SUSPICION_MEDIUM,
    SUSPICION_HIGH,
    CLASSIFICATION_NIL_IN_SOURCE,
    CLASSIFICATION_EXPLAINED_NULL,
    CLASSIFICATION_UNEXPLAINED_NULL
)


class NullValueAnalyzer:
    """
    Analyzes individual facts and statements for null values.
    
    Responsibility: Core analysis logic for null value detection and classification.
    """
    
    def __init__(self, concept_checker, explanation_finder):
        """
        Initialize analyzer with helper components.
        
        Args:
            concept_checker: Component to check if concepts are critical
            explanation_finder: Component to find explanations for nulls
        """
        self.concept_checker = concept_checker
        self.explanation_finder = explanation_finder
        self.stats = {
            'total_nulls': 0,
            'legitimate_nulls': 0,
            'explained_nulls': 0,
            'suspicious_nulls': 0,
            'critical_nulls': 0
        }
    
    def analyze_fact(
        self,
        fact: Dict[str, Any],
        explanatory_texts: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single fact for null value.
        
        Args:
            fact: Fact dictionary to analyze
            explanatory_texts: Available explanatory text blocks
            
        Returns:
            Null information dictionary if fact has null value, None otherwise
        """
        value = fact.get('fact_value')
        
        # Check if value is null/empty
        if not self._is_null_value(value):
            return None
        
        is_nil = fact.get('is_nil', False)
        concept = fact.get('concept', 'unknown')
        
        null_info = self._create_base_null_info(fact, concept, is_nil)
        
        # Classify the null value
        if is_nil:
            null_info = self._classify_as_nil(null_info)
        else:
            null_info = self._classify_as_null(null_info, fact, concept, explanatory_texts)
        
        self.stats['total_nulls'] += 1
        
        return null_info
    
    def analyze_statement_nulls(
        self,
        statement: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze null values in a mapped statement.
        
        Args:
            statement: Statement dictionary to analyze
            
        Returns:
            Analysis results if statement has nulls, None otherwise
        """
        statement_type = statement.get('statement_type', 'unknown')
        line_items = statement.get('line_items', [])
        
        null_items = self._find_null_line_items(line_items)
        
        if not null_items:
            return None
        
        return {
            'statement_type': statement_type,
            'statement_name': statement.get('statement_name'),
            'null_count': len(null_items),
            'total_items': len(line_items),
            'null_percentage': self._calculate_null_percentage(null_items, line_items),
            'null_items': null_items
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get current analysis statistics."""
        return self.stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset analysis statistics."""
        for key in self.stats:
            self.stats[key] = 0
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _is_null_value(self, value: Any) -> bool:
        """Check if value is considered null."""
        return value is None or value == '' or value == 'None'
    
    def _create_base_null_info(
        self,
        fact: Dict[str, Any],
        concept: str,
        is_nil: bool
    ) -> Dict[str, Any]:
        """Create base null information dictionary."""
        return {
            'concept': concept,
            'concept_qname': fact.get('concept_qname', concept),
            'context_id': fact.get('context_id'),
            'unit_id': fact.get('unit_id'),
            'is_nil_in_source': is_nil,
            'decimals': fact.get('decimals'),
            'has_explanation': False,
            'explanation_source': None,
            'is_critical': self.concept_checker.is_critical(concept),
            'suspicion_level': SUSPICION_LOW
        }
    
    def _classify_as_nil(self, null_info: Dict[str, Any]) -> Dict[str, Any]:
        """Classify null as nil in source."""
        null_info['classification'] = CLASSIFICATION_NIL_IN_SOURCE
        null_info['suspicion_level'] = SUSPICION_NONE
        self.stats['legitimate_nulls'] += 1
        return null_info
    
    def _classify_as_null(
        self,
        null_info: Dict[str, Any],
        fact: Dict[str, Any],
        concept: str,
        explanatory_texts: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Classify null value based on explanation availability."""
        explanation = self.explanation_finder.find_explanation(
            concept,
            fact,
            explanatory_texts
        )
        
        if explanation:
            null_info = self._classify_as_explained(null_info, explanation)
        else:
            null_info = self._classify_as_unexplained(null_info)
        
        return null_info
    
    def _classify_as_explained(
        self,
        null_info: Dict[str, Any],
        explanation: str
    ) -> Dict[str, Any]:
        """Classify null as explained."""
        null_info['has_explanation'] = True
        null_info['explanation_source'] = explanation
        null_info['classification'] = CLASSIFICATION_EXPLAINED_NULL
        null_info['suspicion_level'] = SUSPICION_LOW
        self.stats['explained_nulls'] += 1
        return null_info
    
    def _classify_as_unexplained(self, null_info: Dict[str, Any]) -> Dict[str, Any]:
        """Classify null as unexplained."""
        null_info['classification'] = CLASSIFICATION_UNEXPLAINED_NULL
        
        if null_info['is_critical']:
            null_info['suspicion_level'] = SUSPICION_HIGH
            self.stats['critical_nulls'] += 1
        else:
            null_info['suspicion_level'] = SUSPICION_MEDIUM
        
        self.stats['suspicious_nulls'] += 1
        return null_info
    
    def _find_null_line_items(self, line_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find all null line items in statement."""
        null_items = []
        
        for item in line_items:
            if self._is_null_value(item.get('value')):
                null_items.append({
                    'label': item.get('label'),
                    'concept': item.get('concept'),
                    'has_source_fact': bool(item.get('source_fact_id'))
                })
        
        return null_items
    
    def _calculate_null_percentage(
        self,
        null_items: List[Dict[str, Any]],
        line_items: List[Dict[str, Any]]
    ) -> float:
        """Calculate percentage of null items."""
        if not line_items:
            return 0.0
        return round(len(null_items) / len(line_items) * 100, 2)