# File: core/filing_stages/parsing_job_aggregator.py

"""
Parsing Job Aggregator
=======================

Aggregates results from multiple parsing jobs.
Waits for all jobs to complete and combines their outputs.

CRITICAL: This module ensures ALL parsing jobs complete before
declaring stage success. Previous bug: only waited for one job.

Architecture: Single Responsibility - Focuses only on job result aggregation.
"""

from typing import Dict, Any, List, Optional

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.parsed_models import ParsedDocument
from core.filing_stages.parsing_stage_constants import (
    STAGE_NAME,
    INITIAL_JOB_RESULTS,
    RESULT_KEY_JOBS_COMPLETED,
    RESULT_KEY_JOBS_FAILED,
    RESULT_KEY_FACTS_EXTRACTED,
    RESULT_KEY_DOCUMENTS_PARSED,
    RESULT_KEY_ERRORS,
    RESULT_KEY_SUCCESS,
    RESULT_KEY_DOCUMENT_ID,
    RESULT_KEY_ERROR,
    ZERO_COUNT
)

logger = get_logger(__name__, 'core')


class ParsingJobAggregator:
    """
    Aggregates results from multiple parsing jobs.
    
    Responsibilities:
    - Wait for ALL parsing jobs to complete (not just one)
    - Aggregate facts counts from all jobs
    - Track success/failure for each job
    - Query database for fact counts as fallback
    
    Does NOT handle:
    - Job creation (parsing_job_manager handles this)
    - Job execution (job_orchestrator handles this)
    - Prerequisites checking (parsing_prerequisites handles this)
    - Output verification (output_verifier handles this)
    """
    
    def __init__(self, job_waiter):
        """
        Initialize parsing job aggregator.
        
        Args:
            job_waiter: JobWaiter instance for waiting on jobs
        """
        self.logger = logger
        self.job_waiter = job_waiter
    
    async def wait_for_all_jobs(
        self,
        job_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for ALL parsing jobs to complete and aggregate results.
        
        CRITICAL FIX: Waits for ALL jobs, not just the first one.
        This ensures all documents in a filing are parsed before proceeding.
        
        Args:
            job_ids: List of job IDs to wait for
            
        Returns:
            Aggregated results dictionary if successful, None otherwise
        """
        self.logger.info(
            "Waiting for %d parsing jobs to complete",
            len(job_ids)
        )
        
        all_results = INITIAL_JOB_RESULTS.copy()
        
        try:
            for index, job_id in enumerate(job_ids, start=1):
                self.logger.info(
                    "Waiting for job %d/%d: %s",
                    index,
                    len(job_ids),
                    job_id
                )
                
                job_result = await self.job_waiter.wait_for_job_completion(
                    job_id,
                    STAGE_NAME
                )
                
                self._aggregate_single_job_result(
                    job_result,
                    job_id,
                    all_results
                )
            
            # Log aggregated summary
            self._log_aggregation_summary(all_results, len(job_ids))
            
            # Check if we have any successful results
            if all_results[RESULT_KEY_JOBS_COMPLETED] == ZERO_COUNT:
                self.logger.error(
                    "All %d parsing jobs failed",
                    len(job_ids)
                )
                return None
            
            return all_results
            
        except Exception as error:
            self.logger.error(
                "Error waiting for job completion: %s",
                str(error),
                exc_info=True
            )
            return None
    
    def _aggregate_single_job_result(
        self,
        job_result: Optional[Dict[str, Any]],
        job_id: str,
        all_results: Dict[str, Any]
    ) -> None:
        """
        Aggregate results from a single job into the overall results.
        
        Args:
            job_result: Result dictionary from job waiter
            job_id: Job identifier for logging
            all_results: Aggregated results dictionary to update
        """
        if not job_result:
            self.logger.warning(
                "Job %s did not complete successfully",
                job_id
            )
            all_results[RESULT_KEY_JOBS_FAILED] += 1
            all_results[RESULT_KEY_ERRORS].append(
                f"Job {job_id} failed or timed out"
            )
            return
        
        # Check if job succeeded
        if job_result.get(RESULT_KEY_SUCCESS):
            self._aggregate_successful_job(job_result, job_id, all_results)
        else:
            self._aggregate_failed_job(job_result, job_id, all_results)
    
    def _aggregate_successful_job(
        self,
        job_result: Dict[str, Any],
        job_id: str,
        all_results: Dict[str, Any]
    ) -> None:
        """
        Aggregate results from a successful job.
        
        Args:
            job_result: Result dictionary from successful job
            job_id: Job identifier for logging
            all_results: Aggregated results dictionary to update
        """
        all_results[RESULT_KEY_JOBS_COMPLETED] += 1
        
        facts = job_result.get(RESULT_KEY_FACTS_EXTRACTED, ZERO_COUNT)
        all_results[RESULT_KEY_FACTS_EXTRACTED] += facts
        
        document_id = job_result.get(RESULT_KEY_DOCUMENT_ID)
        if document_id:
            all_results[RESULT_KEY_DOCUMENTS_PARSED].append(document_id)
        
        self.logger.info(
            "Job %s completed: %d facts extracted",
            job_id,
            facts
        )
    
    def _aggregate_failed_job(
        self,
        job_result: Dict[str, Any],
        job_id: str,
        all_results: Dict[str, Any]
    ) -> None:
        """
        Aggregate results from a failed job.
        
        Args:
            job_result: Result dictionary from failed job
            job_id: Job identifier for logging
            all_results: Aggregated results dictionary to update
        """
        all_results[RESULT_KEY_JOBS_FAILED] += 1
        error = job_result.get(RESULT_KEY_ERROR, 'Unknown error')
        all_results[RESULT_KEY_ERRORS].append(f"Job {job_id}: {error}")
        
        self.logger.warning(
            "Job %s completed with error: %s",
            job_id,
            error
        )
    
    def _log_aggregation_summary(
        self,
        all_results: Dict[str, Any],
        total_jobs: int
    ) -> None:
        """
        Log summary of aggregated job results.
        
        Args:
            all_results: Aggregated results dictionary
            total_jobs: Total number of jobs processed
        """
        self.logger.info(
            "All parsing jobs completed: %d succeeded, %d failed, %d total facts",
            all_results[RESULT_KEY_JOBS_COMPLETED],
            all_results[RESULT_KEY_JOBS_FAILED],
            all_results[RESULT_KEY_FACTS_EXTRACTED]
        )
    
    def query_facts_count_from_database(self, filing_id: str) -> int:
        """
        Query facts count from ParsedDocument table as fallback.
        
        Used when job results report zero facts but we want to verify
        against the database reality.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Total facts count from database
        """
        try:
            with db_coordinator.get_session('parsed') as session:
                parsed_docs = session.query(ParsedDocument).filter_by(
                    filing_universal_id=filing_id
                ).all()
                
                facts_count = sum(
                    doc.facts_extracted or ZERO_COUNT for doc in parsed_docs
                )
                
                if facts_count > ZERO_COUNT:
                    self.logger.info(
                        "Retrieved facts count from database for filing %s: %d",
                        filing_id,
                        facts_count
                    )
                
                return facts_count
        
        except Exception as error:
            self.logger.warning(
                "Could not query ParsedDocument for filing %s: %s",
                filing_id,
                str(error)
            )
            return ZERO_COUNT


__all__ = [
    'ParsingJobAggregator'
]