"""
Fact Extractor
==============

Location: map_pro/engines/mapper/analysis/fact_extractor.py

Market-agnostic extraction of fields from facts.

Different markets use different field names for the same data:
- SEC: concept_qname, contextRef, fact_value
- FCA: qname, context_id, value
- ESMA: element_name, context_ref, amount

This module provides universal extraction that works across all markets.
"""

from typing import Any, Optional, List
from .duplicate_constants import (
    CONCEPT_FIELD_NAMES,
    CONTEXT_FIELD_NAMES,
    VALUE_FIELD_NAMES
)


def extract_concept(fact: dict) -> Optional[str]:
    """
    Extract concept from fact (market-agnostic).
    
    Args:
        fact: Fact dictionary
        
    Returns:
        Concept string or None
    """
    for field_name in CONCEPT_FIELD_NAMES:
        if field_name in fact and fact[field_name]:
            return str(fact[field_name])
    return None


def extract_context(fact: dict) -> Optional[str]:
    """
    Extract context from fact (market-agnostic).
    
    Args:
        fact: Fact dictionary
        
    Returns:
        Context string or None
    """
    for field_name in CONTEXT_FIELD_NAMES:
        if field_name in fact and fact[field_name]:
            return str(fact[field_name])
    return None


def extract_value(fact: dict) -> Any:
    """
    Extract value from fact (market-agnostic).
    
    Args:
        fact: Fact dictionary
        
    Returns:
        Value (any type) or None
    """
    for field_name in VALUE_FIELD_NAMES:
        if field_name in fact:
            return fact[field_name]
    return None


def extract_all_values(facts: List[dict]) -> List[Any]:
    """
    Extract values from list of facts.
    
    Args:
        facts: List of fact dictionaries
        
    Returns:
        List of values
    """
    return [extract_value(fact) for fact in facts]


def extract_unique_values(facts: List[dict]) -> List[Any]:
    """
    Extract unique values from list of facts.
    
    Args:
        facts: List of fact dictionaries
        
    Returns:
        List of unique values
    """
    values = extract_all_values(facts)
    # Convert to strings for comparison (handles different types)
    seen = set()
    unique = []
    
    for val in values:
        val_str = str(val)
        if val_str not in seen:
            seen.add(val_str)
            unique.append(val)
    
    return unique


__all__ = [
    'extract_concept',
    'extract_context',
    'extract_value',
    'extract_all_values',
    'extract_unique_values'
]