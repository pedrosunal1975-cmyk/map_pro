# File: core/filing_stages/parsing_stage.py

"""
Parsing Stage Processor - REFACTORED
=====================================

1. Waits for ALL parsing jobs for a filing (not just one)
2. Handles multiple document parsing jobs properly
3. Aggregates facts count from all completed jobs
4. Only declares stage complete when ALL jobs are done

Handles parsing stage of filing processing workflow.
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger
from core.filing_stages.parsing_prerequisites import ParsingPrerequisitesChecker
from core.filing_stages.parsing_job_manager import ParsingJobManager
from core.filing_stages.parsing_job_aggregator import ParsingJobAggregator
from core.filing_stages.parsing_output_verifier import ParsingOutputVerifier
from core.filing_stages.parsing_stage_constants import (
    STAGE_NAME,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    RESULT_KEY_STAGES_COMPLETED,
    RESULT_KEY_STAGE_FAILED,
    RESULT_KEY_PARSE_COMPLETED,
    RESULT_KEY_FACTS_PARSED,
    RESULT_KEY_FACTS_EXTRACTED,
    RESULT_KEY_JOBS_COMPLETED,
    RESULT_KEY_ERROR,
    ZERO_COUNT
)

logger = get_logger(__name__, 'core')


class ParsingStageProcessor:
    """
    Orchestrates parsing stage for a filing.
    
    Responsibilities:
    - Coordinate parsing stage workflow
    - Check prerequisites before starting
    - Ensure all parsing jobs exist
    - Wait for all jobs to complete
    - Verify output and handle results
    
    Does NOT handle:
    - Individual job management (parsing_job_manager handles this)
    - Result aggregation (parsing_job_aggregator handles this)
    - Output verification logic (parsing_output_verifier handles this)
    - Prerequisites checking logic (parsing_prerequisites handles this)
    
    Refactored from 587-line monolithic class to focused orchestrator.
    """
    
    def __init__(self, job_waiter, output_verifier):
        """
        Initialize parsing stage processor with dependencies.
        
        Args:
            job_waiter: JobWaiter instance for waiting on jobs
            output_verifier: OutputVerifier instance for reality checks
        """
        self.logger = logger
        self.prerequisites_checker = ParsingPrerequisitesChecker()
        self.job_manager = ParsingJobManager()
        self.job_aggregator = ParsingJobAggregator(job_waiter)
        self.output_verifier = ParsingOutputVerifier(output_verifier)
    
    async def process(
        self,
        filing_id: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Process parsing stage for a filing.
        
        Revolutionary process:
        1. Check physical prerequisites
        2. Ensure jobs exist for all documents (create if needed)
        3. Wait for ALL jobs completion
        4. Verify physical output
        
        Args:
            filing_id: Filing universal ID
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
            
        Returns:
            True if parsing successful, False otherwise
        """
        workflow_status[STAGE_NAME] = STATUS_RUNNING
        
        try:
            # Step 1: Check physical prerequisites
            if not await self._verify_prerequisites(filing_id, results):
                return False
            
            # Step 2: Ensure jobs exist for all documents
            job_ids = self.job_manager.ensure_parsing_jobs(filing_id)
            if not job_ids:
                self._handle_failure(results, 'Failed to create or find parsing jobs')
                return False
            
            self.logger.info(
                "Found/created %d parsing jobs for filing %s",
                len(job_ids),
                filing_id
            )
            
            # Step 3: Wait for ALL jobs completion
            all_results = await self.job_aggregator.wait_for_all_jobs(job_ids)
            if all_results is None:
                self._handle_failure(results, 'Job completion failed or timed out')
                return False
            
            # Step 4: Verify physical output
            if not self.output_verifier.verify_output(filing_id, all_results):
                self._handle_failure(results, 'Parsing failed with no output')
                return False
            
            # Success
            self._handle_success(
                workflow_status,
                results,
                filing_id,
                all_results
            )
            return True
            
        except Exception as error:
            self.logger.error(
                "Parsing stage failed for %s: %s",
                filing_id,
                str(error),
                exc_info=True
            )
            self._handle_failure(results, f'Unexpected error: {str(error)}')
            return False
    
    async def _verify_prerequisites(
        self,
        filing_id: str,
        results: Dict[str, Any]
    ) -> bool:
        """
        Verify all prerequisites are met for parsing.
        
        Args:
            filing_id: Filing universal ID
            results: Results dictionary for error reporting
            
        Returns:
            True if prerequisites met, False otherwise
        """
        self.logger.info(
            "Checking parsing prerequisites for %s",
            filing_id
        )
        
        prerequisites = self.prerequisites_checker.check_all_prerequisites(filing_id)
        
        if not prerequisites['ready']:
            self._log_prerequisite_status(prerequisites)
            error_msg = f"Prerequisites not met: {prerequisites['summary']}"
            self._handle_failure(results, error_msg)
            return False
        
        self.logger.info(
            "All parsing prerequisites met for %s: %s",
            filing_id,
            prerequisites['summary']
        )
        return True
    
    def _log_prerequisite_status(self, prerequisites: Dict[str, Any]) -> None:
        """
        Log detailed prerequisite status for troubleshooting.
        
        Args:
            prerequisites: Prerequisites check result
        """
        self.logger.error("Parsing prerequisites not met:")
        
        xbrl = prerequisites['xbrl']
        
        if xbrl['ready']:
            self.logger.info("  [OK] XBRL files: %s", xbrl['reason'])
        else:
            self.logger.error("  [FAIL] XBRL files: %s", xbrl['reason'])
    
    def _handle_success(
        self,
        workflow_status: Dict[str, str],
        results: Dict[str, Any],
        filing_id: str,
        all_results: Dict[str, Any]
    ) -> None:
        """
        Handle successful parsing completion.
        
        Args:
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
            filing_id: Filing universal ID
            all_results: Aggregated results from all jobs
        """
        workflow_status[STAGE_NAME] = STATUS_COMPLETED
        results[RESULT_KEY_STAGES_COMPLETED].append(STAGE_NAME)
        results[RESULT_KEY_PARSE_COMPLETED] = True
        
        # Use aggregated facts count
        facts_count = all_results.get(RESULT_KEY_FACTS_EXTRACTED, ZERO_COUNT)
        
        # Double-check against database if count is zero
        if facts_count == ZERO_COUNT:
            facts_count = self.job_aggregator.query_facts_count_from_database(
                filing_id
            )
        
        results[RESULT_KEY_FACTS_PARSED] = facts_count
        
        self.logger.info(
            "Parsing completed for %s: %d facts extracted from %d jobs",
            filing_id,
            facts_count,
            all_results[RESULT_KEY_JOBS_COMPLETED]
        )
    
    def _handle_failure(
        self,
        results: Dict[str, Any],
        error: str
    ) -> None:
        """
        Handle parsing stage failure.
        
        Args:
            results: Results accumulation dictionary
            error: Error message
        """
        results[RESULT_KEY_STAGE_FAILED] = STAGE_NAME
        results[RESULT_KEY_ERROR] = error
        self.logger.error("Parsing stage failed: %s", error)


__all__ = ['ParsingStageProcessor']