# File: /map_pro/core/job_database_operations.py

"""
Job Database Operations
========================

Abstraction layer for job-related database operations.
Encapsulates all SQL queries and database interactions.

This provides the abstraction needed to reduce concrete dependencies
and improve testability (DIP principle).
"""

import uuid as uuid_module
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy import text

from .system_logger import get_logger
from .database_coordinator import get_database_session
from shared.constants.job_constants import JobType, JobStatus, JobPriority

from .job_orchestrator_constants import (
    DEFAULT_FETCH_LIMIT,
    QUEUE_STATS_LOOKBACK_HOURS
)

logger = get_logger(__name__, 'core')


class JobDatabaseOperations:
    """
    Database operations for job management.
    
    Responsibilities:
    - Execute all database queries for jobs
    - Handle transaction management
    - Parse database results
    - Convert between database and application formats
    
    This class provides the abstraction layer that reduces
    concrete dependencies in JobOrchestrator.
    """
    
    def __init__(self):
        """Initialize job database operations."""
        self.logger = logger
    
    def create_job(
        self,
        job_type: JobType,
        entity_id: str,
        filing_id: Optional[str],
        market_type: str,
        parameters: Dict[str, Any],
        priority: JobPriority
    ) -> str:
        """
        Create new job in database.
        
        Args:
            job_type: Type of job
            entity_id: Entity universal ID
            filing_id: Filing universal ID (optional)
            market_type: Market type
            parameters: Job parameters
            priority: Job priority
            
        Returns:
            Created job ID
            
        Raises:
            Exception: If job creation fails
        """
        job_id = str(uuid_module.uuid4())
        entity_id_str = str(entity_id) if entity_id else None
        filing_id_str = str(filing_id) if filing_id else None
        
        self.logger.debug(
            f"Creating job {job_id} of type {job_type.value} "
            f"for entity {entity_id_str}, filing {filing_id_str}"
        )
        
        try:
            with get_database_session('core') as session:
                session.execute(
                    text(
                        """
                        INSERT INTO processing_jobs 
                        (job_id, job_type, job_status, job_priority, entity_universal_id, 
                        filing_universal_id, job_parameters, created_at, updated_at)
                        VALUES (:job_id, :job_type, :job_status, :job_priority, :entity_id,
                                :filing_id, :job_parameters, :created_at, :updated_at)
                        """
                    ),
                    {
                        'job_id': job_id,
                        'job_type': job_type.value,
                        'job_status': JobStatus.QUEUED.value,
                        'job_priority': priority.value,
                        'entity_id': entity_id_str,
                        'filing_id': filing_id_str,
                        'job_parameters': json.dumps(parameters),
                        'created_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc)
                    }
                )
                session.commit()
            
            self.logger.debug(f"Job {job_id} created successfully")
            return job_id
            
        except Exception as exception:
            self.logger.error(f"Failed to create job: {exception}", exc_info=True)
            raise
    
    def fetch_and_lock_job(
        self,
        job_types: List[JobType]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch next available job and lock it.
        
        Args:
            job_types: List of acceptable job types
            
        Returns:
            Job data dictionary or None if no jobs available
        """
        try:
            with get_database_session('core') as session:
                job_type_values = [jt.value for jt in job_types]
                
                result = session.execute(
                    text(
                        """
                        SELECT job_id, job_type, entity_universal_id, job_parameters, job_priority
                        FROM processing_jobs 
                        WHERE job_status = :status 
                        AND job_type = ANY(:job_types)
                        ORDER BY job_priority DESC, created_at ASC
                        LIMIT :limit
                        FOR UPDATE SKIP LOCKED
                        """
                    ),
                    {
                        'status': JobStatus.QUEUED.value,
                        'job_types': job_type_values,
                        'limit': DEFAULT_FETCH_LIMIT
                    }
                ).fetchone()
                
                if not result:
                    return None
                
                job_id, job_type, entity_id_raw, parameters_json, priority = result
                
                # Parse and structure job data
                job_data = self._parse_job_data(
                    job_id=job_id,
                    job_type=job_type,
                    entity_id_raw=entity_id_raw,
                    parameters_json=parameters_json,
                    priority=priority
                )
                
                self.logger.debug(f"Fetched and locked job {job_id}")
                return job_data
                
        except Exception as exception:
            self.logger.error(f"Failed to fetch next job: {exception}", exc_info=True)
            return None
    
    def mark_job_running(self, job_id: str) -> None:
        """
        Mark job as running.
        
        Args:
            job_id: Job ID to update
        """
        try:
            with get_database_session('core') as session:
                session.execute(
                    text(
                        """
                        UPDATE processing_jobs 
                        SET job_status = :status, started_at = :started_at, updated_at = :updated_at
                        WHERE job_id = :job_id
                        """
                    ),
                    {
                        'status': JobStatus.RUNNING.value,
                        'started_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                        'job_id': job_id
                    }
                )
                session.commit()
            
            self.logger.debug(f"Job {job_id} marked as running")
            
        except Exception as exception:
            self.logger.error(
                f"Failed to mark job {job_id} as running: {exception}",
                exc_info=True
            )
            raise
    
    def mark_job_completed(
        self,
        job_id: str,
        result_data: Optional[Dict[str, Any]]
    ) -> None:
        """
        Mark job as completed.
        
        Args:
            job_id: Job ID to complete
            result_data: Optional result data
        """
        try:
            with get_database_session('core') as session:
                session.execute(
                    text(
                        """
                        UPDATE processing_jobs 
                        SET job_status = :status, 
                            completed_at = :completed_at, 
                            updated_at = :updated_at,
                            job_result = :job_result
                        WHERE job_id = :job_id
                        """
                    ),
                    {
                        'status': JobStatus.COMPLETED.value,
                        'completed_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                        'job_id': job_id,
                        'job_result': json.dumps(result_data) if result_data else None
                    }
                )
                session.commit()
            
            self.logger.debug(f"Job {job_id} marked as completed")
            
        except Exception as exception:
            self.logger.error(
                f"Failed to complete job {job_id}: {exception}",
                exc_info=True
            )
            raise
    
    def mark_job_for_retry(
        self,
        job_id: str,
        retry_count: int,
        error_message: str
    ) -> None:
        """
        Mark job for retry.
        
        Args:
            job_id: Job ID to retry
            retry_count: New retry count
            error_message: Error that occurred
        """
        try:
            with get_database_session('core') as session:
                session.execute(
                    text(
                        """
                        UPDATE processing_jobs 
                        SET job_status = :status, retry_count = :retry_count, 
                            error_message = :error_message, updated_at = :updated_at
                        WHERE job_id = :job_id
                        """
                    ),
                    {
                        'status': JobStatus.QUEUED.value,
                        'retry_count': retry_count,
                        'error_message': error_message,
                        'updated_at': datetime.now(timezone.utc),
                        'job_id': job_id
                    }
                )
                session.commit()
            
            self.logger.debug(f"Job {job_id} queued for retry (attempt {retry_count})")
            
        except Exception as exception:
            self.logger.error(
                f"Failed to queue job {job_id} for retry: {exception}",
                exc_info=True
            )
            raise
    
    def mark_job_failed(self, job_id: str, error_message: str) -> None:
        """
        Mark job as permanently failed.
        
        Args:
            job_id: Job ID to fail
            error_message: Final error message
        """
        try:
            with get_database_session('core') as session:
                session.execute(
                    text(
                        """
                        UPDATE processing_jobs 
                        SET job_status = :status, error_message = :error_message, 
                            updated_at = :updated_at
                        WHERE job_id = :job_id
                        """
                    ),
                    {
                        'status': JobStatus.FAILED.value,
                        'error_message': error_message,
                        'updated_at': datetime.now(timezone.utc),
                        'job_id': job_id
                    }
                )
                session.commit()
            
            self.logger.debug(f"Job {job_id} marked as permanently failed")
            
        except Exception as exception:
            self.logger.error(
                f"Failed to mark job {job_id} as failed: {exception}",
                exc_info=True
            )
            raise
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get basic job information.
        
        Args:
            job_id: Job ID to query
            
        Returns:
            Dictionary with job_type and retry_count or None
        """
        try:
            with get_database_session('core') as session:
                result = session.execute(
                    text(
                        """
                        SELECT job_type, retry_count 
                        FROM processing_jobs 
                        WHERE job_id = :job_id
                        """
                    ),
                    {'job_id': job_id}
                ).fetchone()
                
                if not result:
                    return None
                
                job_type, retry_count = result
                
                return {
                    'job_type': job_type,
                    'retry_count': retry_count if retry_count else 0
                }
                
        except Exception as exception:
            self.logger.error(
                f"Failed to get job info for {job_id}: {exception}",
                exc_info=True
            )
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete job status.
        
        Args:
            job_id: Job ID to query
            
        Returns:
            Complete job data dictionary or None
        """
        try:
            with get_database_session('core') as session:
                result = session.execute(
                    text(
                        """
                        SELECT job_id, job_type, job_status, job_priority, entity_universal_id,
                               job_parameters, job_result, started_at, completed_at, error_message,
                               retry_count, created_at, updated_at
                        FROM processing_jobs 
                        WHERE job_id = :job_id
                        """
                    ),
                    {'job_id': job_id}
                ).fetchone()
                
                if not result:
                    return None
                
                job_data = dict(result._mapping)
                
                # Convert UUID to string if present
                if job_data.get('entity_universal_id'):
                    job_data['entity_universal_id'] = str(job_data['entity_universal_id'])
                
                return job_data
                
        except Exception as exception:
            self.logger.error(
                f"Failed to get job status for {job_id}: {exception}",
                exc_info=True
            )
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a queued job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled, False otherwise
        """
        try:
            with get_database_session('core') as session:
                result = session.execute(
                    text(
                        """
                        UPDATE processing_jobs 
                        SET job_status = :new_status, updated_at = :updated_at
                        WHERE job_id = :job_id AND job_status = :old_status
                        """
                    ),
                    {
                        'new_status': JobStatus.CANCELLED.value,
                        'old_status': JobStatus.QUEUED.value,
                        'updated_at': datetime.now(timezone.utc),
                        'job_id': job_id
                    }
                )
                session.commit()
                
                rows_affected = result.rowcount
                return rows_affected > 0
                
        except Exception as exception:
            self.logger.error(
                f"Failed to cancel job {job_id}: {exception}",
                exc_info=True
            )
            return False
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about job queue.
        
        Returns:
            Dictionary with queue statistics by status
        """
        try:
            with get_database_session('core') as session:
                result = session.execute(
                    text(
                        """
                        SELECT 
                            job_status,
                            COUNT(*) as count
                        FROM processing_jobs 
                        WHERE created_at > NOW() - INTERVAL ':hours hours'
                        GROUP BY job_status
                        """
                    ),
                    {'hours': QUEUE_STATS_LOOKBACK_HOURS}
                ).fetchall()
                
                stats = {row[0]: row[1] for row in result}
                stats['total'] = sum(stats.values())
                
                return stats
                
        except Exception as exception:
            self.logger.error(
                f"Failed to get queue stats: {exception}",
                exc_info=True
            )
            return {}
    
    def _parse_job_data(
        self,
        job_id: str,
        job_type: str,
        entity_id_raw: Any,
        parameters_json: Any,
        priority: int
    ) -> Dict[str, Any]:
        """
        Parse raw database job data into structured format.
        
        Args:
            job_id: Job ID
            job_type: Job type string
            entity_id_raw: Raw entity ID from database
            parameters_json: Parameters as JSON or dict
            priority: Priority value
            
        Returns:
            Structured job data dictionary
        """
        # Convert entity ID
        entity_id = str(entity_id_raw) if entity_id_raw else None
        
        # Parse parameters
        parameters = self._parse_parameters(parameters_json, job_id)
        
        return {
            'job_id': job_id,
            'job_type': job_type,
            'entity_id': entity_id,
            'parameters': parameters,
            'priority': JobPriority(priority)
        }
    
    def _parse_parameters(self, parameters_json: Any, job_id: str) -> Dict[str, Any]:
        """
        Parse parameters from JSON or dict.
        
        Args:
            parameters_json: Parameters as JSON string or dict
            job_id: Job ID for error logging
            
        Returns:
            Parameters dictionary
        """
        if isinstance(parameters_json, dict):
            self.logger.debug(f"Parameters already dict for job {job_id}")
            return parameters_json
        elif parameters_json:
            try:
                params = json.loads(parameters_json)
                self.logger.debug(f"Parsed JSON parameters for job {job_id}")
                return params
            except (json.JSONDecodeError, TypeError) as exception:
                self.logger.error(
                    f"Failed to parse parameters for job {job_id}: {exception}"
                )
                return {}
        else:
            self.logger.debug(f"No parameters for job {job_id}")
            return {}


__all__ = ['JobDatabaseOperations']