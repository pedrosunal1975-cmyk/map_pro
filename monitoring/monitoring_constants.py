"""
Map Pro Monitoring Constants
=============================

Constants used across monitoring modules.

Save location: tools/monitoring/monitoring_constants.py
"""

from shared.constants.job_constants import JobType

# Default configuration values
DEFAULT_COLLECTION_INTERVAL = 60  # seconds
DEFAULT_METRICS_HISTORY_SIZE = 1000

# Conversion constants
BYTES_PER_GB = 1024 ** 3
BYTES_PER_MB = 1024 ** 2
ROUND_DECIMAL_PLACES = 2

# Database names
DATABASE_NAMES = ['core', 'parsed', 'library', 'mapped']

# Engine to job type mapping
# Note: Librarian excluded as it doesn't process standard workflow jobs
ENGINE_JOB_TYPE_MAPPING = {
    'searcher': [JobType.SEARCH_ENTITY, JobType.FIND_FILINGS],
    'downloader': [JobType.DOWNLOAD_FILING],
    'extractor': [JobType.EXTRACT_FILES],
    'parser': [JobType.PARSE_XBRL],
    'mapper': [JobType.MAP_FACTS]
}

# Report formatting
REPORT_SEPARATOR_CHAR = '='
REPORT_SEPARATOR_LENGTH = 60

# Processing rate calculation
PROCESSING_RATE_WINDOW_MINUTES = 5