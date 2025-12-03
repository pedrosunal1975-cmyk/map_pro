# PATH: /map_pro/core/filing_stages/mapping_stage.py

"""
Mapping Stage Processor
=======================

Handles mapping stage of filing processing workflow.

Revolutionary Architecture:
- Checks own prerequisites before starting (engineer responsibility)
- Creates own job when prerequisites met (takes initiative)
- No dependency on job_workflow_manager (no dictator)
- Database as journalist (read metadata, write results)

Process Flow:
1. Check prerequisites (XBRL files, facts.json, libraries)
2. Create map job if prerequisites met
3. Wait for job completion
4. Verify output exists

Dependencies:
- MappingPrerequisitesChecker: Verifies prerequisites
- job_orchestrator: Job queue management
- output_verifier: Physical output verification
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.job_orchestrator import job_orchestrator
from database.models.core_models import Filing, ProcessingJob  # FIXED: Added ProcessingJob import
from shared.constants.job_constants import JobType
from .mapping_prerequisites import MappingPrerequisitesChecker

logger = get_logger(__name__, 'core')

STAGE_NAME = 'map'
STATUS_RUNNING = 'running'
STATUS_COMPLETED = 'completed'


class MappingStageProcessor:
    """
    Processes mapping stage for a filing.
    
    Responsible engineer: Checks prerequisites, creates job, verifies output.
    """
    
    def __init__(self, job_waiter, output_verifier):
        """
        Initialize mapping stage processor.
        
        Args:
            job_waiter: JobWaiter instance for waiting on jobs
            output_verifier: OutputVerifier instance for reality checks
        """
        self.logger = logger
        self.job_waiter = job_waiter
        self.output_verifier = output_verifier
        self.prerequisites_checker = MappingPrerequisitesChecker()
    
    async def process(
        self,
        filing_id: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Process mapping stage for a filing.
        
        Revolutionary process:
        1. Check physical prerequisites
        2. Create job if ready (take initiative)
        3. Wait for job completion
        4. Verify physical output
        
        Args:
            filing_id: Filing universal ID
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
            
        Returns:
            True if mapping successful, False otherwise
        """
        workflow_status[STAGE_NAME] = STATUS_RUNNING
        
        try:
            # Step 1: Check physical prerequisites
            if not await self._verify_prerequisites(filing_id, results):
                return False
            
            # Step 2: Ensure job exists (create if needed)
            job_id = await self._ensure_mapping_job(filing_id, results)
            if not job_id:
                return False
            
            # Step 3: Wait for job completion
            job_result = await self._wait_for_completion(job_id, results)
            if not job_result:
                return False
            
            # Step 4: Verify physical output
            if not self._verify_output(filing_id, job_result, results):
                return False
            
            # Success
            self._handle_success(workflow_status, results, filing_id, job_result)
            return True
            
        except Exception as e:
            self.logger.error(f"Mapping stage failed for {filing_id}: {e}", exc_info=True)
            self._handle_failure(results, f'Unexpected error: {str(e)}')
            return False
    
    async def _verify_prerequisites(
        self,
        filing_id: str,
        results: Dict[str, Any]
    ) -> bool:
        """
        Verify all prerequisites are met for mapping.
        
        Args:
            filing_id: Filing universal ID
            results: Results dictionary for error reporting
            
        Returns:
            True if prerequisites met, False otherwise
        """
        self.logger.info(f"Checking mapping prerequisites for {filing_id}")
        
        prerequisites = self.prerequisites_checker.check_all_prerequisites(filing_id)
        
        if not prerequisites['ready']:
            self._log_prerequisite_status(prerequisites)
            error_msg = f"Prerequisites not met: {prerequisites['summary']}"
            self._handle_failure(results, error_msg)
            return False
        
        self.logger.info(
            f"All mapping prerequisites met for {filing_id}: "
            f"{prerequisites['summary']}"
        )
        return True
    
    def _log_prerequisite_status(self, prerequisites: Dict[str, Any]) -> None:
        """
        Log detailed prerequisite status for troubleshooting.
        
        Args:
            prerequisites: Prerequisites check result
        """
        self.logger.error("Mapping prerequisites not met:")
        
        xbrl = prerequisites['xbrl']
        facts = prerequisites['facts']
        libs = prerequisites['libraries']
        
        # Log XBRL status
        if xbrl['ready']:
            self.logger.info(f"  [OK] XBRL files: {xbrl['reason']}")
        else:
            self.logger.error(f"  [FAIL] XBRL files: {xbrl['reason']}")
        
        # Log facts status
        if facts['ready']:
            self.logger.info(f"  [OK] facts.json: {facts['reason']}")
        else:
            self.logger.error(f"  [FAIL] facts.json: {facts['reason']}")
        
        # Log libraries status
        if libs['ready']:
            self.logger.info(f"  [OK] Libraries: {libs['reason']}")
        else:
            self.logger.error(f"  [FAIL] Libraries: {libs['reason']}")
    
    async def _ensure_mapping_job(
        self,
        filing_id: str,
        results: Dict[str, Any]
    ) -> str:
        """
        Ensure mapping job exists, create if needed.
        
        Engineer takes initiative: Prerequisites verified, create own job.
        
        Args:
            filing_id: Filing universal ID
            results: Results dictionary for error reporting
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            # First, try to find existing job
            job_id = self._find_mapping_job(filing_id)
            
            if job_id:
                self.logger.info(f"Found existing mapping job: {job_id}")
                return job_id
            
            # No job found - create one (engineer's initiative)
            self.logger.info(
                f"Creating mapping job for {filing_id} (prerequisites verified)"
            )
            
            job_id = self._create_mapping_job(filing_id)
            
            if job_id:
                self.logger.info(f"Created mapping job: {job_id}")
                return job_id
            else:
                self._handle_failure(results, 'Failed to create mapping job')
                return None
                
        except Exception as e:
            self.logger.error(f"Error ensuring mapping job: {e}", exc_info=True)
            self._handle_failure(results, f'Job creation error: {str(e)}')
            return None
    
    def _find_mapping_job(self, filing_id: str) -> Optional[str]:
        """
        Find mapping job for filing.
        
        Looks for queued or running mapping jobs for this filing.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Job ID if found, None otherwise
        """
        try:
            with db_coordinator.get_session('core') as session:
                job = session.query(ProcessingJob).filter(
                    ProcessingJob.filing_universal_id == filing_id,
                    ProcessingJob.job_type == JobType.MAP_FACTS.value,
                    ProcessingJob.job_status.in_(['queued', 'running'])
                ).order_by(ProcessingJob.created_at.desc()).first()
                
                if job:
                    self.logger.debug(
                        f"Found mapping job {job.job_id} with status {job.job_status}"
                    )
                    return str(job.job_id)
                
                self.logger.debug(f"No mapping job found for filing {filing_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error finding mapping job: {e}")
            return None
    
    def _create_mapping_job(self, filing_id: str) -> str:
        """
        Create mapping job in job queue.
        
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
                job_type=JobType.MAP_FACTS,
                entity_id=entity_id,
                market_type=market_type,
                parameters={'filing_universal_id': filing_id}
            )
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"Error creating mapping job: {e}", exc_info=True)
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
        Wait for mapping job to complete.
        
        Args:
            job_id: Job ID to wait for
            results: Results dictionary for error reporting
            
        Returns:
            Job result dictionary if successful, None otherwise
        """
        self.logger.info(f"Waiting for mapping job {job_id} to complete")
        
        try:
            job_result = await self.job_waiter.wait_for_job_completion(
                job_id,
                STAGE_NAME
            )
            
            if not job_result:
                self._handle_failure(results, 'Job completion timeout')
                return None
            
            return job_result
            
        except Exception as e:
            self.logger.error(f"Error waiting for job completion: {e}", exc_info=True)
            self._handle_failure(results, f'Job wait error: {str(e)}')
            return None
    
    def _verify_output(
        self,
        filing_id: str,
        job_result: Dict[str, Any],
        results: Dict[str, Any]
    ) -> bool:
        """
        Verify mapping output exists physically.
        
        Trust reality (files) over metadata (database) if mismatch.
        
        Args:
            filing_id: Filing universal ID
            job_result: Result from completed job
            results: Results dictionary for error reporting
            
        Returns:
            True if output verified, False otherwise
        """
        db_success = job_result.get('success', False)
        files_exist = self.output_verifier.verify_mapping_output(filing_id)
        
        # Both agree it failed
        if not db_success and not files_exist:
            self.logger.error(
                f"Mapping failed for {filing_id}: "
                f"Database reports failure and no output files found"
            )
            self._handle_failure(results, 'Mapping failed with no output')
            return False
        
        # Database says failed but files exist (trust reality!)
        if not db_success and files_exist:
            self.logger.warning(
                f"Database reports mapping failed for {filing_id} "
                f"but output files exist - trusting physical reality"
            )
        
        return True
    
    def _handle_success(
        self,
        workflow_status: Dict[str, str],
        results: Dict[str, Any],
        filing_id: str,
        job_result: Dict[str, Any]
    ) -> None:
        """
        Handle successful mapping completion.
        
        Args:
            workflow_status: Workflow status tracking dictionary
            results: Results accumulation dictionary
            filing_id: Filing universal ID
            job_result: Result from completed job
        """
        workflow_status[STAGE_NAME] = STATUS_COMPLETED
        results['stages_completed'].append(STAGE_NAME)
        results['map_completed'] = True
        
        # Extract statistics from job result
        results['facts_mapped'] = job_result.get('mapped_facts', 0)
        results['total_facts'] = job_result.get('total_facts', 0)
        results['unmapped_facts'] = job_result.get('unmapped_facts', 0)
        results['success_rate'] = job_result.get('success_rate', 0.0)
        results['statements_created'] = job_result.get('statements_created', 0)
        
        self.logger.info(
            f"Mapping completed for {filing_id}: "
            f"{results['facts_mapped']}/{results['total_facts']} facts mapped "
            f"({results['success_rate']:.1f}% success rate)"
        )
    
    def _handle_failure(
        self,
        results: Dict[str, Any],
        error: str
    ) -> None:
        """
        Handle mapping stage failure.
        
        Args:
            results: Results accumulation dictionary
            error: Error message
        """
        results['stage_failed'] = STAGE_NAME
        results['error'] = error
        self.logger.error(f"Mapping stage failed: {error}")


__all__ = ['MappingStageProcessor']