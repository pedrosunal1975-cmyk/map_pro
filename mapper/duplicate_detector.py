"""
Map Pro Duplicate Detector
==========================

Detects and analyzes duplicate facts in source XBRL filings.

Critical Purpose:
- Identify data integrity issues in XBRL filings
- Flag filings with material duplicate conflicts
- Provide severity classification for quality assessment
- Act as early warning system for unreliable financial data

Architecture: Market-agnostic duplicate detection for all XBRL sources.

Severity Levels:
- CRITICAL: Same concept, material variance (>5%) - severe data integrity issue
- MAJOR: Same concept, significant variance (1-5%) - needs review
- MINOR: Same concept, small variance (<1%) - likely rounding/formatting
- REDUNDANT: Same concept, exact same value - harmless duplicate

This is a WARNING system, not a blocker - mapper continues processing.
"""

from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


# Severity thresholds (variance as decimal, e.g., 0.05 = 5%)
CRITICAL_VARIANCE_THRESHOLD = 0.05  # 5% or more variance
MAJOR_VARIANCE_THRESHOLD = 0.01     # 1-5% variance
MINOR_VARIANCE_THRESHOLD = 0.0001   # 0.01-1% variance

# Display limits
MAX_DUPLICATES_DETAIL_LOG = 10
SEPARATOR_LENGTH = 80

# Severity levels
SEVERITY_CRITICAL = 'CRITICAL'
SEVERITY_MAJOR = 'MAJOR'
SEVERITY_MINOR = 'MINOR'
SEVERITY_REDUNDANT = 'REDUNDANT'


class DuplicateDetector:
    """
    Detects duplicate facts in source XBRL filings.
    
    Responsibilities:
    - Identify facts with same concept + context
    - Calculate variance between duplicate values
    - Classify severity of duplicates
    - Generate duplicate analysis report
    - Provide warnings for quality assessment
    
    Does NOT:
    - Block mapper processing
    - Modify facts or database
    - Make market-specific assumptions
    """
    
    def __init__(self):
        """Initialize duplicate detector."""
        self.logger = logger
        self.logger.info("Duplicate detector initialized")
    
    def analyze_duplicates(
        self,
        parsed_facts: List[Dict[str, Any]],
        parsed_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze parsed facts for duplicates.
        
        Args:
            parsed_facts: List of facts from source XBRL
            parsed_metadata: Metadata from parsing (filing info)
            
        Returns:
            Duplicate analysis report dictionary
        """
        self.logger.info(f"Analyzing {len(parsed_facts)} facts for duplicates...")
        
        # Group facts by concept + context
        fact_groups = self._group_facts_by_concept_and_context(parsed_facts)
        
        # Find duplicates (groups with >1 fact)
        duplicate_groups = {
            key: facts for key, facts in fact_groups.items()
            if len(facts) > 1
        }
        
        if not duplicate_groups:
            self.logger.info("No duplicates found in source XBRL")
            return self._build_empty_report(len(parsed_facts))
        
        # Analyze each duplicate group
        duplicate_findings = self._analyze_duplicate_groups(duplicate_groups)
        
        # Build comprehensive report
        report = self._build_duplicate_report(
            duplicate_findings,
            len(parsed_facts),
            parsed_metadata
        )
        
        # Log summary
        self._log_duplicate_summary(report)
        
        return report
    
    def _group_facts_by_concept_and_context(
        self,
        facts: List[Dict[str, Any]]
    ) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
        """
        Group facts by (concept, context) pair.
        
        Args:
            facts: List of fact dictionaries
            
        Returns:
            Dictionary mapping (concept, context) to list of matching facts
        """
        groups = defaultdict(list)
        
        for fact in facts:
            concept = self._extract_concept(fact)
            context = self._extract_context(fact)
            
            if concept and context:
                key = (concept, context)
                groups[key].append(fact)
        
        return dict(groups)
    
    def _extract_concept(self, fact: Dict[str, Any]) -> str:
        """
        Extract concept identifier from fact.
        
        Args:
            fact: Fact dictionary
            
        Returns:
            Concept string or None
        """
        # Try multiple field names (market-agnostic)
        for field in ['concept_qname', 'concept', 'concept_local_name', 'name']:
            concept = fact.get(field)
            if concept:
                return str(concept)
        return None
    
    def _extract_context(self, fact: Dict[str, Any]) -> str:
        """
        Extract context identifier from fact.
        
        Args:
            fact: Fact dictionary
            
        Returns:
            Context string or None
        """
        # Try multiple field names (market-agnostic)
        for field in ['context_ref', 'context_id', 'contextRef']:
            context = fact.get(field)
            if context:
                return str(context)
        return None
    
    def _analyze_duplicate_groups(
        self,
        duplicate_groups: Dict[Tuple[str, str], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze each duplicate group for severity.
        
        Args:
            duplicate_groups: Dictionary of (concept, context) -> facts
            
        Returns:
            List of duplicate finding dictionaries
        """
        findings = []
        
        for (concept, context), facts in duplicate_groups.items():
            finding = self._analyze_single_duplicate(concept, context, facts)
            findings.append(finding)
        
        return findings
    
    def _analyze_single_duplicate(
        self,
        concept: str,
        context: str,
        facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a single duplicate group.
        
        Args:
            concept: Concept identifier
            context: Context identifier
            facts: List of duplicate facts
            
        Returns:
            Duplicate finding dictionary
        """
        # Extract values
        values = self._extract_values(facts)
        unique_values = list(set(values))
        
        # Calculate variance if numeric
        variance_pct, max_variance = self._calculate_variance(values)
        
        # Classify severity
        severity = self._classify_severity(variance_pct, unique_values)
        
        return {
            'concept': concept,
            'context': context[:60] + '...' if len(context) > 60 else context,
            'full_context': context,
            'duplicate_count': len(facts),
            'unique_values': unique_values,
            'values': values,
            'variance_percentage': variance_pct,
            'max_variance_amount': max_variance,
            'severity': severity,
            'fact_ids': [f.get('fact_id', 'unknown') for f in facts],
            'decimals': [f.get('decimals', 'unknown') for f in facts],
            'units': [f.get('unit_ref', 'unknown') for f in facts]
        }
    
    def _extract_values(self, facts: List[Dict[str, Any]]) -> List[Any]:
        """
        Extract values from facts.
        
        Args:
            facts: List of fact dictionaries
            
        Returns:
            List of values
        """
        values = []
        for fact in facts:
            # Try multiple field names
            for field in ['fact_value', 'value', 'amount']:
                value = fact.get(field)
                if value is not None:
                    values.append(value)
                    break
        return values
    
    def _calculate_variance(
        self,
        values: List[Any]
    ) -> Tuple[float, float]:
        """
        Calculate variance between values.
        
        Args:
            values: List of values (may be numeric or non-numeric)
            
        Returns:
            Tuple of (variance_percentage, max_variance_amount)
        """
        # Try to convert to numeric
        numeric_values = []
        for val in values:
            try:
                if val is None or val == '':
                    continue
                numeric_val = Decimal(str(val))
                numeric_values.append(numeric_val)
            except (InvalidOperation, ValueError, TypeError):
                # Non-numeric value
                continue
        
        if len(numeric_values) < 2:
            # Can't calculate variance for non-numeric or single value
            return 0.0, 0.0
        
        # Calculate variance
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        variance_amount = abs(max_val - min_val)
        
        # Avoid division by zero
        if min_val == 0 and max_val == 0:
            return 0.0, 0.0
        
        # Calculate percentage variance relative to the larger absolute value
        base = max(abs(min_val), abs(max_val))
        if base == 0:
            return 0.0, float(variance_amount)
        
        variance_pct = float(variance_amount / base)
        
        return variance_pct, float(variance_amount)
    
    def _classify_severity(
        self,
        variance_pct: float,
        unique_values: List[Any]
    ) -> str:
        """
        Classify duplicate severity.
        
        Args:
            variance_pct: Variance percentage (0.0 to 1.0+)
            unique_values: List of unique values
            
        Returns:
            Severity level: CRITICAL, MAJOR, MINOR, or REDUNDANT
        """
        # If all values are identical -> REDUNDANT
        if len(unique_values) == 1:
            return SEVERITY_REDUNDANT
        
        # If non-numeric or zero variance -> MINOR
        if variance_pct == 0.0:
            return SEVERITY_MINOR
        
        # Classify by variance threshold
        if variance_pct >= CRITICAL_VARIANCE_THRESHOLD:
            return SEVERITY_CRITICAL
        elif variance_pct >= MAJOR_VARIANCE_THRESHOLD:
            return SEVERITY_MAJOR
        else:
            return SEVERITY_MINOR
    
    def _build_duplicate_report(
        self,
        findings: List[Dict[str, Any]],
        total_facts: int,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build comprehensive duplicate analysis report.
        
        Args:
            findings: List of duplicate findings
            total_facts: Total number of facts analyzed
            metadata: Filing metadata
            
        Returns:
            Duplicate report dictionary
        """
        # Count by severity
        severity_counts = self._count_by_severity(findings)
        
        # Separate findings by severity
        critical = [f for f in findings if f['severity'] == SEVERITY_CRITICAL]
        major = [f for f in findings if f['severity'] == SEVERITY_MAJOR]
        minor = [f for f in findings if f['severity'] == SEVERITY_MINOR]
        redundant = [f for f in findings if f['severity'] == SEVERITY_REDUNDANT]
        
        # Calculate statistics
        total_duplicates = len(findings)
        duplicate_facts_count = sum(f['duplicate_count'] for f in findings)
        
        return {
            'total_facts_analyzed': total_facts,
            'total_duplicate_groups': total_duplicates,
            'total_duplicate_facts': duplicate_facts_count,
            'duplicate_percentage': round(duplicate_facts_count / total_facts * 100, 2) if total_facts > 0 else 0.0,
            'severity_counts': severity_counts,
            'has_critical_duplicates': len(critical) > 0,
            'has_major_duplicates': len(major) > 0,
            'critical_findings': critical,
            'major_findings': major,
            'minor_findings': minor,
            'redundant_findings': redundant,
            'all_findings': findings,
            'filing_metadata': {
                'filing_id': metadata.get('filing_id', 'unknown'),
                'filing_date': metadata.get('filing_date', 'unknown')
            },
            'quality_assessment': self._generate_quality_assessment(severity_counts)
        }
    
    def _count_by_severity(
        self,
        findings: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Count findings by severity level.
        
        Args:
            findings: List of duplicate findings
            
        Returns:
            Dictionary mapping severity to count
        """
        counts = {
            SEVERITY_CRITICAL: 0,
            SEVERITY_MAJOR: 0,
            SEVERITY_MINOR: 0,
            SEVERITY_REDUNDANT: 0
        }
        
        for finding in findings:
            severity = finding['severity']
            counts[severity] = counts.get(severity, 0) + 1
        
        return counts
    
    def _generate_quality_assessment(
        self,
        severity_counts: Dict[str, int]
    ) -> str:
        """
        Generate overall quality assessment message.
        
        Args:
            severity_counts: Counts by severity level
            
        Returns:
            Quality assessment string
        """
        critical = severity_counts.get(SEVERITY_CRITICAL, 0)
        major = severity_counts.get(SEVERITY_MAJOR, 0)
        
        if critical > 0:
            return (
                f"SEVERE DATA INTEGRITY ISSUES: {critical} critical duplicate(s) with material variance. "
                "Filing may contain erroneous or fraudulent data. Recommend exclusion from analysis."
            )
        elif major > 0:
            return (
                f"SIGNIFICANT DATA QUALITY CONCERNS: {major} major duplicate(s) with notable variance. "
                "Manual review recommended before analysis."
            )
        elif severity_counts.get(SEVERITY_MINOR, 0) > 0:
            return "Minor duplicate variances detected - likely formatting or rounding differences."
        else:
            return "Harmless redundant duplicates only - no data integrity concerns."
    
    def _build_empty_report(self, total_facts: int) -> Dict[str, Any]:
        """
        Build empty report when no duplicates found.
        
        Args:
            total_facts: Total number of facts analyzed
            
        Returns:
            Empty duplicate report
        """
        return {
            'total_facts_analyzed': total_facts,
            'total_duplicate_groups': 0,
            'total_duplicate_facts': 0,
            'duplicate_percentage': 0.0,
            'severity_counts': {
                SEVERITY_CRITICAL: 0,
                SEVERITY_MAJOR: 0,
                SEVERITY_MINOR: 0,
                SEVERITY_REDUNDANT: 0
            },
            'has_critical_duplicates': False,
            'has_major_duplicates': False,
            'critical_findings': [],
            'major_findings': [],
            'minor_findings': [],
            'redundant_findings': [],
            'all_findings': [],
            'filing_metadata': {},
            'quality_assessment': 'No duplicates detected - clean XBRL filing.'
        }
    
    def _log_duplicate_summary(self, report: Dict[str, Any]) -> None:
        """
        Log summary of duplicate analysis.
        
        Args:
            report: Duplicate analysis report
        """
        total = report['total_duplicate_groups']
        
        if total == 0:
            self.logger.info("[OK] No duplicates found - clean source XBRL")
            return
        
        severity_counts = report['severity_counts']
        
        self.logger.warning(f"\n{'='*SEPARATOR_LENGTH}")
        self.logger.warning(f"DUPLICATE DETECTION SUMMARY")
        self.logger.warning(f"{'='*SEPARATOR_LENGTH}")
        self.logger.warning(f"Total duplicate groups found: {total}")
        self.logger.warning(f"  - CRITICAL (>5% variance): {severity_counts[SEVERITY_CRITICAL]}")
        self.logger.warning(f"  - MAJOR (1-5% variance): {severity_counts[SEVERITY_MAJOR]}")
        self.logger.warning(f"  - MINOR (<1% variance): {severity_counts[SEVERITY_MINOR]}")
        self.logger.warning(f"  - REDUNDANT (exact match): {severity_counts[SEVERITY_REDUNDANT]}")
        self.logger.warning(f"\nQuality Assessment:")
        self.logger.warning(f"  {report['quality_assessment']}")
        
        # Log critical findings in detail
        if report['has_critical_duplicates']:
            self.logger.error(f"\n{'='*SEPARATOR_LENGTH}")
            self.logger.error(f"[!] CRITICAL DUPLICATES DETECTED - DATA INTEGRITY ISSUES")
            self.logger.error(f"{'='*SEPARATOR_LENGTH}")
            
            for idx, finding in enumerate(report['critical_findings'][:MAX_DUPLICATES_DETAIL_LOG], 1):
                self.logger.error(
                    f"\n{idx}. Concept: {finding['concept']}\n"
                    f"   Context: {finding['context']}\n"
                    f"   Values: {finding['unique_values']}\n"
                    f"   Variance: {finding['variance_percentage']*100:.2f}% "
                    f"(${finding['max_variance_amount']:,.0f})\n"
                    f"   Severity: {finding['severity']}"
                )
        
        # Log major findings
        if report['has_major_duplicates']:
            self.logger.warning(f"\n{'='*SEPARATOR_LENGTH}")
            self.logger.warning(f"[!] MAJOR DUPLICATES - REVIEW RECOMMENDED")
            self.logger.warning(f"{'='*SEPARATOR_LENGTH}")
            
            for idx, finding in enumerate(report['major_findings'][:MAX_DUPLICATES_DETAIL_LOG], 1):
                self.logger.warning(
                    f"\n{idx}. Concept: {finding['concept']}\n"
                    f"   Context: {finding['context']}\n"
                    f"   Values: {finding['unique_values']}\n"
                    f"   Variance: {finding['variance_percentage']*100:.2f}%"
                )
        
        self.logger.warning(f"\n{'='*SEPARATOR_LENGTH}\n")


__all__ = ['DuplicateDetector']