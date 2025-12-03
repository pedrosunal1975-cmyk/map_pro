"""
Mapping Utilities.

Reusable utility functions for data extraction, formatting, and manipulation
in the mapping process.

Location: /engines/mapper/mapping_utils.py
"""

from typing import Dict, Any, List


# Constants for data extraction
CONCEPT_FIELD_NAMES = [
    'concept_qname',
    'concept',
    'concept_local_name',
    'name',
    'element'
]

VALUE_FIELD_NAMES = [
    'fact_value',
    'value',
    'amount'
]

# Default values when data is missing
DEFAULT_NO_CONCEPT = 'NO_CONCEPT_IDENTIFIER'
DEFAULT_NO_VALUE = 'N/A'

# Display limits
MAX_VALUE_LENGTH_DISPLAY = 50


def extract_concept_from_fact(fact: Dict[str, Any]) -> str:
    """
    Extract concept identifier from fact.
    
    Tries multiple field names in priority order to find the concept identifier.
    
    Args:
        fact: Fact dictionary
        
    Returns:
        Concept identifier string or default if not found
    """
    for field_name in CONCEPT_FIELD_NAMES:
        concept = fact.get(field_name)
        if concept:
            return concept
    return DEFAULT_NO_CONCEPT


def extract_value_from_fact(fact: Dict[str, Any]) -> str:
    """
    Extract and format value from fact.
    
    Tries multiple field names in priority order to find the value,
    then formats it for display.
    
    Args:
        fact: Fact dictionary
        
    Returns:
        Formatted value string or default if not found
    """
    for field_name in VALUE_FIELD_NAMES:
        value = fact.get(field_name)
        if value is not None:
            return format_fact_value(value)
    return DEFAULT_NO_VALUE


def format_fact_value(value: Any) -> str:
    """
    Format fact value for display.
    
    Truncates long values and converts to string.
    
    Args:
        value: Value to format
        
    Returns:
        Formatted value string
    """
    value_str = str(value)
    if len(value_str) > MAX_VALUE_LENGTH_DISPLAY:
        return value_str[:MAX_VALUE_LENGTH_DISPLAY - 3] + "..."
    return value_str


def group_facts_by_reason(
    unmapped_facts: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group unmapped facts by their mapping failure reason.
    
    Args:
        unmapped_facts: List of unmapped facts
        
    Returns:
        Dictionary mapping reasons to lists of facts
    """
    by_reason = {}
    for fact in unmapped_facts:
        reason = fact.get('mapping_reason', 'Unknown reason')
        if reason not in by_reason:
            by_reason[reason] = []
        by_reason[reason].append(fact)
    return by_reason


def clean_recommendation_text(text: str) -> str:
    """
    Clean recommendation text by removing non-ASCII characters.
    
    Useful for logging recommendations that may contain special characters
    that could cause encoding issues.
    
    Args:
        text: Original recommendation text
        
    Returns:
        Cleaned text string with only ASCII characters
    """
    return text.encode('ascii', 'ignore').decode('ascii').strip()


def extract_filing_id_from_job_data(job_data: Dict[str, Any]) -> str:
    """
    Extract filing ID from job data with multiple fallback attempts.
    
    Args:
        job_data: Job data dictionary
        
    Returns:
        Filing ID string or None if not found
    """
    return (
        job_data.get('parameters', {}).get('filing_universal_id') or
        job_data.get('filing_universal_id') or  
        job_data.get('parameters', {}).get('filing_id')
    )


__all__ = [
    'CONCEPT_FIELD_NAMES',
    'VALUE_FIELD_NAMES',
    'DEFAULT_NO_CONCEPT',
    'DEFAULT_NO_VALUE',
    'MAX_VALUE_LENGTH_DISPLAY',
    'extract_concept_from_fact',
    'extract_value_from_fact',
    'format_fact_value',
    'group_facts_by_reason',
    'clean_recommendation_text',
    'extract_filing_id_from_job_data'
]