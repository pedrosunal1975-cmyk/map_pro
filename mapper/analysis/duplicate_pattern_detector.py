"""
Duplicate Pattern Detector
===========================

Location: map_pro/engines/mapper/analysis/duplicate_pattern_detector.py

Detects systematic patterns in duplicates.
"""

from typing import Dict, List, Any
from collections import defaultdict


def detect_patterns(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect systematic patterns in duplicates.
    
    Args:
        findings: List of duplicate findings
        
    Returns:
        Dictionary of detected patterns
    """
    # Pattern by statement type (if available)
    by_statement = _group_by_statement(findings)
    
    # Pattern by value type (numeric, text, etc)
    by_value_type = _group_by_value_type(findings)
    
    # Pattern by severity
    by_severity = _group_by_severity(findings)
    
    # Detect systematic patterns
    systematic_patterns = _identify_systematic_patterns(
        by_statement,
        by_value_type,
        by_severity
    )
    
    return {
        'by_statement': by_statement,
        'by_value_type': by_value_type,
        'by_severity': by_severity,
        'systematic_patterns': systematic_patterns
    }


def _group_by_statement(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Group findings by statement type if available in facts."""
    statement_counts = defaultdict(int)
    
    for finding in findings:
        # Check if any fact has statement info
        facts = finding.get('facts', [])
        for fact in facts:
            stmt = fact.get('statement', 'unknown')
            statement_counts[stmt] += 1
            break  # Count once per finding
    
    return dict(statement_counts)


def _group_by_value_type(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Group findings by value type."""
    type_counts = defaultdict(int)
    
    for finding in findings:
        unique_values = finding.get('unique_values', [])
        if not unique_values:
            type_counts['empty'] += 1
            continue
        
        # Check first unique value type
        val = unique_values[0]
        
        if val is None:
            val_type = 'null'
        elif isinstance(val, (int, float)):
            val_type = 'numeric'
        elif isinstance(val, str):
            if val.strip() == '':
                val_type = 'empty_string'
            else:
                try:
                    float(val)
                    val_type = 'numeric_string'
                except ValueError:
                    val_type = 'text'
        else:
            val_type = 'other'
        
        type_counts[val_type] += 1
    
    return dict(type_counts)


def _group_by_severity(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Group findings by severity."""
    severity_counts = defaultdict(int)
    
    for finding in findings:
        severity = finding.get('severity', 'unknown')
        severity_counts[severity] += 1
    
    return dict(severity_counts)


def _identify_systematic_patterns(
    by_statement: Dict[str, int],
    by_value_type: Dict[str, int],
    by_severity: Dict[str, int]
) -> List[str]:
    """Identify systematic patterns that indicate systemic issues."""
    patterns = []
    
    # Check if duplicates cluster in one statement
    if by_statement:
        max_stmt = max(by_statement, key=by_statement.get)
        max_count = by_statement[max_stmt]
        total = sum(by_statement.values())
        
        if max_count / total > 0.7:  # 70% in one statement
            patterns.append(
                f"Duplicates heavily concentrated in {max_stmt} statement ({max_count}/{total})"
            )
    
    # Check if duplicates are all one type
    if by_value_type:
        max_type = max(by_value_type, key=by_value_type.get)
        max_count = by_value_type[max_type]
        total = sum(by_value_type.values())
        
        if max_count / total > 0.8:  # 80% one type
            patterns.append(
                f"Duplicates predominantly {max_type} values ({max_count}/{total})"
            )
    
    # Check severity distribution
    from .duplicate_constants import SEVERITY_CRITICAL, SEVERITY_MAJOR
    
    critical_count = by_severity.get(SEVERITY_CRITICAL, 0)
    major_count = by_severity.get(SEVERITY_MAJOR, 0)
    
    if critical_count > 0:
        patterns.append(f"Contains {critical_count} CRITICAL duplicates requiring immediate review")
    
    if major_count > 5:
        patterns.append(f"Multiple MAJOR duplicates ({major_count}) suggest systematic mapping issue")
    
    if not patterns:
        patterns.append("No systematic patterns detected - duplicates appear random")
    
    return patterns


__all__ = ['detect_patterns']