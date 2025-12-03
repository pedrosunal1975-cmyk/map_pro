"""
Mapping Logger.

Specialized logging functionality for mapping results, including unmapped facts
analysis and null value quality reports.

Location: /engines/mapper/mapping_logger.py
"""

from typing import Dict, Any, List, Optional
from core.system_logger import get_logger
from engines.mapper.mapping_utils import (
    extract_concept_from_fact,
    extract_value_from_fact,
    clean_recommendation_text,
    group_facts_by_reason,
    DEFAULT_NO_VALUE
)


# Constants for logging display
MAX_UNMAPPED_FACTS_DISPLAY = 20
SEPARATOR_LINE_LENGTH = 80


class MappingLogger:
    """
    Specialized logger for mapping operations.
    
    Handles detailed logging of:
    - Unmapped facts analysis
    - Null value quality reports
    - Pattern analysis
    - Recommendations
    """
    
    def __init__(self, logger_name: str = 'mapper'):
        """
        Initialize mapping logger.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = get_logger(logger_name, 'core')
    
    def log_mapping_completion(self, success_metrics: Dict[str, Any]) -> None:
        """
        Log mapping completion summary.
        
        Args:
            success_metrics: Success metrics dictionary
        """
        self.logger.info(
            f"Mapping completed: {success_metrics['mapped_facts']}/"
            f"{success_metrics['total_facts']} facts mapped "
            f"({success_metrics['success_rate']:.1f}%)"
        )
    
    def log_unmapped_facts_details(
        self, 
        resolved_facts: List[Dict[str, Any]], 
        success_metrics: Dict[str, Any]
    ) -> None:
        """
        Log detailed information about unmapped facts.
        
        Args:
            resolved_facts: List of all resolved facts
            success_metrics: Success metrics containing gap analysis
        """
        unmapped_count = success_metrics.get('unmapped_facts', 0)
        
        if unmapped_count == 0:
            self.logger.info("All facts successfully mapped!")
            return
        
        unmapped_facts = [f for f in resolved_facts if f.get('is_unmapped', False)]
        
        self._log_unmapped_header(unmapped_count)
        self._log_unmapped_by_reason(unmapped_facts)
        self._log_unmapped_patterns(success_metrics)
        self._log_unmapped_fact_details(unmapped_facts)
        self._log_unmapped_recommendations(success_metrics)
        self._log_unmapped_footer()
    
    def log_null_quality_report(self, null_report: Dict[str, Any]) -> None:
        """
        Log null value quality report.
        
        Args:
            null_report: Null quality report from validator
        """
        self._log_null_report_header(null_report)
        self._log_parsed_facts_null_analysis(null_report)
        self._log_null_report_issues(null_report)
        self._log_null_report_action_required(null_report)
        self._log_null_report_footer()

    def log_duplicate_analysis(self, duplicate_report: Dict[str, Any]) -> None:
        """
        Log duplicate detection analysis.
        
        Args:
            duplicate_report: Duplicate analysis report from DuplicateDetector
        """
        total_duplicates = duplicate_report.get('total_duplicate_groups', 0)
        
        # If no duplicates, log success and return
        if total_duplicates == 0:
            self.logger.info("\n" + "="*SEPARATOR_LINE_LENGTH)
            self.logger.info("DUPLICATE DETECTION - CLEAN XBRL FILING")
            self.logger.info("="*SEPARATOR_LINE_LENGTH)
            self.logger.info("[OK] No duplicate facts detected in source XBRL")
            self.logger.info("="*SEPARATOR_LINE_LENGTH + "\n")
            return
        
        # Log duplicate findings
        self._log_duplicate_header(duplicate_report)
        self._log_duplicate_severity_breakdown(duplicate_report)
        self._log_duplicate_quality_assessment(duplicate_report)
        self._log_critical_duplicate_details(duplicate_report)
        self._log_major_duplicate_details(duplicate_report)
        self._log_duplicate_footer()


    def _log_duplicate_header(self, report: Dict[str, Any]) -> None:
        """Log duplicate analysis header."""
        total = report['total_duplicate_groups']
        facts = report['total_duplicate_facts']
        pct = report['duplicate_percentage']
        
        self.logger.warning(f"\n{'='*SEPARATOR_LINE_LENGTH}")
        self.logger.warning(f"DUPLICATE DETECTION ANALYSIS")
        self.logger.warning(f"{'='*SEPARATOR_LINE_LENGTH}")
        self.logger.warning(
            f"Found {total} duplicate group(s) affecting {facts} facts "
            f"({pct:.1f}% of source XBRL)"
        )


    def _log_duplicate_severity_breakdown(self, report: Dict[str, Any]) -> None:
        """Log severity breakdown."""
        counts = report['severity_counts']
        
        self.logger.warning(f"\nSeverity Breakdown:")
        
        if counts.get('CRITICAL', 0) > 0:
            self.logger.error(f"  [!] CRITICAL (>5% variance): {counts['CRITICAL']} - SEVERE DATA ISSUES")
        else:
            self.logger.warning(f"  [OK] CRITICAL: 0")
        
        if counts.get('MAJOR', 0) > 0:
            self.logger.warning(f"  [!] MAJOR (1-5% variance): {counts['MAJOR']} - Review recommended")
        else:
            self.logger.info(f"  [OK] MAJOR: 0")
        
        self.logger.info(f"  • MINOR (<1% variance): {counts.get('MINOR', 0)}")
        self.logger.info(f"  • REDUNDANT (exact match): {counts.get('REDUNDANT', 0)}")


    def _log_duplicate_quality_assessment(self, report: Dict[str, Any]) -> None:
        """Log overall quality assessment."""
        assessment = report.get('quality_assessment', '')
        
        self.logger.warning(f"\nQuality Assessment:")
        
        if report.get('has_critical_duplicates'):
            self.logger.error(f"  [!] {assessment}")
        elif report.get('has_major_duplicates'):
            self.logger.warning(f"  [!] {assessment}")
        else:
            self.logger.info(f"  [i] {assessment}")


    def _log_critical_duplicate_details(self, report: Dict[str, Any]) -> None:
        """Log critical duplicate details."""
        critical = report.get('critical_findings', [])
        
        if not critical:
            return
        
        self.logger.error(f"\n{'='*SEPARATOR_LINE_LENGTH}")
        self.logger.error(f"CRITICAL DUPLICATES - DATA INTEGRITY ISSUES")
        self.logger.error(f"{'='*SEPARATOR_LINE_LENGTH}")
        self.logger.error(
            f"[!] WARNING: These duplicates indicate serious data quality problems."
        )
        self.logger.error(
            f"Consider excluding this filing from financial analysis.\n"
        )
        
        for idx, finding in enumerate(critical[:MAX_UNMAPPED_FACTS_DISPLAY], 1):
            variance_pct = finding.get('variance_percentage', 0) * 100
            variance_amt = finding.get('max_variance_amount', 0)
            
            self.logger.error(
                f"{idx}. Concept: {finding['concept']}\n"
                f"   Context: {finding['context']}\n"
                f"   Duplicate Values: {finding['unique_values']}\n"
                f"   Variance: {variance_pct:.2f}% (${variance_amt:,.0f})\n"
                f"   Duplicate Count: {finding['duplicate_count']} instances\n"
            )


    def _log_major_duplicate_details(self, report: Dict[str, Any]) -> None:
        """Log major duplicate details."""
        major = report.get('major_findings', [])
        
        if not major:
            return
        
        self.logger.warning(f"\n{'='*SEPARATOR_LINE_LENGTH}")
        self.logger.warning(f"MAJOR DUPLICATES - REVIEW RECOMMENDED")
        self.logger.warning(f"{'='*SEPARATOR_LINE_LENGTH}")
        self.logger.warning(
            f"These duplicates show significant variance. Manual review advised.\n"
        )
        
        for idx, finding in enumerate(major[:MAX_UNMAPPED_FACTS_DISPLAY], 1):
            variance_pct = finding.get('variance_percentage', 0) * 100
            
            self.logger.warning(
                f"{idx}. Concept: {finding['concept']}\n"
                f"   Values: {finding['unique_values']}\n"
                f"   Variance: {variance_pct:.2f}%\n"
            )


    def _log_duplicate_footer(self) -> None:
        """Log duplicate analysis footer."""
        self.logger.warning(f"{'='*SEPARATOR_LINE_LENGTH}\n")

    # ========================================================================
    # Unmapped Facts Logging Methods
    # ========================================================================
    
    def _log_unmapped_header(self, unmapped_count: int) -> None:
        """Log unmapped facts header."""
        self.logger.warning(f"\n{'=' * SEPARATOR_LINE_LENGTH}")
        self.logger.warning(f"UNMAPPED FACTS ANALYSIS - {unmapped_count} facts could not be mapped")
        self.logger.warning(f"{'=' * SEPARATOR_LINE_LENGTH}")
    
    def _log_unmapped_by_reason(self, unmapped_facts: List[Dict[str, Any]]) -> None:
        """
        Log unmapped facts grouped by reason.
        
        Args:
            unmapped_facts: List of unmapped facts
        """
        by_reason = group_facts_by_reason(unmapped_facts)
        
        self.logger.warning(f"\nUnmapped Facts by Reason:")
        for reason, facts in by_reason.items():
            self.logger.warning(f"  - {reason}: {len(facts)} facts")
    
    def _log_unmapped_patterns(self, success_metrics: Dict[str, Any]) -> None:
        """
        Log pattern analysis of unmapped facts.
        
        Args:
            success_metrics: Success metrics containing gap analysis
        """
        gap_analysis = success_metrics.get('gap_analysis', {})
        patterns = gap_analysis.get('patterns', {})
        
        self.logger.warning(f"\nPattern Analysis:")
        self.logger.warning(f"  - Missing prefix: {patterns.get('missing_prefix_count', 0)} facts")
        self.logger.warning(f"  - Complex extensions: {patterns.get('complex_extensions_count', 0)} facts")
        self.logger.warning(f"  - Unknown business terms: {patterns.get('unknown_business_terms_count', 0)} facts")
        self.logger.warning(f"  - Most common issue: {gap_analysis.get('most_common_issue', 'unknown')}")
    
    def _log_unmapped_fact_details(self, unmapped_facts: List[Dict[str, Any]]) -> None:
        """
        Log detailed list of unmapped facts.
        
        Args:
            unmapped_facts: List of unmapped facts
        """
        self.logger.warning(f"\nDetailed Unmapped Facts List:")
        self.logger.warning(
            f"(Showing first {MAX_UNMAPPED_FACTS_DISPLAY} of {len(unmapped_facts)} unmapped facts)\n"
        )
        
        for idx, fact in enumerate(unmapped_facts[:MAX_UNMAPPED_FACTS_DISPLAY], 1):
            self._log_single_unmapped_fact(idx, fact)
        
        if len(unmapped_facts) > MAX_UNMAPPED_FACTS_DISPLAY:
            remaining = len(unmapped_facts) - MAX_UNMAPPED_FACTS_DISPLAY
            self.logger.warning(f"\n  ... and {remaining} more unmapped facts (not shown)")
    
    def _log_single_unmapped_fact(self, index: int, fact: Dict[str, Any]) -> None:
        """
        Log details of a single unmapped fact.
        
        Args:
            index: Fact index number
            fact: Fact dictionary
        """
        concept = extract_concept_from_fact(fact)
        value = extract_value_from_fact(fact)
        
        self.logger.warning(
            f"  {index}. Concept: {concept}\n"
            f"     Namespace: {fact.get('concept_namespace', DEFAULT_NO_VALUE)}\n"
            f"     Value: {value}\n"
            f"     Context: {fact.get('context_id', DEFAULT_NO_VALUE)}\n"
            f"     Unit: {fact.get('unit_id', DEFAULT_NO_VALUE)}\n"
            f"     Decimals: {fact.get('decimals', DEFAULT_NO_VALUE)}\n"
            f"     Reason: {fact.get('mapping_reason', 'Unknown')}\n"
        )
    
    def _log_unmapped_recommendations(self, success_metrics: Dict[str, Any]) -> None:
        """
        Log recommendations for unmapped facts.
        
        Args:
            success_metrics: Success metrics containing recommendations
        """
        self.logger.warning(f"\nRecommendations:")
        recommendations = success_metrics.get('recommendations', [])
        for rec in recommendations:
            clean_rec = clean_recommendation_text(rec)
            if clean_rec:
                self.logger.warning(f"  - {clean_rec}")
    
    def _log_unmapped_footer(self) -> None:
        """Log unmapped facts footer."""
        self.logger.warning(f"{'=' * SEPARATOR_LINE_LENGTH}\n")
    
    # ========================================================================
    # Null Quality Report Logging Methods
    # ========================================================================
    
    def _log_null_report_header(self, null_report: Dict[str, Any]) -> None:
        """Log null report header with score."""
        score = null_report.get('overall_quality_score', 0)
        grade = null_report.get('data_quality_grade', 'UNKNOWN')
        
        self.logger.info(f"\n{'=' * SEPARATOR_LINE_LENGTH}")
        self.logger.info(f"NULL VALUE QUALITY REPORT")
        self.logger.info(f"{'=' * SEPARATOR_LINE_LENGTH}")
        self.logger.info(f"\nOverall Quality Score: {score:.1f}/100 ({grade})")
    
    def _log_parsed_facts_null_analysis(self, null_report: Dict[str, Any]) -> None:
        """Log parsed facts null analysis section."""
        parsed = null_report.get('parsed_facts_analysis', {})
        if not parsed:
            return
        
        self.logger.info(f"\nParsed Facts Analysis:")
        self.logger.info(f"  - Total nulls: {parsed.get('total_nulls', 0)}")
        self.logger.info(f"  - Nil in source XBRL: {parsed.get('nil_in_source', 0)} (LEGITIMATE)")
        self.logger.info(f"  - Explained nulls: {parsed.get('explained_nulls', 0)}")
        self.logger.info(f"  - Suspicious nulls: {parsed.get('suspicious_nulls', 0)}")
        self.logger.info(f"  - Critical nulls: {parsed.get('critical_nulls', 0)}")
        self.logger.info(f"  - Explanation coverage: {parsed.get('explanation_coverage', 0):.1f}%")
    
    def _log_null_report_issues(self, null_report: Dict[str, Any]) -> None:
        """Log critical issues, warnings, and info from null report."""
        self._log_critical_issues(null_report.get('critical_issues', []))
        self._log_warnings(null_report.get('warnings', []))
        self._log_info_items(null_report.get('info', []))
    
    def _log_critical_issues(self, critical_issues: List[str]) -> None:
        """Log critical issues."""
        if critical_issues:
            self.logger.error(f"\n[CRITICAL ISSUES]")
            for issue in critical_issues:
                self.logger.error(f"  ! {issue}")
    
    def _log_warnings(self, warnings: List[str]) -> None:
        """Log warnings."""
        if warnings:
            self.logger.warning(f"\n[WARNINGS]")
            for warning in warnings:
                self.logger.warning(f"  - {warning}")
    
    def _log_info_items(self, info_items: List[str]) -> None:
        """Log info items."""
        if info_items:
            self.logger.info(f"\n[INFO]")
            for info in info_items:
                self.logger.info(f"  - {info}")
    
    def _log_null_report_action_required(self, null_report: Dict[str, Any]) -> None:
        """Log whether action is required."""
        if null_report.get('action_required'):
            self.logger.error(f"\n[ACTION REQUIRED] Manual review of critical nulls is needed")
        else:
            self.logger.info(f"\n[OK] No critical issues detected with null values")
    
    def _log_null_report_footer(self) -> None:
        """Log null report footer."""
        self.logger.info(f"\n{'=' * SEPARATOR_LINE_LENGTH}\n")


__all__ = ['MappingLogger']