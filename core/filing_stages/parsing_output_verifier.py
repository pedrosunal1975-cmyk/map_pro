# File: core/filing_stages/parsing_output_verifier.py

"""
Parsing Output Verifier
========================

Verifies parsing output and reconciles job results with physical reality.
Implements "trust reality over metadata" philosophy.

Architecture: Single Responsibility - Focuses only on output verification.
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.filing_stages.parsing_stage_constants import (
    RESULT_KEY_JOBS_COMPLETED,
    ZERO_COUNT
)

logger = get_logger(__name__, 'core')


class ParsingOutputVerifier:
    """
    Verifies parsing output exists and reconciles with job results.
    
    Responsibilities:
    - Verify physical output files exist
    - Reconcile job results with file system reality
    - Handle discrepancies between metadata and reality
    
    Philosophy: Trust reality (files) over metadata (database) when they conflict.
    
    Does NOT handle:
    - Job creation (parsing_job_manager handles this)
    - Job execution (job_orchestrator handles this)
    - Prerequisites checking (parsing_prerequisites handles this)
    - Result aggregation (parsing_job_aggregator handles this)
    """
    
    def __init__(self, output_verifier):
        """
        Initialize parsing output verifier.
        
        Args:
            output_verifier: OutputVerifier instance for physical checks
        """
        self.logger = logger
        self.output_verifier = output_verifier
    
    def verify_output(
        self,
        filing_id: str,
        all_results: Dict[str, Any]
    ) -> bool:
        """
        Verify parsing output exists physically and reconcile with job results.
        
        Trust reality (files) over metadata (database) if mismatch exists.
        This handles cases where jobs report failure but files exist, or vice versa.
        
        Args:
            filing_id: Filing universal ID
            all_results: Aggregated results from all jobs
            
        Returns:
            True if output verified or reconciled, False if definitively failed
        """
        jobs_succeeded = self._check_jobs_succeeded(all_results)
        files_exist = self._check_files_exist(filing_id)
        
        return self._reconcile_results(
            filing_id,
            jobs_succeeded,
            files_exist
        )
    
    def _check_jobs_succeeded(self, all_results: Dict[str, Any]) -> bool:
        """
        Check if any jobs completed successfully.
        
        Args:
            all_results: Aggregated job results
            
        Returns:
            True if at least one job succeeded, False otherwise
        """
        return all_results[RESULT_KEY_JOBS_COMPLETED] > ZERO_COUNT
    
    def _check_files_exist(self, filing_id: str) -> bool:
        """
        Check if parsing output files exist physically.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            True if output files exist, False otherwise
        """
        return self.output_verifier.verify_parsing_output(filing_id)
    
    def _reconcile_results(
        self,
        filing_id: str,
        jobs_succeeded: bool,
        files_exist: bool
    ) -> bool:
        """
        Reconcile job results with file system reality.
        
        Handles four scenarios:
        1. Both failed: Definitive failure
        2. Jobs failed but files exist: Trust reality (success)
        3. Jobs succeeded but no files: Warning but accept (non-instance docs)
        4. Both succeeded: Clear success
        
        Args:
            filing_id: Filing universal ID
            jobs_succeeded: Whether any jobs completed successfully
            files_exist: Whether output files exist physically
            
        Returns:
            True if reconciliation indicates success, False if definitive failure
        """
        # Scenario 1: Both agree it failed
        if not jobs_succeeded and not files_exist:
            self.logger.error(
                "Parsing failed for %s: No jobs succeeded and no output files found",
                filing_id
            )
            return False
        
        # Scenario 2: Jobs failed but files exist (trust reality!)
        if not jobs_succeeded and files_exist:
            self.logger.warning(
                "Jobs report failure for %s but output files exist - trusting physical reality",
                filing_id
            )
            return True
        
        # Scenario 3: Jobs succeeded but no files (may be normal)
        if jobs_succeeded and not files_exist:
            self.logger.warning(
                "Jobs report success for %s but no output files found - "
                "may be normal for non-instance documents",
                filing_id
            )
            return True
        
        # Scenario 4: Both succeeded (ideal case)
        return True


__all__ = [
    'ParsingOutputVerifier'
]