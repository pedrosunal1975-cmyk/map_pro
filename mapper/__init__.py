# File: /map_pro/engines/mapper/__init__.py

"""
Map Pro Mapper Engine
=====================

Universal fact-to-concept mapping engine.

Components:
- MappingCoordinator: Main engine coordinator (inherits BaseEngine)
- ConceptResolver: Maps facts to taxonomy concepts (8 strategies)
- FactMatcher: Categorizes facts into statement types
- StatementBuilder: Builds complete financial statements
- QualityAssessor: Assesses mapping quality
- SuccessCalculator: Calculates success metrics
- DataLoader: Handles all data loading and saving operations
- DuplicateDetector: Detects and analyzes duplicate facts in source XBRL

Usage:
    from engines.mapper import create_mapping_engine
    
    engine = create_mapping_engine()
    result = await engine.process_job({'filing_universal_id': filing_id})
"""

from .mapping_coordinator import MappingCoordinator, create_mapping_engine
from .concept_resolver import ConceptResolver
from .fact_matcher import FactMatcher
from .statement_builder import StatementBuilder
from .quality_assessor import QualityAssessor
from .success_calculator import SuccessCalculator
from .data_loader import DataLoader
from .analysis.duplicate_detector import DuplicateDetector  # Updated import path

__all__ = [
    'MappingCoordinator',
    'create_mapping_engine',
    'ConceptResolver',
    'FactMatcher',
    'StatementBuilder',
    'QualityAssessor',
    'SuccessCalculator',
    'DataLoader',
    'DuplicateDetector'
]

__version__ = '1.2.0'  # Updated version
__author__ = 'Map Pro Team'