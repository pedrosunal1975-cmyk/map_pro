# Path: mapping/statement/fact_extractor.py
"""
Fact Extractor

Extracts facts from parsed filing according to presentation hierarchy.
Handles QName normalization and hierarchical traversal.
"""

import logging
from typing import Optional
from collections import defaultdict

from ...loaders.parser_output import ParsedFiling
from ...components.qname_utils import QNameUtils
from ...mapping.statement.models import StatementFact
from ...mapping.statement.fact_enricher import FactEnricher


class FactExtractor:
    """
    Extracts facts following presentation hierarchy order.
    
    Responsibilities:
    - Build concept-to-facts mapping with normalized QNames
    - Traverse hierarchy depth-first
    - Extract facts in presentation order
    - Handle parent-child relationships
    """
    
    def __init__(self, get_attr_func):
        """
        Initialize fact extractor.
        
        Args:
            get_attr_func: Function to safely get attributes from data objects
        """
        self.logger = logging.getLogger('mapping.fact_extractor')
        self._get_attr = get_attr_func
        self.fact_enricher = FactEnricher()  # Initialize enricher
    
    def extract_facts_in_order(
        self,
        hierarchy: dict[str, any],
        parsed_filing: ParsedFiling,
        role_uri: str
    ) -> list[StatementFact]:
        """
        Extract facts following hierarchy order.
        
        Uses normalized concept name matching (local names) to handle
        QName variations (us-gaap:Assets vs Assets vs us-gaap_Assets).
        
        Args:
            hierarchy: Hierarchy structure with roots, children, parents, order
            parsed_filing: Parsed filing with facts
            role_uri: Role URI for this statement
            
        Returns:
            List of StatementFacts in hierarchical order
        """
        statement_facts = []
        
        # DEBUG logging
        self.logger.warning(f"DEBUG: Starting fact extraction for role: {role_uri}")
        self.logger.warning(f"DEBUG: Total facts in filing: {len(parsed_filing.facts)}")
        
        # Sample a few facts to see their format
        if parsed_filing.facts:
            sample_facts = parsed_filing.facts[:3]
            self.logger.warning("DEBUG: Sample fact concepts:")
            for i, fact in enumerate(sample_facts, 1):
                concept_name = self._get_attr(fact, 'name')
                self.logger.warning(f"  {i}. '{concept_name}' (type: {type(concept_name)})")
        
        # Build concept-to-facts map with normalized local names
        concept_facts_map = self._build_concept_facts_map(parsed_filing)
        
        self.logger.warning(
            f"DEBUG: Built concept map: {len(concept_facts_map)} unique local names "
            f"from {len(parsed_filing.facts)} facts"
        )
        
        if concept_facts_map:
            sample_keys = list(concept_facts_map.keys())[:5]
            self.logger.warning(f"DEBUG: Sample concept map keys: {sample_keys}")
        else:
            self.logger.error("DEBUG: CRITICAL - concept_facts_map is EMPTY!")
        
        # DEBUG hierarchy
        if hierarchy['roots']:
            self.logger.warning(f"DEBUG: Hierarchy has {len(hierarchy['roots'])} roots")
            sample_roots = hierarchy['roots'][:3]
            self.logger.warning(f"DEBUG: Sample hierarchy roots: {sample_roots}")
        
        # Traverse hierarchy depth-first
        visited = set()
        
        for root in hierarchy['roots']:
            self._traverse_and_extract(
                root,
                hierarchy,
                concept_facts_map,
                parsed_filing,
                statement_facts,
                visited,
                level=0,
                parent=None
            )
        
        self.logger.warning(
            f"DEBUG: Extracted {len(statement_facts)} facts for this statement"
        )
        
        # ENRICH facts with calculated values for verification
        enriched_facts = []
        for fact in statement_facts:
            enriched_fact = self.fact_enricher.enrich_fact(fact)
            enriched_facts.append(enriched_fact)
        
        self.logger.info(f"Enriched {len(enriched_facts)} facts with calculated values")
        
        return enriched_facts
    
    def _build_concept_facts_map(self, parsed_filing: ParsedFiling) -> dict[str, list]:
        """
        Build map from normalized concept names to facts.
        
        Normalizes QNames to local names for matching:
        - us-gaap:Assets -> Assets
        - us-gaap_Assets -> Assets
        - Assets -> Assets
        
        Args:
            parsed_filing: Parsed filing with facts
            
        Returns:
            Dictionary mapping local concept names to lists of facts
        """
        concept_facts_map = defaultdict(list)
        
        for fact in parsed_filing.facts:
            concept_name = self._get_attr(fact, 'name')
            if concept_name:
                try:
                    local_name = QNameUtils.get_local_name(concept_name)
                    concept_facts_map[local_name].append(fact)
                except Exception as e:
                    self.logger.warning(
                        f"DEBUG: Failed to normalize concept '{concept_name}': {e}"
                    )
        
        return concept_facts_map
    
    def _traverse_and_extract(
        self,
        concept: str,
        hierarchy: dict[str, any],
        concept_facts_map: dict[str, list],
        parsed_filing: ParsedFiling,
        statement_facts: list[StatementFact],
        visited: set[str],
        level: int,
        parent: Optional[str]
    ):
        """
        Recursively traverse hierarchy and extract facts.
        
        Uses normalized concept matching (local names only).
        
        Args:
            concept: Current concept to process (from hierarchy)
            hierarchy: Hierarchy structure
            concept_facts_map: Map from LOCAL NAMES to their facts
            parsed_filing: Parsed filing
            statement_facts: List to append facts to (modified in place)
            visited: Set of visited concepts (prevents loops)
            level: Current hierarchy level (depth)
            parent: Parent concept
        """
        if concept in visited:
            return
        
        visited.add(concept)
        
        # Normalize concept to local name for lookup
        concept_local = QNameUtils.get_local_name(concept)
        
        # Get facts for this concept using normalized name
        facts = concept_facts_map.get(concept_local, [])
        
        if facts:
            self.logger.debug(
                f"Matched {len(facts)} facts for concept '{concept}' "
                f"(normalized to '{concept_local}')"
            )
        
        # Get order for this concept
        order = hierarchy['order'].get(concept, 0)
        
        # Add facts to statement
        for fact in facts:
            statement_fact = StatementFact(
                concept=concept,  # Keep original concept from hierarchy
                value=self._get_attr(fact, 'value'),
                context_ref=self._get_attr(fact, 'context_ref'),
                unit_ref=self._get_attr(fact, 'unit_ref'),
                decimals=self._get_attr(fact, 'decimals'),
                precision=self._get_attr(fact, 'precision'),
                order=order,
                level=level,
                parent_concept=parent,
                metadata={}
            )
            statement_facts.append(statement_fact)
        
        # Recursively process children
        children = hierarchy['children'].get(concept, [])
        
        # Sort children by order
        children_with_order = [
            (child, hierarchy['order'].get(child, 0))
            for child in children
        ]
        children_with_order.sort(key=lambda x: x[1])
        
        for child, _ in children_with_order:
            self._traverse_and_extract(
                child,
                hierarchy,
                concept_facts_map,
                parsed_filing,
                statement_facts,
                visited,
                level + 1,
                concept
            )