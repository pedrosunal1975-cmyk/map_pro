"""
Duplicate Analyzer Helper
==========================

Location: map_pro/engines/mapper/analysis/duplicate_analyzer_helper.py

Analyzes individual duplicate groups and builds finding dictionaries.
"""

from typing import Dict, List, Tuple, Any
from .fact_extractor import extract_unique_values, extract_all_values
from .variance_calculator import calculate_variance, classify_severity


def analyze_single_duplicate(
    concept: str,
    context: str,
    facts: List[dict]
) -> Dict[str, Any]:
    """
    Analyze a single duplicate group.
    
    Args:
        concept: Concept identifier
        context: Context identifier
        facts: List of duplicate facts
        
    Returns:
        Finding dictionary with analysis
    """
    # Extract values
    all_values = extract_all_values(facts)
    unique_values = extract_unique_values(facts)
    
    # Calculate variance
    variance_pct, variance_amount = calculate_variance(all_values)
    
    # Classify severity
    severity = classify_severity(variance_pct, unique_values)
    
    return {
        'concept': concept,
        'context': context,
        'duplicate_count': len(facts),
        'unique_values': unique_values,
        'variance_percentage': variance_pct,
        'max_variance_amount': variance_amount,
        'severity': severity,
        'facts': facts
    }


def analyze_duplicate_groups(
    duplicate_groups: Dict[Tuple[str, str], List[dict]]
) -> List[Dict[str, Any]]:
    """
    Analyze all duplicate groups.
    
    Args:
        duplicate_groups: Dictionary of (concept, context) -> facts
        
    Returns:
        List of duplicate finding dictionaries
    """
    findings = []
    
    for (concept, context), facts in duplicate_groups.items():
        finding = analyze_single_duplicate(concept, context, facts)
        findings.append(finding)
    
    return findings


def separate_findings_by_severity(
    findings: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Separate findings by severity level.
    
    Args:
        findings: List of all duplicate findings
        
    Returns:
        Dictionary mapping severity to list of findings
    """
    from .duplicate_constants import (
        SEVERITY_CRITICAL,
        SEVERITY_MAJOR,
        SEVERITY_MINOR,
        SEVERITY_REDUNDANT
    )
    
    return {
        'critical': [f for f in findings if f['severity'] == SEVERITY_CRITICAL],
        'major': [f for f in findings if f['severity'] == SEVERITY_MAJOR],
        'minor': [f for f in findings if f['severity'] == SEVERITY_MINOR],
        'redundant': [f for f in findings if f['severity'] == SEVERITY_REDUNDANT]
    }


__all__ = [
    'analyze_single_duplicate',
    'analyze_duplicate_groups',
    'separate_findings_by_severity'
]