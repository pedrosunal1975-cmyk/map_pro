# PATH: /map_pro/core/filing_stages/__init__.py

"""
Filing Processing Stages
========================

Submodule for handling individual filing processing stages.

Revolutionary Architecture:
- Stages check their own prerequisites
- Stages create their own jobs
- No dictator (job_workflow_manager deleted)
- Clean job waiting utility

Modules:
- download_stage: Handle download operations
- extraction_stage: Handle extraction operations
- parsing_stage: Handle parsing operations
- mapping_stage: Handle mapping operations
- verification: Verify stage outputs (physical reality checks)
- job_waiter: Wait for job completion (NO job finding!)
"""

from .download_stage import DownloadStageProcessor
from .extraction_stage import ExtractionStageProcessor
from .parsing_stage import ParsingStageProcessor
from .mapping_stage import MappingStageProcessor
from .verification import OutputVerifier
from .job_waiter import JobWaiter

__all__ = [
    'DownloadStageProcessor',
    'ExtractionStageProcessor',
    'ParsingStageProcessor',
    'MappingStageProcessor',
    'OutputVerifier',
    'JobWaiter'
]