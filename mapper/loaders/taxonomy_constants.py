# File: engines/mapper/loaders/taxonomy_constants.py
"""
Taxonomy Constants
==================

Centralized constants for taxonomy loading operations.
Eliminates magic numbers and strings throughout the taxonomy subsystem.
"""

# Database Constants
DEFAULT_LIBRARY_STATUS = 'active'

# Namespace Constants
# NOTE: SEC_DEI_NAMESPACE is a fallback default for US markets only.
# Market-specific namespaces should be configured in market plugins or taxonomy config.
# This constant is kept for backward compatibility with existing code.
FASB_NAMESPACE_TEMPLATE = "http://fasb.org/{}/2023"
SEC_DEI_NAMESPACE = "http://xbrl.sec.gov/dei/2023"  # US market default fallback
XSD_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'
XBRL_INSTANCE_NAMESPACE = 'http://www.xbrl.org/2003/instance'

# XSD Namespace Mapping
XSD_NS_MAP = {'xs': XSD_NAMESPACE}

# Default Libraries
DEFAULT_LIBRARIES = ['us-gaap-2024', 'dei-2024', 'srt-2024']

# Standard Taxonomy Prefixes
STANDARD_TAXONOMIES = ['us-gaap', 'dei', 'srt', 'ifrs']

# Type Category Mappings
MONETARY_TYPES = ['monetary', 'decimal', 'integer', 'float']
DATE_TYPES = ['date', 'time']
PERCENT_TYPES = ['percent', 'ratio']
BOOLEAN_TYPES = ['boolean']
SHARES_TYPES = ['shares']

# XSD Attribute Names
XSD_ATTR_NAME = 'name'
XSD_ATTR_TYPE = 'type'
XSD_ATTR_PERIOD_TYPE = 'periodType'
XSD_ATTR_BALANCE = 'balance'
XSD_ATTR_ABSTRACT = 'abstract'

# XBRL Attribute Names (with namespace)
XBRL_PERIOD_TYPE_ATTR = f'{{{XBRL_INSTANCE_NAMESPACE}}}periodType'
XBRL_BALANCE_ATTR = f'{{{XBRL_INSTANCE_NAMESPACE}}}balance'

# XSD Element Paths
XSD_ELEMENT_PATH = './/xs:element[@name]'

# Default Type Values
DEFAULT_TYPE = 'string'
DEFAULT_PERIOD_TYPE = 'duration'

# Boolean String Values
BOOLEAN_TRUE = 'true'
BOOLEAN_FALSE = 'false'

# Period Types
PERIOD_TYPE_INSTANT = 'instant'
PERIOD_TYPE_DURATION = 'duration'

# Balance Types
BALANCE_TYPE_DEBIT = 'debit'
BALANCE_TYPE_CREDIT = 'credit'

# Namespace Mapping for Library Discovery
NAMESPACE_TO_LIBRARY_MAP = {
    'gaap': 'us-gaap',
    'us-gaap': 'us-gaap',
    'dei': 'dei',
    'srt': 'srt',
    'ifrs': 'ifrs'
}

# Directory Names
LIBRARIES_DIR_NAME = 'libraries'

# File Patterns
XSD_FILE_PATTERN = '*.xsd'

# Concept Separator
CONCEPT_QNAME_SEPARATOR = ':'

# Regex Patterns (pre-compiled for performance would be even better)
CAMELCASE_SPLIT_PATTERN_LOWER_UPPER = r'([a-z])([A-Z])'
CAMELCASE_SPLIT_PATTERN_CONSECUTIVE = r'([A-Z])([A-Z][a-z])'
CAMELCASE_REPLACEMENT = r'\1 \2'


__all__ = [
    'DEFAULT_LIBRARY_STATUS',
    'FASB_NAMESPACE_TEMPLATE',
    'SEC_DEI_NAMESPACE',
    'XSD_NAMESPACE',
    'XBRL_INSTANCE_NAMESPACE',
    'XSD_NS_MAP',
    'DEFAULT_LIBRARIES',
    'STANDARD_TAXONOMIES',
    'MONETARY_TYPES',
    'DATE_TYPES',
    'PERCENT_TYPES',
    'BOOLEAN_TYPES',
    'SHARES_TYPES',
    'XSD_ATTR_NAME',
    'XSD_ATTR_TYPE',
    'XSD_ATTR_PERIOD_TYPE',
    'XSD_ATTR_BALANCE',
    'XSD_ATTR_ABSTRACT',
    'XBRL_PERIOD_TYPE_ATTR',
    'XBRL_BALANCE_ATTR',
    'XSD_ELEMENT_PATH',
    'DEFAULT_TYPE',
    'DEFAULT_PERIOD_TYPE',
    'BOOLEAN_TRUE',
    'BOOLEAN_FALSE',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_DURATION',
    'BALANCE_TYPE_DEBIT',
    'BALANCE_TYPE_CREDIT',
    'NAMESPACE_TO_LIBRARY_MAP',
    'LIBRARIES_DIR_NAME',
    'XSD_FILE_PATTERN',
    'CONCEPT_QNAME_SEPARATOR',
    'CAMELCASE_SPLIT_PATTERN_LOWER_UPPER',
    'CAMELCASE_SPLIT_PATTERN_CONSECUTIVE',
    'CAMELCASE_REPLACEMENT',
]