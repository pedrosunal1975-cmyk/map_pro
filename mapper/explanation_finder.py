# File: map_pro/engines/mapper/explanation_finder.py

"""
Explanation Finder
==================

Finds explanations for null values in parsed facts.
Handles text extraction and pattern matching logic.
"""

import re
from typing import Dict, Any, List, Optional

from .null_validation_constants import (
    EXPLANATION_PATTERNS,
    MIN_EXPLANATORY_TEXT_LENGTH,
    MAX_EXPLANATION_TEXT_LENGTH,
    EXPLANATORY_CONCEPT_KEYWORDS,
    GENERAL_EXPLANATION_KEYWORDS,
    EXPLANATION_TEXT_CONCEPT,
    EXPLANATION_CONTEXT_RELATED,
    EXPLANATION_DOCUMENT_LEVEL
)


class ExplanationFinder:
    """
    Finds explanations for null values.
    
    Responsibility: Text extraction and explanation matching logic.
    """
    
    def __init__(self):
        """Initialize explanation finder."""
        self.explanation_regex = re.compile(
            '|'.join(EXPLANATION_PATTERNS),
            re.IGNORECASE
        )
    
    def extract_explanatory_texts(
        self,
        facts: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Extract text blocks that might explain null values.
        
        Args:
            facts: List of fact dictionaries
            
        Returns:
            List of explanatory text dictionaries
        """
        explanatory_texts = []
        
        for fact in facts:
            explanation = self._extract_from_fact(fact)
            if explanation:
                explanatory_texts.append(explanation)
        
        return explanatory_texts
    
    def find_explanation(
        self,
        concept: str,
        fact: Dict[str, Any],
        explanatory_texts: List[Dict[str, str]]
    ) -> Optional[str]:
        """
        Find explanation for a null value.
        
        Args:
            concept: Concept name
            fact: Fact dictionary
            explanatory_texts: Available explanatory texts
            
        Returns:
            Explanation string if found, None otherwise
        """
        # Check if concept itself is explanatory
        explanation = self._check_concept_explanation(concept)
        if explanation:
            return explanation
        
        # Check context-related explanations
        explanation = self._check_context_explanation(fact, explanatory_texts)
        if explanation:
            return explanation
        
        # Check general explanations
        explanation = self._check_general_explanation(explanatory_texts)
        if explanation:
            return explanation
        
        return None
    
    # ========================================================================
    # EXTRACTION METHODS
    # ========================================================================
    
    def _extract_from_fact(self, fact: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract explanatory text from a single fact."""
        value = fact.get('fact_value', '')
        
        if not self._is_explanatory_text(value):
            return None
        
        if not self.explanation_regex.search(value):
            return None
        
        return {
            'concept': fact.get('concept', ''),
            'text': value[:MAX_EXPLANATION_TEXT_LENGTH],
            'full_text': value,
            'context_id': fact.get('context_id')
        }
    
    def _is_explanatory_text(self, value: Any) -> bool:
        """Check if value is a text that might be explanatory."""
        return (
            isinstance(value, str) and 
            len(value) > MIN_EXPLANATORY_TEXT_LENGTH
        )
    
    # ========================================================================
    # EXPLANATION CHECKING METHODS
    # ========================================================================
    
    def _check_concept_explanation(self, concept: str) -> Optional[str]:
        """Check if concept itself contains explanation keywords."""
        concept_lower = concept.lower()
        
        for keyword in EXPLANATORY_CONCEPT_KEYWORDS:
            if keyword in concept_lower:
                return EXPLANATION_TEXT_CONCEPT
        
        return None
    
    def _check_context_explanation(
        self,
        fact: Dict[str, Any],
        explanatory_texts: List[Dict[str, str]]
    ) -> Optional[str]:
        """Check for context-related explanatory texts."""
        fact_context = fact.get('context_id')
        
        for explanation in explanatory_texts:
            if explanation['context_id'] == fact_context:
                return EXPLANATION_CONTEXT_RELATED.format(text=explanation['text'])
        
        return None
    
    def _check_general_explanation(
        self,
        explanatory_texts: List[Dict[str, str]]
    ) -> Optional[str]:
        """Check for general document-level explanations."""
        for explanation in explanatory_texts:
            text_lower = explanation['text'].lower()
            
            for keyword in GENERAL_EXPLANATION_KEYWORDS:
                if keyword in text_lower:
                    return EXPLANATION_DOCUMENT_LEVEL.format(text=explanation['text'])
        
        return None


class ConceptChecker:
    """
    Checks if concepts are critical (should rarely be null).
    
    Responsibility: Concept classification logic.
    """
    
    def __init__(self):
        """Initialize concept checker."""
        from .null_validation_constants import CRITICAL_CONCEPTS
        self.critical_concepts = CRITICAL_CONCEPTS
    
    def is_critical(self, concept: str) -> bool:
        """
        Check if concept is critical.
        
        Args:
            concept: Concept name to check
            
        Returns:
            True if concept is critical, False otherwise
        """
        concept_lower = concept.lower()
        return any(
            critical in concept_lower 
            for critical in self.critical_concepts
        )