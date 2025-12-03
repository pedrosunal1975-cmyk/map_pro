# File: core/filing_stages/parsing_stage_constants.py

"""
Parsing Stage Constants
========================

Constants used in parsing stage processing.
Centralizes magic numbers and status values.

Architecture: Configuration module - reduces magic numbers in codebase.
"""

# Stage identification
STAGE_NAME = 'parse'

# Job and workflow statuses
STATUS_QUEUED = 'queued'
STATUS_RUNNING = 'running'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'
STATUS_NOT_APPLICABLE = 'not_applicable'

# Valid job statuses for finding existing jobs
VALID_JOB_STATUSES = [STATUS_QUEUED, STATUS_RUNNING, STATUS_COMPLETED]

# Result dictionary keys
RESULT_KEY_JOBS_COMPLETED = 'jobs_completed'
RESULT_KEY_JOBS_FAILED = 'jobs_failed'
RESULT_KEY_FACTS_EXTRACTED = 'facts_extracted'
RESULT_KEY_DOCUMENTS_PARSED = 'documents_parsed'
RESULT_KEY_ERRORS = 'errors'
RESULT_KEY_SUCCESS = 'success'
RESULT_KEY_DOCUMENT_ID = 'document_id'
RESULT_KEY_ERROR = 'error'
RESULT_KEY_STAGES_COMPLETED = 'stages_completed'
RESULT_KEY_STAGE_FAILED = 'stage_failed'
RESULT_KEY_PARSE_COMPLETED = 'parse_completed'
RESULT_KEY_FACTS_PARSED = 'facts_parsed'

# Initial job results template
INITIAL_JOB_RESULTS = {
    RESULT_KEY_JOBS_COMPLETED: 0,
    RESULT_KEY_JOBS_FAILED: 0,
    RESULT_KEY_FACTS_EXTRACTED: 0,
    RESULT_KEY_DOCUMENTS_PARSED: [],
    RESULT_KEY_ERRORS: []
}

# Counts
ZERO_COUNT = 0
MINIMUM_SUCCESSFUL_JOBS = 0


__all__ = [
    'STAGE_NAME',
    'STATUS_QUEUED',
    'STATUS_RUNNING',
    'STATUS_COMPLETED',
    'STATUS_FAILED',
    'STATUS_NOT_APPLICABLE',
    'VALID_JOB_STATUSES',
    'RESULT_KEY_JOBS_COMPLETED',
    'RESULT_KEY_JOBS_FAILED',
    'RESULT_KEY_FACTS_EXTRACTED',
    'RESULT_KEY_DOCUMENTS_PARSED',
    'RESULT_KEY_ERRORS',
    'RESULT_KEY_SUCCESS',
    'RESULT_KEY_DOCUMENT_ID',
    'RESULT_KEY_ERROR',
    'RESULT_KEY_STAGES_COMPLETED',
    'RESULT_KEY_STAGE_FAILED',
    'RESULT_KEY_PARSE_COMPLETED',
    'RESULT_KEY_FACTS_PARSED',
    'INITIAL_JOB_RESULTS',
    'ZERO_COUNT',
    'MINIMUM_SUCCESSFUL_JOBS'
]