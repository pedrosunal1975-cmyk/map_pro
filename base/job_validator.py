"""
Map Pro Job Processor - Job Validator
======================================

Location: engines/base/job_validator.py

Validates job data before processing.
"""

from typing import Dict, Any, TYPE_CHECKING

from core.system_logger import get_logger
from shared.constants.job_constants import JobType
from .job_processor_constants import REQUIRED_JOB_FIELDS

if TYPE_CHECKING:
    from .engine_base import BaseEngine


class JobValidator:
    """
    Validates job data to ensure it meets requirements.
    
    Responsibilities:
    - Validating required fields presence
    - Validating job type support
    - Special validation for different job types (e.g., MAP_FACTS)
    """
    
    def __init__(self, engine: 'BaseEngine') -> None:
        """
        Initialize job validator.
        
        Args:
            engine: The engine instance
        """
        self.engine = engine
        self.logger = get_logger(f"engines.{engine.engine_name}.validator", 'engine')
    
    def validate_job_data(self, job_data: Dict[str, Any]) -> bool:
        """
        Validate that job data contains required fields and is valid.
        
        Args:
            job_data: Job data to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self._validate_required_fields(job_data):
            return False
        
        if not self._validate_job_type_supported(job_data):
            return False
        
        if not self._validate_job_specific_requirements(job_data):
            return False
        
        return True
    
    def _validate_required_fields(self, job_data: Dict[str, Any]) -> bool:
        """
        Validate that all required fields are present.
        
        Args:
            job_data: Job data to validate
            
        Returns:
            True if all required fields present, False otherwise
        """
        for field in REQUIRED_JOB_FIELDS:
            if field not in job_data:
                self.logger.error(
                    f"Missing required field '{field}' in job data"
                )
                return False
        
        return True
    
    def _validate_job_type_supported(self, job_data: Dict[str, Any]) -> bool:
        """
        Validate that the job type is supported by this engine.
        
        Args:
            job_data: Job data to validate
            
        Returns:
            True if job type supported, False otherwise
        """
        job_type_value = self._extract_job_type_value(job_data['job_type'])
        
        if job_type_value not in self.engine.get_supported_job_types():
            self.logger.error(f"Unsupported job type: {job_data['job_type']}")
            return False
        
        return True
    
    def _extract_job_type_value(self, job_type: Any) -> str:
        """
        Extract job type string value from enum or string.
        
        Args:
            job_type: Job type (may be enum or string)
            
        Returns:
            Job type as string
        """
        if hasattr(job_type, 'value'):
            return job_type.value
        return job_type
    
    def _validate_job_specific_requirements(self, job_data: Dict[str, Any]) -> bool:
        """
        Validate job-specific requirements based on job type.
        
        SAFE FIX: Special handling for MAP_FACTS jobs only, preserve original for others.
        
        Args:
            job_data: Job data to validate
            
        Returns:
            True if job-specific requirements met, False otherwise
        """
        job_type = job_data.get('job_type')
        job_type_str = self._extract_job_type_value(job_type)
        
        if job_type_str == JobType.MAP_FACTS.value:
            return self._validate_map_facts_job(job_data)
        else:
            return self._validate_standard_job(job_data, job_type_str)
    
    def _validate_map_facts_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Validate MAP_FACTS job requirements.
        
        For mapping jobs, check for filing_universal_id instead of entity_id.
        
        Args:
            job_data: Job data to validate
            
        Returns:
            True if MAP_FACTS requirements met, False otherwise
        """
        filing_id = self._extract_filing_id(job_data)
        
        if not filing_id:
            self.logger.error(
                "MAP_FACTS job missing filing_universal_id in parameters"
            )
            return False
        
        return True
    
    def _extract_filing_id(self, job_data: Dict[str, Any]) -> Any:
        """
        Extract filing ID from various possible locations in job data.
        
        Args:
            job_data: Job data to extract filing ID from
            
        Returns:
            Filing ID if found, None otherwise
        """
        parameters = job_data.get('parameters', {})
        
        # Try multiple possible locations for filing ID
        filing_id = (
            parameters.get('filing_universal_id') or
            job_data.get('filing_universal_id') or
            parameters.get('filing_id')
        )
        
        return filing_id
    
    def _validate_standard_job(
        self, 
        job_data: Dict[str, Any], 
        job_type_str: str
    ) -> bool:
        """
        Validate standard job requirements (non-MAP_FACTS).
        
        PRESERVE ORIGINAL: For all other job types, entity_id is still required.
        
        Args:
            job_data: Job data to validate
            job_type_str: Job type as string
            
        Returns:
            True if standard requirements met, False otherwise
        """
        if 'entity_id' not in job_data:
            self.logger.error(
                f"Missing required field 'entity_id' in job data for {job_type_str}"
            )
            return False
        
        return True