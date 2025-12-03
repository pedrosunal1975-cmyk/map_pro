# File: engines/mapper/loaders/taxonomy_fallback_provider.py
"""
Taxonomy Fallback Provider
===========================

Provides essential fallback taxonomy concepts when database and filesystem fail.

Responsibilities:
- Create hardcoded essential concepts
- Provide minimal working taxonomy
- Ensure system can operate with basic concepts
"""

from typing import Dict, Any, List, Optional

from core.system_logger import get_logger
from .taxonomy_constants import (
    FASB_NAMESPACE_TEMPLATE,
    SEC_DEI_NAMESPACE,
    PERIOD_TYPE_DURATION,
    PERIOD_TYPE_INSTANT,
    BALANCE_TYPE_DEBIT,
    BALANCE_TYPE_CREDIT
)

logger = get_logger(__name__, 'engine')


class TaxonomyFallbackProvider:
    """
    Provides fallback taxonomy concepts.
    
    Creates a minimal set of essential concepts for basic operation
    when database and filesystem sources are unavailable.
    
    Attributes:
        logger: System logger instance
    """
    
    def __init__(self) -> None:
        """Initialize fallback provider."""
        self.logger = logger
    
    def get_fallback_concepts(self) -> List[Dict[str, Any]]:
        """
        Create and return basic fallback taxonomy concepts.
        
        Returns:
            List of essential concept dictionaries for basic operation
        """
        fallback_concepts = [
            # Income Statement Concepts
            self._create_concept(
                'us-gaap', 'Revenues', 'monetary', 'Revenues',
                PERIOD_TYPE_DURATION, BALANCE_TYPE_CREDIT, False
            ),
            self._create_concept(
                'us-gaap', 'NetIncomeLoss', 'monetary', 'Net Income (Loss)',
                PERIOD_TYPE_DURATION, BALANCE_TYPE_CREDIT, False
            ),
            self._create_concept(
                'us-gaap', 'CostOfRevenue', 'monetary', 'Cost of Revenue',
                PERIOD_TYPE_DURATION, BALANCE_TYPE_DEBIT, False
            ),
            self._create_concept(
                'us-gaap', 'OperatingIncomeLoss', 'monetary',
                'Operating Income (Loss)',
                PERIOD_TYPE_DURATION, BALANCE_TYPE_CREDIT, False
            ),
            
            # Balance Sheet Concepts
            self._create_concept(
                'us-gaap', 'Assets', 'monetary', 'Assets',
                PERIOD_TYPE_INSTANT, BALANCE_TYPE_DEBIT, False
            ),
            self._create_concept(
                'us-gaap', 'Liabilities', 'monetary', 'Liabilities',
                PERIOD_TYPE_INSTANT, BALANCE_TYPE_CREDIT, False
            ),
            self._create_concept(
                'us-gaap', 'StockholdersEquity', 'monetary',
                'Stockholders Equity',
                PERIOD_TYPE_INSTANT, BALANCE_TYPE_CREDIT, False
            ),
            self._create_concept(
                'us-gaap', 'CashAndCashEquivalentsAtCarryingValue',
                'monetary', 'Cash and Cash Equivalents',
                PERIOD_TYPE_INSTANT, BALANCE_TYPE_DEBIT, False
            ),
            
            # Document and Entity Information
            self._create_concept(
                'dei', 'EntityRegistrantName', 'string',
                'Entity Registrant Name',
                PERIOD_TYPE_DURATION, None, False
            ),
            self._create_concept(
                'dei', 'DocumentFiscalYearFocus', 'string',
                'Document Fiscal Year Focus',
                PERIOD_TYPE_DURATION, None, False
            ),
        ]
        
        self.logger.info(
            "Created %d fallback concepts",
            len(fallback_concepts)
        )
        
        return fallback_concepts
    
    def _create_concept(
        self,
        prefix: str,
        local_name: str,
        concept_type: str,
        label: str,
        period_type: str,
        balance_type: Optional[str] = None,
        is_abstract: bool = False
    ) -> Dict[str, Any]:
        """
        Create a single fallback concept dictionary.
        
        Args:
            prefix: Taxonomy prefix (e.g., 'us-gaap', 'dei')
            local_name: Local concept name
            concept_type: Type (monetary, string, etc.)
            label: Human-readable label
            period_type: Period type (instant/duration)
            balance_type: Balance type (debit/credit) or None
            is_abstract: Whether concept is abstract
            
        Returns:
            Concept dictionary with standardized keys
        """
        namespace = self._get_namespace_for_prefix(prefix)
        
        return {
            'concept_qname': f"{prefix}:{local_name}",
            'concept_local_name': local_name,
            'concept_namespace': namespace,
            'concept_type': concept_type,
            'concept_label': label,
            'period_type': period_type,
            'balance_type': balance_type,
            'is_abstract': is_abstract,
            'is_extension': False
        }
    
    def _get_namespace_for_prefix(self, prefix: str) -> str:
        """
        Get namespace URI for taxonomy prefix.
        
        Args:
            prefix: Taxonomy prefix
            
        Returns:
            Full namespace URI
            
        Note:
            This is a fallback implementation using US market defaults.
            Market-specific implementations should provide proper namespace configuration.
        """
        # DEI namespace varies by market:
        # - SEC (US): http://xbrl.sec.gov/dei/2023
        # - FCA (UK): varies by reporting framework
        # - ESMA (EU): http://www.esma.europa.eu/xbrl/esef/...
        # Using SEC as fallback for backward compatibility
        if prefix == 'dei':
            self.logger.debug(
                "Using US market default namespace for 'dei' prefix. "
                "Market-specific configuration recommended."
            )
            return SEC_DEI_NAMESPACE
        return FASB_NAMESPACE_TEMPLATE.format(prefix)


__all__ = ['TaxonomyFallbackProvider']