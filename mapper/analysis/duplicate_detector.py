"""
Map Pro Duplicate Detector - Main Orchestrator
===============================================

Location: map_pro/engines/mapper/analysis/duplicate_detector.py

Main orchestrator for comprehensive duplicate detection and analysis.

Responsibilities:
- Coordinate all duplicate analysis components
- Detect duplicates in parsed facts
- Classify severity (CRITICAL/MAJOR/MINOR/REDUNDANT)
- Trace source (SOURCE_DATA vs MAPPING_INTRODUCED)
- Detect patterns and assess risk
- Generate comprehensive reports
- Log findings using Map Pro's logging system

Architecture: Market-agnostic duplicate detection for all XBRL sources.
"""

from typing import Dict, List, Any
from pathlib import Path
from core.system_logger import get_logger

# Import all components
from .fact_grouper import find_duplicate_groups, count_facts_in_groups
from .duplicate_analyzer_helper import analyze_duplicate_groups
from .duplicate_report_builder import build_duplicate_report, build_empty_report
from .duplicate_logger_util import (
    log_analysis_start,
    log_analysis_complete,
    log_duplicate_summary
)
from .duplicate_source_tracer import DuplicateSourceTracer
from .duplicate_pattern_detector import detect_patterns
from .duplicate_assessors import assess_risk, assess_significance

logger = get_logger(__name__, 'engine')


class DuplicateDetector:
    """
    Main orchestrator for duplicate detection and analysis.
    
    Coordinates all duplicate analysis components to provide comprehensive
    duplicate detection with severity classification, source attribution,
    pattern detection, and risk assessment.
    
    This is a WARNING system, not a blocker - mapper continues processing.
    """
    
    def __init__(self):
        """Initialize duplicate detector with all components."""
        self.logger = logger
        
        # Initialize source tracer
        try:
            self.source_tracer = DuplicateSourceTracer()
            self.logger.debug("Duplicate source tracer initialized")
        except Exception as e:
            self.logger.warning(f"Source tracer initialization failed: {e}")
            self.source_tracer = None
        
        self.logger.info("Map Pro duplicate detector initialized")
    
    def analyze_duplicates(
        self,
        parsed_facts: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        parsed_facts_path: Path = None
    ) -> Dict[str, Any]:
        """
        Analyze parsed facts for duplicates with comprehensive analysis.
        
        Args:
            parsed_facts: List of parsed fact dictionaries
            metadata: Filing metadata (filing_id, filing_date, company, etc.)
            parsed_facts_path: Optional path to parsed_facts.json for source tracing
            
        Returns:
            Comprehensive duplicate analysis report
        """
        total_facts = len(parsed_facts)
        
        self.logger.info(f"Analyzing {total_facts} facts for duplicates")
        log_analysis_start(total_facts)
        
        # Find duplicate groups
        duplicate_groups = find_duplicate_groups(parsed_facts)
        
        if not duplicate_groups:
            self.logger.info("No duplicates detected - clean XBRL filing")
            report = build_empty_report(total_facts)
            log_duplicate_summary(report)
            return report
        
        total_groups = len(duplicate_groups)
        duplicate_fact_count = count_facts_in_groups(duplicate_groups)
        
        self.logger.info(
            f"Found {total_groups} duplicate groups affecting {duplicate_fact_count} facts"
        )
        
        # Analyze individual duplicate groups
        findings = analyze_duplicate_groups(duplicate_groups)
        
        # Trace source attribution if possible
        source_report = None
        if self.source_tracer and parsed_facts_path:
            try:
                source_report = self.source_tracer.trace_duplicate_sources(
                    parsed_facts_path,
                    duplicate_groups
                )
                self.logger.debug("Source attribution complete")
            except Exception as e:
                self.logger.warning(f"Source tracing failed: {e}")
        
        # Detect patterns
        try:
            patterns = detect_patterns(findings)
            self.logger.debug("Pattern detection complete")
        except Exception as e:
            self.logger.warning(f"Pattern detection failed: {e}")
            patterns = {}
        
        # Assess risk
        try:
            risk_assessment = assess_risk(findings)
            self.logger.debug("Risk assessment complete")
        except Exception as e:
            self.logger.warning(f"Risk assessment failed: {e}")
            risk_assessment = {}
        
        # Assess significance
        try:
            significance = assess_significance(findings)
            self.logger.debug("Significance assessment complete")
        except Exception as e:
            self.logger.warning(f"Significance assessment failed: {e}")
            significance = {}
        
        # Build comprehensive analysis
        comprehensive_analysis = {
            'patterns': patterns,
            'risk_assessment': risk_assessment,
            'significance': significance
        }
        
        # Build final report
        report = build_duplicate_report(
            findings=findings,
            total_facts=total_facts,
            metadata=metadata,
            source_report=source_report,
            comprehensive_analysis=comprehensive_analysis
        )
        
        # Log summary
        log_duplicate_summary(report)
        log_analysis_complete(report)
        
        self.logger.info("Duplicate analysis complete")
        
        return report


__all__ = ['DuplicateDetector']