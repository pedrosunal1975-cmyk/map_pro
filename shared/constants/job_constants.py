# File: shared/constants/job_constants.py
"""
Map Pro Job Constants - Updated with Library Dependency Analysis
===============================================================

Defines all job types, statuses, and priorities for the Map Pro workflow system.
Used across all engines and the job orchestrator for consistent job handling.

UPDATED: Added ANALYZE_LIBRARY_DEPENDENCIES job type for library dependency analysis.
"""

from enum import Enum


class JobType(Enum):
    """Enumeration of all job types in the Map Pro workflow."""
    SEARCH_ENTITY = "search_entity"
    FIND_FILINGS = "find_filings"
    DOWNLOAD_FILING = "download_filing"
    EXTRACT_FILES = "extract_files"
    PARSE_XBRL = "parse_xbrl"
    ANALYZE_LIBRARY_DEPENDENCIES = "analyze_library_dependencies"
    MAP_FACTS = "map_facts"
    VALIDATE_RESULTS = "validate_results"


class JobStatus(Enum):
    """Enumeration of job status values."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


# WORKFLOW PATTERNS
# TODO: These workflow patterns should be moved to market-specific configuration files
# in /map_pro/markets/<market_name>/ or stored in database configuration.
# Current implementation is for backward compatibility only.
# Each market may have different workflow requirements (e.g., FCA doesn't need EXTRACT_FILES).
WORKFLOW_PATTERNS = {
    "standard_sec": [  # US SEC market workflow
        JobType.SEARCH_ENTITY,
        JobType.FIND_FILINGS,
        JobType.DOWNLOAD_FILING,
        JobType.EXTRACT_FILES,
        JobType.PARSE_XBRL,
        JobType.ANALYZE_LIBRARY_DEPENDENCIES,
        JobType.MAP_FACTS
    ],
    "standard_fca": [  # UK FCA market workflow (no extraction step)
        JobType.SEARCH_ENTITY,
        JobType.FIND_FILINGS,
        JobType.DOWNLOAD_FILING,
        JobType.PARSE_XBRL,
        JobType.ANALYZE_LIBRARY_DEPENDENCIES,
        JobType.MAP_FACTS
    ],
    "standard_esma": [  # EU ESMA market workflow
        JobType.SEARCH_ENTITY,
        JobType.FIND_FILINGS,
        JobType.DOWNLOAD_FILING,
        JobType.EXTRACT_FILES,
        JobType.PARSE_XBRL,
        JobType.ANALYZE_LIBRARY_DEPENDENCIES,
        JobType.MAP_FACTS
    ]
}

JOB_TIMEOUTS = {
    JobType.SEARCH_ENTITY: 10,
    JobType.FIND_FILINGS: 15,
    JobType.DOWNLOAD_FILING: 30,
    JobType.EXTRACT_FILES: 15,
    JobType.PARSE_XBRL: 60,
    JobType.ANALYZE_LIBRARY_DEPENDENCIES: 45,
    JobType.MAP_FACTS: 45,
    JobType.VALIDATE_RESULTS: 20
}

MAX_RETRY_ATTEMPTS = {
    JobType.SEARCH_ENTITY: 3,
    JobType.FIND_FILINGS: 3,
    JobType.DOWNLOAD_FILING: 5,
    JobType.EXTRACT_FILES: 3,
    JobType.PARSE_XBRL: 2,
    JobType.ANALYZE_LIBRARY_DEPENDENCIES: 3,
    JobType.MAP_FACTS: 2,
    JobType.VALIDATE_RESULTS: 3
}