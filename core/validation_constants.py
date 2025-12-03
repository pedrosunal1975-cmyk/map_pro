# File: /map_pro/core/validation_constants.py

"""
Validation Constants
====================

Centralized constants for validation system.
Eliminates magic strings and provides clear configuration.
"""

from typing import Dict, List

# Validation status values
STATUS_PASS: str = 'pass'
STATUS_FAIL: str = 'fail'
STATUS_WARNING: str = 'warning'
STATUS_ERROR: str = 'error'
STATUS_UNKNOWN: str = 'unknown'

# Database status values
DB_STATUS_HEALTHY: str = 'healthy'

# Check result keys
KEY_STATUS: str = 'status'
KEY_DETAILS: str = 'details'
KEY_ERROR: str = 'error'
KEY_VIOLATIONS: str = 'violations'
KEY_MISSING_DIRECTORIES: str = 'missing_directories'
KEY_MISSING_FILES: str = 'missing_files'
KEY_INVALID_FILES: str = 'invalid_files'
KEY_PERMISSION_ISSUES: str = 'permission_issues'
KEY_DATABASE_HEALTH: str = 'database_health'

# Engine readiness keys
KEY_ENGINE_NAME: str = 'engine_name'
KEY_READY: str = 'ready'
KEY_BLOCKING_ISSUES: str = 'blocking_issues'
KEY_WARNINGS: str = 'warnings'
KEY_BLOCKING: str = 'blocking'

# File names
PERMISSION_TEST_FILE: str = '.permission_test'

# Configuration file names
CONFIG_SYSTEM_SETTINGS: str = 'system_settings.json'
CONFIG_LOGGING: str = 'logging_config.json'
CONFIG_MARKET_REGISTRY: str = 'market_registry.json'

# Taxonomy paths
TAXONOMY_LIBRARIES_SUBDIR: str = 'libraries'
TAXONOMY_DOWNLOADS_SUBDIR: str = 'downloads'

# Engine names
ENGINE_SEARCHER: str = 'searcher'
ENGINE_DOWNLOADER: str = 'downloader'
ENGINE_EXTRACTOR: str = 'extractor'
ENGINE_PARSER: str = 'parser'
ENGINE_LIBRARIAN: str = 'librarian'
ENGINE_MAPPER: str = 'mapper'

# Validation messages
MSG_COORDINATOR_NOT_INITIALIZED: str = 'Database coordinator not initialized'
MSG_PARTITION_VIOLATION: str = 'Data/program partition separation violated'
MSG_REQUIRED_PATH_MISSING: str = 'Required path missing: {path}'
MSG_VALIDATION_ERROR: str = 'Validation error: {error}'
MSG_NO_TAXONOMY_LIBRARIES: str = 'No taxonomy libraries directory found'
MSG_NO_TAXONOMY_DOWNLOADS: str = 'Taxonomy downloads directory not found'
MSG_NO_PARSED_FACTS: str = 'No parsed facts found - parser should run first'
MSG_ENGINE_CHECK_FAILED: str = 'Engine-specific check failed: {error}'

# Detail keys for results
DETAIL_DATA_DIRS_CHECKED: str = 'data_directories_checked'
DETAIL_PROGRAM_DIRS_CHECKED: str = 'program_directories_checked'
DETAIL_PROGRAM_MISSING: str = 'program_missing'
DETAIL_DATA_IN_PROGRAM: str = 'data_files_in_program'
DETAIL_PROGRAMS_IN_DATA: str = 'program_files_in_data'
DETAIL_SEPARATION_COMPLIANT: str = 'separation_compliant'
DETAIL_FILES_EXCEEDING_LIMIT: str = 'files_exceeding_limit'
DETAIL_LARGEST_FILE_LINES: str = 'largest_file_lines'
DETAIL_ALL_FILES_COMPLIANT: str = 'all_files_compliant'
DETAIL_CONFIGS_CHECKED: str = 'configs_checked'
DETAIL_MISSING_COUNT: str = 'missing_count'
DETAIL_INVALID_COUNT: str = 'invalid_count'
DETAIL_COORDINATOR_ERROR: str = 'coordinator_error'
DETAIL_UNHEALTHY_DBS: str = 'unhealthy_databases'
DETAIL_ALL_DBS_HEALTHY: str = 'all_databases_healthy'
DETAIL_PATHS_TESTED: str = 'paths_tested'
DETAIL_PERMISSION_ERRORS: str = 'permission_errors'