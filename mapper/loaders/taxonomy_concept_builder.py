# File: engines/mapper/loaders/taxonomy_concept_builder.py
"""
Taxonomy Concept Builder
=========================

Builds concept dictionaries from XSD element definitions.

Responsibilities:
- Extract attributes from XSD elements
- Normalize XSD types
- Generate concept labels
- Create standardized concept dictionaries
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from .taxonomy_constants import (
    XSD_ATTR_NAME,
    XSD_ATTR_TYPE,
    XSD_ATTR_PERIOD_TYPE,
    XSD_ATTR_BALANCE,
    XSD_ATTR_ABSTRACT,
    DEFAULT_TYPE,
    DEFAULT_PERIOD_TYPE,
    XBRL_PERIOD_TYPE_ATTR,
    XBRL_BALANCE_ATTR,
    BOOLEAN_TRUE,
    BOOLEAN_FALSE,
    FASB_NAMESPACE_TEMPLATE,
    MONETARY_TYPES,
    DATE_TYPES,
    PERCENT_TYPES,
    BOOLEAN_TYPES,
    SHARES_TYPES,
    CAMELCASE_SPLIT_PATTERN_LOWER_UPPER,
    CAMELCASE_SPLIT_PATTERN_CONSECUTIVE,
    CAMELCASE_REPLACEMENT,
    CONCEPT_QNAME_SEPARATOR
)

logger = get_logger(__name__, 'engine')


class TaxonomyConceptBuilder:
    """
    Builds concept dictionaries from XSD elements.
    
    Attributes:
        logger: System logger instance
    """
    
    def __init__(self) -> None:
        """Initialize concept builder."""
        self.logger = logger
    
    def build_concept(
        self,
        element: ET.Element,
        taxonomy_prefix: str
    ) -> Dict[str, Any]:
        """
        Create concept dictionary from XSD element.
        
        Args:
            element: XML element from XSD
            taxonomy_prefix: Taxonomy prefix (e.g., 'us-gaap')
            
        Returns:
            Concept dictionary with standardized keys
        """
        name = element.get(XSD_ATTR_NAME)
        xsd_type = element.get(XSD_ATTR_TYPE, DEFAULT_TYPE)
        period_type = element.get(XBRL_PERIOD_TYPE_ATTR, DEFAULT_PERIOD_TYPE)
        balance_type = element.get(XBRL_BALANCE_ATTR)
        is_abstract = self._parse_abstract_attribute(element)
        
        return {
            'concept_qname': self._build_qname(taxonomy_prefix, name),
            'concept_local_name': name,
            'concept_namespace': FASB_NAMESPACE_TEMPLATE.format(taxonomy_prefix),
            'concept_type': self._normalize_type(xsd_type),
            'concept_label': self._generate_label(name),
            'period_type': period_type,
            'balance_type': balance_type,
            'is_abstract': is_abstract,
            'is_extension': False
        }
    
    def _build_qname(self, prefix: str, local_name: str) -> str:
        """
        Build qualified name from prefix and local name.
        
        Args:
            prefix: Namespace prefix
            local_name: Local concept name
            
        Returns:
            Qualified name (e.g., 'us-gaap:Assets')
        """
        return f"{prefix}{CONCEPT_QNAME_SEPARATOR}{local_name}"
    
    def _parse_abstract_attribute(self, element: ET.Element) -> bool:
        """
        Parse abstract attribute from element.
        
        Args:
            element: XML element
            
        Returns:
            True if element is abstract, False otherwise
        """
        abstract_value = element.get(XSD_ATTR_ABSTRACT, BOOLEAN_FALSE)
        return abstract_value.lower() == BOOLEAN_TRUE
    
    def _normalize_type(self, xsd_type: str) -> str:
        """
        Normalize XSD type to simple category.
        
        Args:
            xsd_type: XSD type string (e.g., 'xbrli:monetaryItemType')
            
        Returns:
            Normalized type (monetary, string, boolean, etc.)
        """
        if not xsd_type:
            return DEFAULT_TYPE
        
        type_lower = xsd_type.lower()
        
        if self._is_monetary_type(type_lower):
            return 'monetary'
        elif self._is_boolean_type(type_lower):
            return 'boolean'
        elif self._is_date_type(type_lower):
            return 'date'
        elif self._is_percent_type(type_lower):
            return 'percent'
        elif self._is_shares_type(type_lower):
            return 'shares'
        
        return DEFAULT_TYPE
    
    def _is_monetary_type(self, type_str: str) -> bool:
        """Check if type string indicates monetary type."""
        return any(monetary_type in type_str for monetary_type in MONETARY_TYPES)
    
    def _is_boolean_type(self, type_str: str) -> bool:
        """Check if type string indicates boolean type."""
        return any(boolean_type in type_str for boolean_type in BOOLEAN_TYPES)
    
    def _is_date_type(self, type_str: str) -> bool:
        """Check if type string indicates date type."""
        return any(date_type in type_str for date_type in DATE_TYPES)
    
    def _is_percent_type(self, type_str: str) -> bool:
        """Check if type string indicates percent type."""
        return any(percent_type in type_str for percent_type in PERCENT_TYPES)
    
    def _is_shares_type(self, type_str: str) -> bool:
        """Check if type string indicates shares type."""
        return any(shares_type in type_str for shares_type in SHARES_TYPES)
    
    def _generate_label(self, concept_name: str) -> str:
        """
        Generate readable label from CamelCase concept name.
        
        Args:
            concept_name: CamelCase concept name
            
        Returns:
            Human-readable label with spaces
        """
        if not concept_name:
            return ''
        
        # Add spaces before capital letters
        with_spaces = re.sub(CAMELCASE_SPLIT_PATTERN_LOWER_UPPER, CAMELCASE_REPLACEMENT, concept_name)
        with_spaces = re.sub(CAMELCASE_SPLIT_PATTERN_CONSECUTIVE, CAMELCASE_REPLACEMENT, with_spaces)
        
        return with_spaces.strip()


__all__ = ['TaxonomyConceptBuilder']