"""
Duplicate Risk and Significance Assessment
===========================================

Location: map_pro/engines/mapper/analysis/duplicate_assessors.py

Assesses financial risk and significance of duplicates.
"""

from typing import Dict, List, Any
from .duplicate_constants import (
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    HIGH_SIGNIFICANCE_AMOUNT,
    MEDIUM_SIGNIFICANCE_AMOUNT,
    CORE_STATEMENT_CONCEPTS
)


# ============================================================================
# RISK ASSESSMENT
# ============================================================================

def assess_risk(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess overall financial risk of duplicates.
    
    Args:
        findings: List of duplicate findings
        
    Returns:
        Risk assessment dictionary
    """
    high_risk = []
    medium_risk = []
    low_risk = []
    
    for finding in findings:
        risk_level = _assess_finding_risk(finding)
        
        if risk_level == 'HIGH':
            high_risk.append(finding)
        elif risk_level == 'MEDIUM':
            medium_risk.append(finding)
        else:
            low_risk.append(finding)
    
    # Determine overall risk
    if high_risk:
        overall = 'HIGH'
    elif len(medium_risk) > 5:
        overall = 'MEDIUM'
    elif medium_risk:
        overall = 'MEDIUM'
    else:
        overall = 'LOW'
    
    return {
        'overall_risk': overall,
        'high_risk_count': len(high_risk),
        'medium_risk_count': len(medium_risk),
        'low_risk_count': len(low_risk),
        'high_risk_concepts': [f['concept'] for f in high_risk],
        'medium_risk_concepts': [f['concept'] for f in medium_risk]
    }


def _assess_finding_risk(finding: Dict[str, Any]) -> str:
    """Assess risk of individual finding."""
    severity = finding['severity']
    concept = finding['concept']
    variance_amount = finding.get('max_variance_amount', 0)
    
    # CRITICAL severity = HIGH risk
    if severity == SEVERITY_CRITICAL:
        return 'HIGH'
    
    # Core concept + MAJOR severity = HIGH risk
    if severity == SEVERITY_MAJOR and _is_core_concept(concept):
        return 'HIGH'
    
    # Large variance amount = MEDIUM risk
    if variance_amount > HIGH_SIGNIFICANCE_AMOUNT:
        return 'MEDIUM'
    
    # MAJOR severity = MEDIUM risk
    if severity == SEVERITY_MAJOR:
        return 'MEDIUM'
    
    return 'LOW'


# ============================================================================
# SIGNIFICANCE ASSESSMENT
# ============================================================================

def assess_significance(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess financial significance of duplicates.
    
    Args:
        findings: List of duplicate findings
        
    Returns:
        Significance assessment dictionary
    """
    high_sig = []
    medium_sig = []
    low_sig = []
    
    for finding in findings:
        sig_level = _assess_finding_significance(finding)
        
        if sig_level == 'HIGH':
            high_sig.append(finding)
        elif sig_level == 'MEDIUM':
            medium_sig.append(finding)
        else:
            low_sig.append(finding)
    
    return {
        'high_significance_count': len(high_sig),
        'medium_significance_count': len(medium_sig),
        'low_significance_count': len(low_sig),
        'high_significance_concepts': [f['concept'] for f in high_sig],
        'medium_significance_concepts': [f['concept'] for f in medium_sig]
    }


def _assess_finding_significance(finding: Dict[str, Any]) -> str:
    """Assess significance of individual finding."""
    concept = finding['concept']
    variance_amount = finding.get('max_variance_amount', 0)
    
    # Core financial concept = HIGH significance
    if _is_core_concept(concept):
        return 'HIGH'
    
    # Large dollar amount = HIGH significance
    if variance_amount > HIGH_SIGNIFICANCE_AMOUNT:
        return 'HIGH'
    
    # Medium dollar amount = MEDIUM significance
    if variance_amount > MEDIUM_SIGNIFICANCE_AMOUNT:
        return 'MEDIUM'
    
    return 'LOW'


def _is_core_concept(concept: str) -> bool:
    """Check if concept is a core financial statement concept."""
    # Check exact match
    if concept in CORE_STATEMENT_CONCEPTS:
        return True
    
    # Check if concept ends with any core concept (handles namespaces)
    for core in CORE_STATEMENT_CONCEPTS:
        if concept.endswith(core):
            return True
    
    return False


__all__ = [
    'assess_risk',
    'assess_significance'
]