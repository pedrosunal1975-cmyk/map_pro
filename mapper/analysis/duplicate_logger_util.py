"""
Duplicate Logger Utility
=========================

Location: map_pro/engines/mapper/analysis/duplicate_logger_util.py

Specialized logging for duplicate analysis using Map Pro's logging system.
"""

from typing import Dict, Any, List
from core.system_logger import get_logger
from .duplicate_constants import (
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    SEVERITY_REDUNDANT,
    SEPARATOR_LENGTH,
    MAX_DUPLICATES_DETAIL_LOG
)

logger = get_logger(__name__, 'engine')


def log_analysis_start(total_facts: int) -> None:
    """Log start of duplicate analysis."""
    logger.info(f"Starting duplicate analysis on {total_facts} facts")


def log_analysis_complete(report: Dict[str, Any]) -> None:
    """Log completion of duplicate analysis."""
    total_groups = report['total_duplicate_groups']
    logger.info(f"Duplicate analysis complete: {total_groups} groups found")


def log_duplicate_summary(report: Dict[str, Any]) -> None:
    """
    Log comprehensive duplicate analysis summary.
    
    Args:
        report: Duplicate analysis report
    """
    total = report['total_duplicate_groups']
    
    if total == 0:
        logger.info("[OK] No duplicates found - clean source XBRL")
        return
    
    severity_counts = report['severity_counts']
    total_facts = report['total_duplicate_facts']
    total_analyzed = report['total_facts_analyzed']
    percentage = report['duplicate_percentage']
    
    # Header
    logger.warning(f"\n{'='*SEPARATOR_LENGTH}")
    logger.warning(f"DUPLICATE DETECTION ANALYSIS")
    logger.warning(f"{'='*SEPARATOR_LENGTH}")
    logger.warning(
        f"Found {total} duplicate group(s) affecting {total_facts} facts "
        f"({percentage:.1f}% of source XBRL)"
    )
    
    # Severity breakdown
    logger.warning(f"\nSeverity Breakdown:")
    
    critical = severity_counts[SEVERITY_CRITICAL]
    major = severity_counts[SEVERITY_MAJOR]
    minor = severity_counts[SEVERITY_MINOR]
    redundant = severity_counts[SEVERITY_REDUNDANT]
    
    if critical == 0:
        logger.info(f"  [OK] CRITICAL: 0")
    else:
        logger.error(f"  [!!!] CRITICAL: {critical}")
    
    if major == 0:
        logger.info(f"  [OK] MAJOR: 0")
    else:
        logger.warning(f"  [!] MAJOR: {major}")
    
    logger.info(f"  • MINOR (<1% variance): {minor}")
    logger.info(f"  • REDUNDANT (exact match): {redundant}")
    
    # Source attribution if available
    if 'source_attribution' in report:
        source_attr = report['source_attribution']
        logger.warning(f"\nSource Attribution:")
        for source, count in source_attr.items():
            pct = (count / total_facts * 100) if total_facts > 0 else 0
            logger.info(f"  • {source}: {count} ({pct:.1f}%)")
    
    # Quality assessment
    logger.warning(f"\nQuality Assessment:")
    assessment = report['quality_assessment']
    
    if critical > 0:
        logger.error(f"  [!!!] {assessment}")
    elif major > 0:
        logger.warning(f"  [!] {assessment}")
    else:
        logger.info(f"  [i] {assessment}")
    
    # Log critical findings in detail
    if report['has_critical_duplicates']:
        _log_critical_findings(report['critical_findings'])
    
    # Log major findings
    if report['has_major_duplicates']:
        _log_major_findings(report['major_findings'])
    
    logger.warning(f"{'='*SEPARATOR_LENGTH}\n")


def _log_critical_findings(findings: List[Dict[str, Any]]) -> None:
    """Log critical duplicate findings in detail."""
    logger.error(f"\n{'='*SEPARATOR_LENGTH}")
    logger.error(f"[!!!] CRITICAL DUPLICATES DETECTED - DATA INTEGRITY ISSUES")
    logger.error(f"{'='*SEPARATOR_LENGTH}")
    
    for idx, finding in enumerate(findings[:MAX_DUPLICATES_DETAIL_LOG], 1):
        logger.error(
            f"\n{idx}. Concept: {finding['concept']}\n"
            f"   Context: {finding['context']}\n"
            f"   Values: {finding['unique_values']}\n"
            f"   Variance: {finding['variance_percentage']*100:.2f}% "
            f"(${finding['max_variance_amount']:,.0f})\n"
            f"   Severity: {finding['severity']}"
        )


def _log_major_findings(findings: List[Dict[str, Any]]) -> None:
    """Log major duplicate findings."""
    logger.warning(f"\n{'='*SEPARATOR_LENGTH}")
    logger.warning(f"[!] MAJOR DUPLICATES - REVIEW RECOMMENDED")
    logger.warning(f"{'='*SEPARATOR_LENGTH}")
    
    for idx, finding in enumerate(findings[:MAX_DUPLICATES_DETAIL_LOG], 1):
        logger.warning(
            f"\n{idx}. Concept: {finding['concept']}\n"
            f"   Context: {finding['context']}\n"
            f"   Values: {finding['unique_values']}\n"
            f"   Variance: {finding['variance_percentage']*100:.2f}%"
        )


__all__ = [
    'log_analysis_start',
    'log_analysis_complete',
    'log_duplicate_summary'
]