"""
Map Pro Markets Base Module
===========================

Base framework for market-specific plugins.
Provides abstract interface and common utilities for all market implementations.

Components:
- MarketInterface: Abstract base class for market plugins
- ErrorClassifier: Error classification and retry logic
- SuccessEvaluator: Quality and success evaluation
- WorkflowExecutor: Workflow execution with retry and rate limiting

Architecture:
- Abstract interfaces define contracts
- Utility components provide common functionality
- Markets inherit and implement required methods
- No market-specific logic in base module

Usage:
    from markets.base import MarketInterface, ErrorCategory, SuccessLevel
    
    class SECSearcher(MarketInterface):
        def __init__(self):
            super().__init__('sec')
        
        async def search_company(self, company_identifier: str):
            # SEC-specific implementation
            pass
"""

from .market_interface import MarketInterface
from .error_classifier import (
    ErrorClassifier,
    ErrorCategory,
    error_classifier,
    classify_http_error,
    classify_exception,
    is_retryable_error,
    get_retry_delay
)
from .success_evaluator import (
    SuccessEvaluator,
    SuccessLevel,
    success_evaluator,
    evaluate_company_search,
    evaluate_filing_discovery,
    is_acceptable_result
)
from .workflow_executor import WorkflowExecutor

__all__ = [
    # Main interface
    'MarketInterface',
    
    # Error handling
    'ErrorClassifier',
    'ErrorCategory',
    'error_classifier',
    'classify_http_error',
    'classify_exception',
    'is_retryable_error',
    'get_retry_delay',
    
    # Success evaluation
    'SuccessEvaluator',
    'SuccessLevel',
    'success_evaluator',
    'evaluate_company_search',
    'evaluate_filing_discovery',
    'is_acceptable_result',
    
    # Workflow execution
    'WorkflowExecutor',
]

__version__ = '1.0.0'
__author__ = 'Map Pro Team'