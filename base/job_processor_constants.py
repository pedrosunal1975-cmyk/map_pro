"""
Map Pro Job Processor - Constants
==================================

Location: engines/base/job_processor_constants.py

All magic numbers extracted to named constants for better maintainability.
"""

# Processing Configuration
DEFAULT_BATCH_SIZE = 5  # Maximum jobs to process per iteration
DEFAULT_PROCESSING_TIMEOUT = 300  # 5 minutes per job (in seconds)

# Cleanup Configuration
CLEANUP_DEFAULT_DAYS = 30  # Default retention period for old jobs

# Required Job Fields
REQUIRED_JOB_FIELDS = ['job_id', 'job_type']

# Logging Configuration
LOG_LEVEL_DEBUG = 'DEBUG'
LOG_LEVEL_INFO = 'INFO'
LOG_LEVEL_WARNING = 'WARNING'
LOG_LEVEL_ERROR = 'ERROR'