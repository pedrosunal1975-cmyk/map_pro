# PATH: /map_pro/core/filing_stages/extraction_stage.py

"""
Extraction Stage Processor
==========================

Handles extraction stage of filing processing workflow.

Revolutionary Architecture:
- Checks own prerequisites before starting (engineer responsibility)
- Finds existing job or creates if missing (robust fallback)
- No dependency on job_workflow_manager (no dictator)
- Database as journalist (read metadata, write results)

Process Flow:
1. Check prerequisites (downloaded archive file exists)
2. Find existing extraction job (created by download stage)
3. If no job exists, create one (fallback for edge cases)
4. Wait for job completion
5. Success

Dependencies:
- ExtractionPrerequisitesChecker: Verifies prerequisites
- job_orchestrator: Job queue management
- JobWaiter: Wait for job completion
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.job_orchestrator import job_orchestrator
from database.models.core_models import Filing, ProcessingJob
from shared.constants.job_constants import JobType
from .extraction_prerequisites import ExtractionPrerequisitesChecker

logger = get_logger(__name__, 'core')

STAGE_NAME = 'extract'
STATUS_RUNNING = 'running'
STATUS_COMPLETED = 'completed'


class ExtractionStageProcessor:
    """
    Processes extraction stage for a filing.
    
    Responsible engineer: Checks prerequisites, finds/creates job.
    """
    
    def __init__(self, job_waiter):
        """
        Initialize extraction stage processor.
        
        Args:
            job_waiter: JobWaiter instance for waiting on jobs
        """
        self.logger = logger
        self.job_waiter = job_waiter
        self.prerequisites_checker = ExtractionPrerequisitesChecker()
    
    async def process(
        self,
        filing_id: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Process extraction stage for a filing.
        
        Revolutionary process:
        1. Check physical prerequisites
        2. Find existing job or create if missing
        3. Wait for job completion
        
        Args:
            filing_id: Filing universal ID
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
            
        Returns:
            True if extraction successful, False otherwise
        """
        workflow_status[STAGE_NAME] = STATUS_RUNNING
        
        try:
            # Step 1: Check physical prerequisites
            if not await self._verify_prerequisites(filing_id, results):
                return False
            
            # Step 2: Find existing job or create if needed
            job_id = await self._ensure_extraction_job(filing_id, results)
            if not job_id:
                return False
            
            # Step 3: Wait for job completion
            job_result = await self._wait_for_completion(job_id, results)
            if not job_result:
                return False
            
            # Success
            self._handle_success(workflow_status, results)
            return True
            
        except Exception as e:
            self.logger.error(f"Extraction stage failed for {filing_id}: {e}", exc_info=True)
            self._handle_failure(results, f'Unexpected error: {str(e)}')
            return False
    
    async def _verify_prerequisites(
        self,
        filing_id: str,
        results: Dict[str, Any]
    ) -> bool:
        """
        Verify all prerequisites are met for extraction.
        
        Args:
            filing_id: Filing universal ID
            results: Results dictionary for error reporting
            
        Returns:
            True if prerequisites met, False otherwise
        """
        self.logger.info(f"Checking extraction prerequisites for {filing_id}")
        
        prerequisites = self.prerequisites_checker.check_all_prerequisites(filing_id)
        
        if not prerequisites['ready']:
            self._log_prerequisite_status(prerequisites)
            error_msg = f"Prerequisites not met: {prerequisites['summary']}"
            self._handle_failure(results, error_msg)
            return False
        
        self.logger.info(
            f"All extraction prerequisites met for {filing_id}: "
            f"{prerequisites['summary']}"
        )
        return True
    
    def _log_prerequisite_status(self, prerequisites: Dict[str, Any]) -> None:
        """
        Log detailed prerequisite status for troubleshooting.
        
        Args:
            prerequisites: Prerequisites check result
        """
        self.logger.error("Extraction prerequisites not met:")
        
        archive = prerequisites['archive']
        
        if archive['ready']:
            self.logger.info(f"  [OK] Archive file: {archive['reason']}")
        else:
            self.logger.error(f"  [FAIL] Archive file: {archive['reason']}")
    
    async def _ensure_extraction_job(
        self,
        filing_id: str,
        results: Dict[str, Any]
    ) -> str:
        """
        Find existing extraction job or create if missing.
        
        Normal flow: Download stage creates the job, we find it.
        Fallback: If no job exists (edge case), create one.
        
        This approach handles both scenarios:
        - Primary: Find job created by download_coordinator
        - Fallback: Create job if somehow missing (robustness)
        
        Args:
            filing_id: Filing universal ID
            results: Results dictionary for error reporting
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            # First, try to find existing job (normal case)
            job_id = self._find_extraction_job(filing_id)
            
            if job_id:
                self.logger.info(f"Found existing extraction job: {job_id}")
                return job_id
            
            # No job found - create one (fallback for edge cases)
            self.logger.warning(
                f"No extraction job found for {filing_id}, creating one as fallback"
            )
            
            job_id = self._create_extraction_job(filing_id)
            
            if job_id:
                self.logger.info(f"Created extraction job: {job_id}")
                return job_id
            else:
                self._handle_failure(results, 'Failed to create extraction job')
                return None
                
        except Exception as e:
            self.logger.error(f"Error ensuring extraction job: {e}", exc_info=True)
            self._handle_failure(results, f'Job lookup/creation error: {str(e)}')
            return None
    
    def _find_extraction_job(self, filing_id: str) -> str:
        """
        Find extraction job for filing.
        
        Looks for queued or running extraction jobs for this filing.
        Download stage should have already created this job.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Job ID if found, None otherwise
        """
        try:
            with db_coordinator.get_session('core') as session:
                job = session.query(ProcessingJob).filter(
                    ProcessingJob.filing_universal_id == filing_id,
                    ProcessingJob.job_type == JobType.EXTRACT_FILES.value,
                    ProcessingJob.job_status.in_(['queued', 'running'])
                ).order_by(ProcessingJob.created_at.desc()).first()
                
                if job:
                    self.logger.debug(
                        f"Found extraction job {job.job_id} with status {job.job_status}"
                    )
                    return str(job.job_id)
                
                self.logger.debug(f"No extraction job found for filing {filing_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error finding extraction job: {e}")
            return None
    
    def _create_extraction_job(self, filing_id: str) -> str:
        """
        Create extraction job in job queue.
        
        Fallback mechanism when job doesn't exist.
        Normal flow: download_coordinator creates this job.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            # Get filing metadata (database as journalist)
            entity_id, market_type = self._get_filing_metadata(filing_id)
            
            if not entity_id:
                self.logger.error(f"Cannot get entity_id for filing {filing_id}")
                return None
            
            # Create job through orchestrator
            job_id = job_orchestrator.create_job(
                job_type=JobType.EXTRACT_FILES,
                entity_id=entity_id,
                market_type=market_type,
                parameters={'filing_universal_id': filing_id}
            )
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"Error creating extraction job: {e}", exc_info=True)
            return None
    
    def _get_filing_metadata(self, filing_id: str) -> tuple:
        """
        Get filing metadata from database.
        
        Database as journalist: Just reading reported metadata.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Tuple of (entity_id, market_type)
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter_by(
                    filing_universal_id=filing_id
                ).first()
                
                if not filing:
                    self.logger.error(f"Filing {filing_id} not found in database")
                    return None, 'unknown'
                
                if not filing.entity:
                    self.logger.error(f"Filing {filing_id} has no associated entity")
                    return None, 'unknown'
                
                if not filing.entity.market_type:
                    self.logger.error(f"Filing {filing_id} entity has no market_type specified")
                    return None, 'unknown'
                
                entity_id = str(filing.entity_universal_id)
                market_type = filing.entity.market_type
                
                return entity_id, market_type
                
        except Exception as e:
            self.logger.error(f"Error getting filing metadata: {e}")
            return None, 'unknown'
    
    async def _wait_for_completion(
        self,
        job_id: str,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Wait for extraction job to complete.
        
        Args:
            job_id: Job ID to wait for
            results: Results dictionary for error reporting
            
        Returns:
            Job result dictionary if successful, None otherwise
        """
        self.logger.info(f"Waiting for extraction job {job_id} to complete")
        
        try:
            job_result = await self.job_waiter.wait_for_job_completion(
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
        Handle successful extraction completion.
        
        Args:
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
        """
        workflow_status[STAGE_NAME] = STATUS_COMPLETED
        results['stages_completed'].append(STAGE_NAME)
        results['extract_completed'] = True
        
        self.logger.info("Extraction stage completed successfully")
    
    def _handle_failure(
        self,
        results: Dict[str, Any],
        error: str
    ) -> None:
        """
        Handle extraction stage failure.
        
        Args:
            results: Results accumulation dictionary
            error: Error message
        """
        results['stage_failed'] = STAGE_NAME
        results['error'] = error
        self.logger.error(f"Extraction stage failed: {error}")


__all__ = ['ExtractionStageProcessor']