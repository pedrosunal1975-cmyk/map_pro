# PATH: /map_pro/core/filing_stages/download_stage.py

"""
Download Stage Processor
========================

Handles download stage of filing processing workflow.

Revolutionary Architecture:
- Checks own prerequisites before starting (engineer responsibility)
- Creates own job (already did this - was ahead of revolution!)
- No dependency on job_workflow_manager (no dictator)
- Database as journalist (read metadata, write results)

Process Flow:
1. Check prerequisites (filing info valid, download dir writable)
2. Create download job
3. Wait for job completion
4. Success

Dependencies:
- DownloadPrerequisitesChecker: Verifies prerequisites
- job_orchestrator: Job queue management
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.job_orchestrator import job_orchestrator
from shared.constants.job_constants import JobType
from .download_prerequisites import DownloadPrerequisitesChecker

logger = get_logger(__name__, 'core')

STAGE_NAME = 'download'
STATUS_RUNNING = 'running'
STATUS_COMPLETED = 'completed'


class DownloadStageProcessor:
    """
    Processes download stage for a filing.
    
    Responsible engineer: Checks prerequisites, creates job.
    
    NOTE: This stage was already revolutionary (created own job)!
    Just adding prerequisite checks for completeness.
    """
    
    def __init__(self, job_finder):
        """
        Initialize download stage processor.
        
        Args:
            job_finder: JobFinder instance for waiting on jobs
        """
        self.logger = logger
        self.job_finder = job_finder
        self.prerequisites_checker = DownloadPrerequisitesChecker()
    
    async def process(
        self,
        filing_id: str,
        filing_info: Dict[str, Any],
        market_type: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Process download stage for a filing.
        
        Revolutionary process:
        1. Check physical prerequisites
        2. Create job (already did this!)
        3. Wait for job completion
        
        Args:
            filing_id: Filing universal ID
            filing_info: Filing information dictionary
            market_type: Market type identifier
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
            
        Returns:
            True if download successful, False otherwise
        """
        workflow_status[STAGE_NAME] = STATUS_RUNNING
        
        try:
            # Step 1: Check physical prerequisites
            if not self._verify_prerequisites(filing_info, market_type, results):
                return False
            
            # Step 2: Create download job
            job_id = self._create_download_job(filing_id, filing_info, market_type)
            if not job_id:
                self._handle_failure(results, 'Failed to create download job')
                return False
            
            # Step 3: Wait for job completion
            job_result = await self._wait_for_completion(job_id, results)
            if not job_result:
                return False
            
            # Success
            self._handle_success(workflow_status, results)
            return True
            
        except Exception as e:
            self.logger.error(f"Download stage failed: {e}", exc_info=True)
            self._handle_failure(results, f'Unexpected error: {str(e)}')
            return False
    
    def _verify_prerequisites(
        self,
        filing_info: Dict[str, Any],
        market_type: str,
        results: Dict[str, Any]
    ) -> bool:
        """
        Verify all prerequisites are met for download.
        
        Args:
            filing_info: Filing information dictionary
            market_type: Market type identifier
            results: Results dictionary for error reporting
            
        Returns:
            True if prerequisites met, False otherwise
        """
        self.logger.info("Checking download prerequisites")
        
        prerequisites = self.prerequisites_checker.check_all_prerequisites(
            filing_info,
            market_type
        )
        
        if not prerequisites['ready']:
            self._log_prerequisite_status(prerequisites)
            error_msg = f"Prerequisites not met: {prerequisites['summary']}"
            self._handle_failure(results, error_msg)
            return False
        
        self.logger.info(
            f"All download prerequisites met: {prerequisites['summary']}"
        )
        return True
    
    def _log_prerequisite_status(self, prerequisites: Dict[str, Any]) -> None:
        """
        Log detailed prerequisite status for troubleshooting.
        
        Args:
            prerequisites: Prerequisites check result
        """
        self.logger.error("Download prerequisites not met:")
        
        filing_info = prerequisites['filing_info']
        download_dir = prerequisites['download_dir']
        
        # Log filing info status
        if filing_info['ready']:
            self.logger.info(f"  [OK] Filing info: {filing_info['reason']}")
        else:
            self.logger.error(f"  [FAIL] Filing info: {filing_info['reason']}")
        
        # Log download directory status
        if download_dir['ready']:
            self.logger.info(f"  [OK] Download directory: {download_dir['reason']}")
        else:
            self.logger.error(f"  [FAIL] Download directory: {download_dir['reason']}")
    
    def _create_download_job(
        self,
        filing_id: str,
        filing_info: Dict[str, Any],
        market_type: str
    ) -> str:
        """
        Create download job in job queue.
        
        NOTE: This was already revolutionary! Download stage already
        created its own job instead of waiting for dictator.
        
        Args:
            filing_id: Filing universal ID
            filing_info: Filing information dictionary
            market_type: Market type identifier
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            job_id = job_orchestrator.create_job(
                job_type=JobType.DOWNLOAD_FILING,
                entity_id=filing_info.get('entity_id'),
                market_type=market_type,
                parameters={'filing_universal_id': filing_id}
            )
            
            self.logger.info(f"Created download job: {job_id}")
            return job_id
            
        except Exception as e:
            self.logger.error(f"Error creating download job: {e}", exc_info=True)
            return None
    
    async def _wait_for_completion(
        self,
        job_id: str,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Wait for download job to complete.
        
        Args:
            job_id: Job ID to wait for
            results: Results dictionary for error reporting
            
        Returns:
            Job result dictionary if successful, None otherwise
        """
        self.logger.info(f"Waiting for download job {job_id} to complete")
        
        try:
            job_result = await self.job_finder.wait_for_job_completion(
                job_id,
                STAGE_NAME
            )
            
            if not job_result:
                self._handle_failure(results, 'Job completion timeout')
                return None
            
            if not job_result.get('success'):
                error = job_result.get('error', 'Unknown error')
                self._handle_failure(results, error)
                return None
            
            return job_result
            
        except Exception as e:
            self.logger.error(f"Error waiting for job completion: {e}", exc_info=True)
            self._handle_failure(results, f'Job wait error: {str(e)}')
            return None
    
    def _handle_success(
        self,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> None:
        """
        Handle successful download completion.
        
        Args:
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
        """
        workflow_status[STAGE_NAME] = STATUS_COMPLETED
        results['stages_completed'].append(STAGE_NAME)
        results['download_completed'] = True
        
        self.logger.info("Download stage completed successfully")
    
    def _handle_failure(
        self,
        results: Dict[str, Any],
        error: str
    ) -> None:
        """
        Handle download stage failure.
        
        Args:
            results: Results accumulation dictionary
            error: Error message
        """
        results['stage_failed'] = STAGE_NAME
        results['error'] = error
        self.logger.error(f"Download stage failed: {error}")


__all__ = ['DownloadStageProcessor']