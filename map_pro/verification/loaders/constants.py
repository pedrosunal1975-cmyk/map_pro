# Path: verification/loaders/constants.py
"""
Loaders Module Constants for Verification

Constants for data loading operations.
All patterns here are DETECTION AIDS, not business logic.
"""

# ==============================================================================
# FILE DETECTION PATTERNS
# ==============================================================================

# File type detection by extension
FILE_TYPE_PATTERNS = {
    'json': ['.json'],
    'csv': ['.csv'],
    'xlsx': ['.xlsx', '.xlsm'],
    'txt': ['.txt'],
    'xml': ['.xml'],
    'xbrl': ['.xbrl'],
    'htm': ['.htm', '.html', '.xhtml'],
    'xsd': ['.xsd'],
}

# ==============================================================================
# MAPPED STATEMENTS DETECTION
# ==============================================================================

# Files that indicate a valid mapped statement directory
MAPPED_STATEMENT_MARKERS = [
    'MAIN_FINANCIAL_STATEMENTS.json',
    'statements.json',
]

# Subdirectories within mapped statement output
MAPPED_OUTPUT_SUBDIRS = ['json', 'csv', 'excel']

# ==============================================================================
# PARSED OUTPUT DETECTION
# ==============================================================================

# Main parsed output file
PARSED_JSON_FILE = 'parsed.json'

# ==============================================================================
# XBRL FILING DETECTION
# ==============================================================================

# Linkbase file patterns
CALCULATION_LINKBASE_PATTERNS = ['_cal.xml', '_calculation.xml', '-cal.xml', 'cal.xml']
PRESENTATION_LINKBASE_PATTERNS = ['_pre.xml', '_presentation.xml', '-pre.xml', 'pre.xml']
DEFINITION_LINKBASE_PATTERNS = ['_def.xml', '_definition.xml', '-def.xml', 'def.xml']
LABEL_LINKBASE_PATTERNS = ['_lab.xml', '_label.xml', '-lab.xml', 'lab.xml']

# Schema file patterns
SCHEMA_FILE_PATTERNS = ['.xsd']

# Instance document patterns
INSTANCE_FILE_PATTERNS = ['.xml', '.xbrl', '.xhtml', '.htm', '.html']

# ==============================================================================
# XBRL SPECIFICATION CONSTANTS
# ==============================================================================

# XML Namespace URIs (XBRL 2.1 Specification)
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'
XBRL_LINKBASE_NAMESPACE = 'http://www.xbrl.org/2003/linkbase'
XBRL_INSTANCE_NAMESPACE = 'http://www.xbrl.org/2003/instance'

# XLink attribute names
XLINK_ATTRS = {
    'from': f'{{{XLINK_NAMESPACE}}}from',
    'to': f'{{{XLINK_NAMESPACE}}}to',
    'label': f'{{{XLINK_NAMESPACE}}}label',
    'href': f'{{{XLINK_NAMESPACE}}}href',
    'role': f'{{{XLINK_NAMESPACE}}}role',
    'arcrole': f'{{{XLINK_NAMESPACE}}}arcrole',
}

# Linkbase element names
LINKBASE_ELEMENTS = {
    'calculation_link': 'calculationLink',
    'calculation_arc': 'calculationArc',
    'presentation_link': 'presentationLink',
    'presentation_arc': 'presentationArc',
    'definition_link': 'definitionLink',
    'definition_arc': 'definitionArc',
    'locator': 'loc',
}

# Arc attributes
ARC_ATTRIBUTES = ['order', 'priority', 'use', 'weight', 'preferredLabel']

# ==============================================================================
# TAXONOMY LIBRARY PATTERNS
# ==============================================================================

# Common standard taxonomy patterns
STANDARD_TAXONOMY_PATTERNS = {
    'us_gaap': ['us-gaap', 'fasb.org/us-gaap'],
    'ifrs': ['ifrs', 'iasb'],
    'uk_gaap': ['uk-gaap', 'frc.org.uk'],
    'esef': ['esef', 'esma'],
    'dei': ['dei', 'xbrl.sec.gov/dei'],
    'srt': ['srt', 'fasb.org/srt'],
}

# ==============================================================================
# OPERATIONAL CONFIGURATION
# ==============================================================================

# Maximum directory depth to search
MAX_DIRECTORY_DEPTH = 25

# File size limits (MB)
MAX_FILE_SIZES = {
    'json': 500,
    'xml': 200,
    'xsd': 50,
    'csv': 100,
    'xlsx': 100,
}

# Logging levels for loader operations
LOG_LEVELS = {
    'discovery': 'INFO',
    'reading': 'DEBUG',
    'validation': 'INFO',
    'errors': 'ERROR',
}


__all__ = [
    # File patterns
    'FILE_TYPE_PATTERNS',

    # Mapped statements
    'MAPPED_STATEMENT_MARKERS',
    'MAPPED_OUTPUT_SUBDIRS',

    # Parsed output
    'PARSED_JSON_FILE',

    # XBRL patterns
    'CALCULATION_LINKBASE_PATTERNS',
    'PRESENTATION_LINKBASE_PATTERNS',
    'DEFINITION_LINKBASE_PATTERNS',
    'LABEL_LINKBASE_PATTERNS',
    'SCHEMA_FILE_PATTERNS',
    'INSTANCE_FILE_PATTERNS',

    # XBRL namespaces
    'XLINK_NAMESPACE',
    'XBRL_LINKBASE_NAMESPACE',
    'XBRL_INSTANCE_NAMESPACE',
    'XLINK_ATTRS',
    'LINKBASE_ELEMENTS',
    'ARC_ATTRIBUTES',

    # Taxonomy patterns
    'STANDARD_TAXONOMY_PATTERNS',

    # Configuration
    'MAX_DIRECTORY_DEPTH',
    'MAX_FILE_SIZES',
    'LOG_LEVELS',
]
