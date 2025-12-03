"""
Download Job Processor
=====================

Handles job data extraction and result formatting for download jobs.
Separates job processing logic from download execution.
"""

from typing import Dict, Any

from shared.exceptions.custom_exceptions import EngineError


class DownloadJobProcessor:
    """
    Processes download job data and formats results.
    
    Responsibilities:
    - Extract filing_id from various job data structures
    - Create standardized result dictionaries
    - Handle error formatting
    """
    
    def __init__(self, logger):
        """
        Initialize job processor.
        
        Args:
            logger: Logger instance for error reporting
        """
        self.logger = logger
    
    def extract_filing_id(self, job_data: Dict[str, Any]) -> str:
        """
        Extract filing_universal_id from job data.
        
        Handles multiple job data structures for compatibility.
        
        Args:
            job_data: Job information dictionary
            
        Returns:
            Filing universal ID
            
        Raises:
            EngineError: If filing_id cannot be extracted
        """
        parameters = job_data.get('parameters', {})
        filing_id = (
            parameters.get('filing_universal_id') or 
            job_data.get('filing_universal_id')
        )
        
        if not filing_id:
            self._log_extraction_error(job_data, parameters)
            raise EngineError("Missing filing_universal_id in job data")
        
        return filing_id
    
    def _log_extraction_error(
        self,
        job_data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> None:
        """
        Log detailed error information for missing filing_id.
        
        Args:
            job_data: Original job data
            parameters: Parameters section of job data
        """
        self.logger.error("Missing filing_universal_id in job data")
        self.logger.error(f"Available job_data keys: {list(job_data.keys())}")
        self.logger.error(f"Available parameters keys: {list(parameters.keys())}")

    def create_result_dict(
        self,
        result,
        filing_id: str
    ) -> Dict[str, Any]:
        """
        Create standardized result dictionary from download result.
        
        Args:
            result: DownloadResult object
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with standardized result format
        """
        return {
            'success': result.success,
            'filing_id': filing_id,
            'error_message': result.error_message if not result.success else None,
            'file_size_bytes': getattr(result, 'file_size_bytes', 0),
            'duration_seconds': getattr(result, 'duration_seconds', 0.0)
        }
    
    def create_error_dict(self, filing_id: str, error_message: str) -> Dict[str, Any]:
        """
        Create standardized error result dictionary.
        
        Args:
            filing_id: Filing universal ID
            error_message: Error message
            
        Returns:
            Dictionary with error information
        """
        return {
            'success': False,
            'filing_id': filing_id,
            'error_message': f"Download processing failed: {error_message}"
        }