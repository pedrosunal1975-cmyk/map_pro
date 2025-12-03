"""
File: engines/mapper/resolvers/__init__.py
Path: engines/mapper/resolvers/__init__.py

Concept Resolver Package
=========================

This package contains the concept resolution system that matches XBRL facts
to taxonomy concepts using an 8-strategy matching chain.

Modules:
    - concept_matcher: 8-strategy matching algorithm
    - concept_index_builder: Builds lookup indexes for fast matching
    - xsd_parser: Parses company XSD schemas for extension concepts
    - fact_filter: Filters non-mappable facts (metadata, DEI, etc.)
    - result_enricher: Enriches facts with taxonomy information
    - resolution_statistics: Tracks resolution statistics
    - text_utils: Text processing utilities
    - constants: Centralized constants and configuration

Architecture:
    The ConceptResolver class in the parent module (concept_resolver.py)
    orchestrates these components to resolve facts to taxonomy concepts.
"""

from engines.mapper.resolvers.concept_matcher import ConceptMatcher
from engines.mapper.resolvers.concept_index_builder import ConceptIndexBuilder
from engines.mapper.resolvers.xsd_parser import XSDParser
from engines.mapper.resolvers.fact_filter import FactFilter
from engines.mapper.resolvers.result_enricher import ResultEnricher
from engines.mapper.resolvers.resolution_statistics import ResolutionStatistics
from engines.mapper.resolvers.taxonomy_synonym_resolver import TaxonomySynonymResolver
from engines.mapper.resolvers.text_utils import generate_label_from_name, extract_words
from engines.mapper.resolvers.constants import (
    COMMON_PREFIXES,
    NON_MAPPABLE_NAMESPACES,
    NON_MAPPABLE_PATTERNS,
    FINANCIAL_MAPPINGS,
    SEMANTIC_SIMILARITY_THRESHOLD,
)

__all__ = [
    'ConceptMatcher',
    'ConceptIndexBuilder',
    'XSDParser',
    'FactFilter',
    'ResultEnricher',
    'ResolutionStatistics',
    'TaxonomySynonymResolver',  # ← ADD THIS
    'generate_label_from_name',
    'extract_words',
    'COMMON_PREFIXES',
    'NON_MAPPABLE_NAMESPACES',
    'NON_MAPPABLE_PATTERNS',
    'FINANCIAL_MAPPINGS',
    'SEMANTIC_SIMILARITY_THRESHOLD',
]