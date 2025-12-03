"""
Duplicate Source Tracer
========================

Location: map_pro/engines/mapper/analysis/duplicate_source_tracer.py

Tracks the SOURCE of duplicate facts by comparing:
1. Parsed facts JSON (extraction from XBRL)
2. Mapper output

Provides breakdown of WHERE duplicates originate:
- SOURCE_DATA: Duplicates exist in parsed_facts.json (preserved from source)
- MAPPING_INTRODUCED: Mapper process created duplicates
- UNKNOWN: Cannot determine source

CRITICAL for "no mappable data is lost" principle - we need to know
if we're preserving source duplicates (correct) or creating new ones (incorrect).
"""

from typing import Dict, List, Tuple, Set, Any
from collections import defaultdict
from pathlib import Path
import json
from core.system_logger import get_logger
from .duplicate_constants import SOURCE_DATA, SOURCE_MAPPING, SOURCE_UNKNOWN
from .fact_extractor import extract_concept, extract_context
from .fact_grouper import find_duplicate_groups

logger = get_logger(__name__, 'engine')


class DuplicateSourceTracer:
    """
    Traces duplicate facts to their origin in the data pipeline.
    
    Responsibilities:
    - Compare parsed_facts.json vs mapper output
    - Identify where duplicates originate
    - Generate source attribution report
    
    Does NOT:
    - Modify any data
    - Make decisions about duplicate handling
    - Access database
    """
    
    def __init__(self):
        """Initialize duplicate source tracer."""
        self.logger = logger
        self.logger.debug("Duplicate source tracer initialized")
    
    def trace_duplicate_sources(
        self,
        parsed_facts_path: Path,
        duplicate_groups: Dict[Tuple[str, str], List[dict]]
    ) -> Dict[str, Any]:
        """
        Trace duplicate facts to their source.
        
        Strategy:
        Compare parsed_facts.json vs mapper output to determine if
        duplicates existed in source or were created by mapping.
        
        Args:
            parsed_facts_path: Path to parsed_facts.json
            duplicate_groups: Duplicate groups from mapper output
            
        Returns:
            Source attribution report
        """
        self.logger.debug(f"Tracing duplicate sources from {parsed_facts_path}")
        
        # Load source parsed facts
        source_facts = self._load_parsed_facts(parsed_facts_path)
        if not source_facts:
            self.logger.warning("Could not load source facts - source tracing unavailable")
            return self._build_unknown_report(duplicate_groups)
        
        # Find duplicates in source
        source_duplicate_groups = find_duplicate_groups(source_facts)
        
        # Compare mapper duplicates vs source duplicates
        source_attribution = self._compare_duplicates(
            duplicate_groups,
            source_duplicate_groups
        )
        
        # Build attribution report
        report = self._build_attribution_report(
            source_attribution,
            duplicate_groups
        )
        
        self.logger.debug(
            f"Source tracing complete: {report['source_breakdown']}"
        )
        
        return report
    
    def _load_parsed_facts(self, parsed_facts_path: Path) -> List[dict]:
        """
        Load parsed facts from JSON file.
        
        Args:
            parsed_facts_path: Path to parsed_facts.json
            
        Returns:
            List of facts or empty list if load fails
        """
        if not parsed_facts_path or not parsed_facts_path.exists():
            self.logger.warning(f"Parsed facts file not found: {parsed_facts_path}")
            return []
        
        try:
            with open(parsed_facts_path, 'r') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                facts = data
            elif isinstance(data, dict) and 'facts' in data:
                facts = data['facts']
            elif isinstance(data, dict) and 'parsed_facts' in data:
                facts = data['parsed_facts']
            else:
                self.logger.warning(f"Unknown parsed facts structure in {parsed_facts_path}")
                return []
            
            self.logger.debug(f"Loaded {len(facts)} source facts from {parsed_facts_path}")
            return facts
            
        except Exception as e:
            self.logger.error(f"Error loading parsed facts: {e}")
            return []
    
    def _compare_duplicates(
        self,
        mapper_duplicates: Dict[Tuple[str, str], List[dict]],
        source_duplicates: Dict[Tuple[str, str], List[dict]]
    ) -> Dict[Tuple[str, str], str]:
        """
        Compare mapper vs source duplicates to determine origin.
        
        Args:
            mapper_duplicates: Duplicates from mapper output
            source_duplicates: Duplicates from parsed_facts.json
            
        Returns:
            Dictionary mapping (concept, context) -> source classification
        """
        attribution = {}
        
        for key in mapper_duplicates.keys():
            if key in source_duplicates:
                # Duplicate exists in source data
                attribution[key] = SOURCE_DATA
            else:
                # Duplicate introduced by mapping
                attribution[key] = SOURCE_MAPPING
        
        return attribution
    
    def _build_attribution_report(
        self,
        source_attribution: Dict[Tuple[str, str], str],
        duplicate_groups: Dict[Tuple[str, str], List[dict]]
    ) -> Dict[str, Any]:
        """
        Build comprehensive source attribution report.
        
        Args:
            source_attribution: Attribution mapping
            duplicate_groups: Duplicate groups
            
        Returns:
            Attribution report dictionary
        """
        # Count by source
        source_counts = defaultdict(int)
        source_fact_counts = defaultdict(int)
        
        for key, source in source_attribution.items():
            source_counts[source] += 1
            source_fact_counts[source] += len(duplicate_groups[key])
        
        # Build breakdown
        source_breakdown = {
            SOURCE_DATA: source_fact_counts.get(SOURCE_DATA, 0),
            SOURCE_MAPPING: source_fact_counts.get(SOURCE_MAPPING, 0),
            SOURCE_UNKNOWN: source_fact_counts.get(SOURCE_UNKNOWN, 0)
        }
        
        # Build detailed attribution
        source_details = []
        for (concept, context), source in source_attribution.items():
            source_details.append({
                'concept': concept,
                'context': context,
                'source': source,
                'fact_count': len(duplicate_groups[(concept, context)])
            })
        
        return {
            'source_breakdown': source_breakdown,
            'source_group_counts': dict(source_counts),
            'source_details': source_details,
            'total_groups_traced': len(source_attribution)
        }
    
    def _build_unknown_report(
        self,
        duplicate_groups: Dict[Tuple[str, str], List[dict]]
    ) -> Dict[str, Any]:
        """
        Build report when source cannot be traced.
        
        Args:
            duplicate_groups: Duplicate groups
            
        Returns:
            Report with SOURCE_UNKNOWN for all duplicates
        """
        total_facts = sum(len(facts) for facts in duplicate_groups.values())
        
        return {
            'source_breakdown': {
                SOURCE_DATA: 0,
                SOURCE_MAPPING: 0,
                SOURCE_UNKNOWN: total_facts
            },
            'source_group_counts': {
                SOURCE_UNKNOWN: len(duplicate_groups)
            },
            'source_details': [],
            'total_groups_traced': 0,
            'warning': 'Source facts unavailable - could not trace duplicate origins'
        }


__all__ = ['DuplicateSourceTracer']