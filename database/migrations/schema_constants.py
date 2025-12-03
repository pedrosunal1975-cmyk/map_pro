"""
Database Schema Constants
==========================

Constants for database schema definitions and field sizing.

Save location: database/migrations/schema_constants.py

Responsibilities:
- Define field size limits
- Define precision and scale for numeric fields
- Define default values for schema elements
- Provide consistent sizing across all schemas

All values are based on analysis of typical data requirements
and industry standards for XBRL/financial data processing.
"""

# =============================================================================
# VARCHAR Field Sizes
# =============================================================================

# Small identifier fields (10-50 characters)
SIZE_MARKET_ID = 10
SIZE_ENTITY_STATUS = 20
SIZE_FILING_STATUS = 20
SIZE_JOB_STATUS = 20
SIZE_CONFIG_TYPE = 20
SIZE_PERIOD_TYPE = 20
SIZE_BALANCE_TYPE = 20

# Medium identifier/name fields (50-100 characters)
SIZE_MARKET_ENTITY_ID = 50
SIZE_FILING_TYPE = 50
SIZE_DOCUMENT_TYPE = 50
SIZE_JOB_TYPE = 50
SIZE_MODULE_OWNER = 50
SIZE_PARSER_ENGINE = 50
SIZE_PARSER_VERSION = 50
SIZE_SESSION_TYPE = 50
SIZE_CONCEPT_TYPE = 50
SIZE_DATA_TYPE = 50
SIZE_FILE_TYPE = 50
SIZE_CHECK_TYPE = 50
SIZE_MAPPING_STRATEGY = 50
SIZE_METRIC_TYPE = 50
SIZE_UNIT_OF_MEASURE = 50

# Large name/title fields (100-255 characters)
SIZE_CONFIG_KEY = 100
SIZE_MARKET_NAME = 100
SIZE_MARKET_FILING_ID = 100
SIZE_TAXONOMY_NAME = 100
SIZE_TAXONOMY_AUTHORITY = 100
SIZE_MAPPING_ALGORITHM = 100
SIZE_METRIC_NAME = 100
SIZE_MAPPED_BY = 100
SIZE_PRIMARY_NAME = 255
SIZE_SESSION_NAME = 255
SIZE_DOCUMENT_NAME = 255
SIZE_CONCEPT_LOCAL_NAME = 255
SIZE_TARGET_CONCEPT_NAME = 255
SIZE_FILE_NAME = 255

# Hash and identifier fields
SIZE_FILE_HASH_SHA256 = 64
SIZE_MARKET_COUNTRY = 3
SIZE_CURRENCY_CODE = 3

# =============================================================================
# DECIMAL Field Precision and Scale
# =============================================================================

# File sizes and measurements
PRECISION_FILE_SIZE_MB = 10
SCALE_FILE_SIZE_MB = 2

# Timing and duration
PRECISION_DURATION_SECONDS = 10
SCALE_DURATION_SECONDS = 3

PRECISION_SHORT_DURATION = 8
SCALE_SHORT_DURATION = 3

# Confidence and quality scores
PRECISION_CONFIDENCE = 5
SCALE_CONFIDENCE = 4

PRECISION_QUALITY_METRIC = 10
SCALE_QUALITY_METRIC = 4

# =============================================================================
# Default Integer Values
# =============================================================================

# Rate limiting and performance
DEFAULT_RATE_LIMIT_PER_MINUTE = 10
DEFAULT_JOB_PRIORITY = 5
DEFAULT_RETRY_COUNT = 0

# Counters and aggregates
DEFAULT_COUNTER_VALUE = 0
DEFAULT_CONFIDENCE_THRESHOLD = 0.85

# =============================================================================
# Default String Values
# =============================================================================

# Status defaults
DEFAULT_STATUS_PENDING = 'pending'
DEFAULT_STATUS_QUEUED = 'queued'
DEFAULT_STATUS_RUNNING = 'running'
DEFAULT_STATUS_ACTIVE = 'active'

# Configuration defaults
DEFAULT_CONFIG_TYPE = 'string'
DEFAULT_PARSER_ENGINE = 'arelle'
DEFAULT_MARKET_REGISTRY_MODE = 'dynamic'

# Schema versioning
SCHEMA_VERSION = 'v1.0.0'
MODULE_OWNER_MIGRATION = 'migration_system'
MODULE_OWNER_MARKET = 'market_system'

# =============================================================================
# Database Names
# =============================================================================

DATABASE_NAME_CORE = 'core'
DATABASE_NAME_PARSED = 'parsed'
DATABASE_NAME_LIBRARY = 'library'
DATABASE_NAME_MAPPED = 'mapped'

# =============================================================================
# Boolean Defaults
# =============================================================================

DEFAULT_BOOLEAN_TRUE = True
DEFAULT_BOOLEAN_FALSE = False

# =============================================================================
# Constraint Check Values
# =============================================================================

MIN_FILING_COUNT = 0
MIN_COUNTER = 0


__all__ = [
    # VARCHAR sizes
    'SIZE_MARKET_ID',
    'SIZE_ENTITY_STATUS',
    'SIZE_FILING_STATUS',
    'SIZE_JOB_STATUS',
    'SIZE_CONFIG_TYPE',
    'SIZE_PERIOD_TYPE',
    'SIZE_BALANCE_TYPE',
    'SIZE_MARKET_ENTITY_ID',
    'SIZE_FILING_TYPE',
    'SIZE_DOCUMENT_TYPE',
    'SIZE_JOB_TYPE',
    'SIZE_MODULE_OWNER',
    'SIZE_PARSER_ENGINE',
    'SIZE_PARSER_VERSION',
    'SIZE_SESSION_TYPE',
    'SIZE_CONCEPT_TYPE',
    'SIZE_DATA_TYPE',
    'SIZE_FILE_TYPE',
    'SIZE_CHECK_TYPE',
    'SIZE_MAPPING_STRATEGY',
    'SIZE_METRIC_TYPE',
    'SIZE_UNIT_OF_MEASURE',
    'SIZE_CONFIG_KEY',
    'SIZE_MARKET_NAME',
    'SIZE_MARKET_FILING_ID',
    'SIZE_TAXONOMY_NAME',
    'SIZE_TAXONOMY_AUTHORITY',
    'SIZE_MAPPING_ALGORITHM',
    'SIZE_METRIC_NAME',
    'SIZE_MAPPED_BY',
    'SIZE_PRIMARY_NAME',
    'SIZE_SESSION_NAME',
    'SIZE_DOCUMENT_NAME',
    'SIZE_CONCEPT_LOCAL_NAME',
    'SIZE_TARGET_CONCEPT_NAME',
    'SIZE_FILE_NAME',
    'SIZE_FILE_HASH_SHA256',
    'SIZE_MARKET_COUNTRY',
    'SIZE_CURRENCY_CODE',
    
    # DECIMAL precision
    'PRECISION_FILE_SIZE_MB',
    'SCALE_FILE_SIZE_MB',
    'PRECISION_DURATION_SECONDS',
    'SCALE_DURATION_SECONDS',
    'PRECISION_SHORT_DURATION',
    'SCALE_SHORT_DURATION',
    'PRECISION_CONFIDENCE',
    'SCALE_CONFIDENCE',
    'PRECISION_QUALITY_METRIC',
    'SCALE_QUALITY_METRIC',
    
    # Defaults
    'DEFAULT_RATE_LIMIT_PER_MINUTE',
    'DEFAULT_JOB_PRIORITY',
    'DEFAULT_RETRY_COUNT',
    'DEFAULT_COUNTER_VALUE',
    'DEFAULT_CONFIDENCE_THRESHOLD',
    'DEFAULT_STATUS_PENDING',
    'DEFAULT_STATUS_QUEUED',
    'DEFAULT_STATUS_RUNNING',
    'DEFAULT_STATUS_ACTIVE',
    'DEFAULT_CONFIG_TYPE',
    'DEFAULT_PARSER_ENGINE',
    'DEFAULT_MARKET_REGISTRY_MODE',
    'SCHEMA_VERSION',
    'MODULE_OWNER_MIGRATION',
    'MODULE_OWNER_MARKET',
    'DATABASE_NAME_CORE',
    'DATABASE_NAME_PARSED',
    'DATABASE_NAME_LIBRARY',
    'DATABASE_NAME_MAPPED',
    'DEFAULT_BOOLEAN_TRUE',
    'DEFAULT_BOOLEAN_FALSE',
    'MIN_FILING_COUNT',
    'MIN_COUNTER',
]