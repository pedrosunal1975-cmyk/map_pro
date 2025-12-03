# File: /map_pro/engines/mapper/concept_resolver.py

"""
Map Pro Concept Resolver - Main Orchestrator
==============================================

Main entry point for concept resolution. Coordinates between matcher strategies,
XSD parsing, and result enrichment. This is the primary interface used by the
mapping coordinator.

ULTRA-FLOODGATE UPDATE (2025-11-20):
- Removed ALL filtering except pointer references
- All facts (dei, srt, country, currency, naics, sic, etc.) now go through taxonomy mapping
- Only pointer references (ExtensibleList/Enumeration) are excluded
- Simplified logic: mappable facts get mapped, pointer references get marked as excluded

Architecture:
    - Delegates matching to ConceptMatcher (8-strategy chain)
    - Delegates XSD parsing to XSDParser
    - Delegates concept indexing to ConceptIndexBuilder
    - No namespace filtering (all namespaces are mapped)
    - All facts get full taxonomy mapping with proper labels
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from core.system_logger import get_logger
from engines.mapper.resolvers.concept_matcher import ConceptMatcher
from engines.mapper.resolvers.xsd_parser import XSDParser
from engines.mapper.resolvers.concept_index_builder import ConceptIndexBuilder
from engines.mapper.resolvers.fact_filter import FactFilter
from engines.mapper.resolvers.result_enricher import ResultEnricher
from engines.mapper.resolvers.resolution_statistics import ResolutionStatistics
from engines.mapper.resolvers.taxonomy_synonym_resolver import TaxonomySynonymResolver


logger = get_logger(__name__, 'engine')


class ConceptResolver:
    """
    Universal concept resolver utilizing the robust 8-Strategy Chain.
    
    ULTRA-FLOODGATE UPDATE: Maps ALL facts (all namespaces).
    Only excludes pointer references (ExtensibleList/Enumeration).
    
    This class orchestrates the entire concept resolution process:
    1. Build lookup indexes from taxonomy concepts
    2. Filter only pointer references (ExtensibleList/Enumeration)
    3. Resolve ALL OTHER facts using the 8-strategy matching chain
    4. Enrich resolved facts with taxonomy information
    5. Track and report resolution statistics
    
    The resolver is stateless between runs - call resolve_facts() for each
    new batch of facts to resolve.
    """
    
    # ============================================================================
    # MODIFIED __init__ METHOD
    # ============================================================================

    def __init__(self):
        """Initialize concept resolver with all required components."""
        self.logger = logger
        
        # Initialize sub-components
        self.index_builder = ConceptIndexBuilder()
        self.fact_filter = FactFilter()
        self.synonym_resolver = TaxonomySynonymResolver()  # NEW: Synonym resolver
        self.matcher = ConceptMatcher(self.index_builder, self.synonym_resolver)  # MODIFIED: Pass synonym_resolver
        self.enricher = ResultEnricher()
        self.statistics = ResolutionStatistics()
        self.xsd_parser = XSDParser()
        
        self.logger.info("Concept resolver initialized (ULTRA-FLOODGATE: mapping ALL facts, all namespaces)")


    # ============================================================================
    # MODIFIED resolve_facts METHOD
    # ============================================================================

    def resolve_facts(
        self,
        facts: List[Dict[str, Any]],
        concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Resolve all facts to taxonomy concepts.
        
        ULTRA-FLOODGATE UPDATE: Maps everything except pointer references.
        
        Main entry point for the resolution process. Handles:
        - Building lookup indexes from taxonomy concepts
        - Building synonym mappings from taxonomy relationships
        - Filtering only pointer references (ExtensibleList/Enumeration)
        - Resolving ALL OTHER facts to taxonomy concepts (all namespaces)
        - Enriching results with taxonomy information
        - Collecting and reporting statistics
        
        Args:
            facts: List of fact dictionaries to resolve
            concepts: List of taxonomy concept dictionaries to match against
            
        Returns:
            List of resolved fact dictionaries:
            - Resolved facts (with taxonomy_concept, taxonomy_label, mapping_method, etc.)
            - Excluded pointer references (marked with is_pointer_reference=True)
        """
        # Reset statistics for new resolution run
        self.statistics.reset()
        
        # Build lookup indexes from taxonomy concepts
        self.index_builder.build_lookups(concepts)
        
        # Build synonym mappings from taxonomy concepts (NEW)
        self.synonym_resolver.build_synonym_map(concepts)
        
        resolved_facts = []
        pointer_facts = []
        
        # Process each fact
        for fact in facts:
            # Filter ONLY pointer references (ExtensibleList/Enumeration)
            if not self.fact_filter.is_mappable_fact(fact):
                pointer_fact = self._mark_as_pointer_reference(fact)
                pointer_facts.append(pointer_fact)
                continue
            
            # Resolve ALL other facts (all namespaces: dei, srt, country, currency, etc.)
            resolved_fact = self._resolve_single_fact(fact)
            resolved_facts.append(resolved_fact)
        
        # Calculate and log final statistics
        self._log_resolution_summary(pointer_facts)
        
        # Return both resolved and pointer reference facts
        return resolved_facts + pointer_facts
    
    def _resolve_single_fact(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve a single fact using the 8-strategy matching chain.
        
        Delegates the actual matching to ConceptMatcher, then enriches
        the result with taxonomy information or marks it as unmapped.
        
        Args:
            fact: Fact dictionary to resolve
            
        Returns:
            Resolved fact dictionary with taxonomy information
        """
        self.statistics.increment_total_resolved()
        
        # Delegate to matcher for concept resolution
        match_result = self.matcher.resolve_fact(fact, self.statistics)
        
        if match_result:
            concept, confidence, method_name = match_result
            return self.enricher.enrich_fact(fact, concept, confidence, method_name)
        else:
            return self.enricher.mark_unmapped(fact, "No matching strategy succeeded", self.statistics)
    
    def _mark_as_pointer_reference(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mark a fact as a pointer reference (ExtensibleList/Enumeration).
        
        These facts are URLs/references to other concepts, not actual data values.
        They're excluded because they don't represent meaningful financial information.
        
        Args:
            fact: Fact dictionary to mark as pointer reference
            
        Returns:
            Fact dictionary with pointer reference markers
        """
        pointer_fact = fact.copy()
        pointer_fact.update({
            'is_pointer_reference': True,
            'is_unmapped': False,
            'mapping_method': 'pointer_reference_excluded',
            'mapping_reason': 'Pointer reference (ExtensibleList/Enumeration URL)'
        })
        return pointer_fact
    
    def _log_resolution_summary(self, pointer_facts: List[Dict[str, Any]]) -> None:
        """
        Log summary statistics for the resolution run.
        
        Args:
            pointer_facts: List of facts excluded as pointer references
        """
        stats = self.statistics.get_statistics()
        mapped = stats['total_resolved'] - stats['unmapped']
        total = stats['total_resolved']
        mapping_rate = (mapped / total * 100) if total else 0.0
        
        self.logger.info(
            f"Resolution complete: {mapped}/{total} facts mapped ({mapping_rate:.1f}%)"
        )
        self.logger.info(
            f"Excluded {len(pointer_facts)} pointer reference facts (ExtensibleList/Enumeration)"
        )
    
    def parse_company_xsd_file(self, xsd_path: Path) -> List[Dict[str, Any]]:
        """
        Parse company XSD file for extension concepts.
        
        Delegates to XSDParser for actual parsing logic.
        
        Args:
            xsd_path: Path to company XSD file
            
        Returns:
            List of concept dictionaries extracted from XSD
        """
        return self.xsd_parser.parse_company_xsd_file(xsd_path)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get resolution statistics for the current/last run.
        
        Returns:
            Dictionary containing resolution statistics
        """
        return self.statistics.get_statistics()


__all__ = ['ConceptResolver']