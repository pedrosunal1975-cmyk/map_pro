"""
Map Pro Parser Engine
====================

Universal XBRL parser engine for all markets.

Components:
- ParserCoordinator: Main engine inheriting from BaseEngine
- ArelleController: Arelle lifecycle management
- FactExtractor: Universal fact extraction
- ContextProcessor: Context/period processing
- OutputFormatter: JSON output creation
- ValidationEngine: XBRL validation

Architecture: Market-agnostic parsing - handles XBRL from all regulatory markets.

Location: /map_pro/engines/parser/__init__.py
"""

from .parser_coordinator import ParserCoordinator, create_parser_engine
from .arelle_controller import ArelleController, get_arelle_info, ARELLE_AVAILABLE
from .fact_extractor import FactExtractor, extract_numeric_value
from .context_processor import ContextProcessor
from .output_formatter import OutputFormatter
from .validation_engine import ValidationEngine

__all__ = [
    'ParserCoordinator',
    'create_parser_engine',
    'ArelleController',
    'get_arelle_info',
    'ARELLE_AVAILABLE',
    'FactExtractor',
    'extract_numeric_value',
    'ContextProcessor',
    'OutputFormatter',
    'ValidationEngine'
]