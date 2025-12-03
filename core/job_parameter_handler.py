# File: /map_pro/core/job_parameter_handler.py

"""
Job Parameter Handler
=====================

Handles parameter processing for job operations.
Manages UUID conversions and parameter validation.
"""

import uuid as uuid_module
from typing import Dict, Any, Optional

from .system_logger import get_logger

logger = get_logger(__name__, 'core')


class JobParameterHandler:
    """
    Handles job parameter processing.
    
    Responsibilities:
    - Convert UUIDs to strings recursively
    - Process and clean parameters
    - Extract specific parameter values
    - Ensure required parameters are present
    """
    
    def __init__(self):
        """Initialize job parameter handler."""
        self.logger = logger
    
    def process_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process parameters by converting UUIDs to strings.
        
        Args:
            parameters: Raw parameters dictionary
            
        Returns:
            Processed parameters with UUIDs converted to strings
        """
        return self._convert_uuids_to_strings(parameters)
    
    def extract_filing_id(self, parameters: Dict[str, Any]) -> Optional[str]:
        """
        Extract filing_universal_id from parameters.
        
        Args:
            parameters: Job parameters
            
        Returns:
            Filing ID as string or None
        """
        filing_id = parameters.get('filing_universal_id')
        return str(filing_id) if filing_id else None
    
    def ensure_entity_in_parameters(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure entity_id is present in job parameters.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Updated job data with entity_id in parameters
        """
        entity_id = job_data.get('entity_id')
        parameters = job_data.get('parameters', {})
        
        if entity_id and 'entity_id' not in parameters:
            parameters['entity_id'] = entity_id
            job_data['parameters'] = parameters
            
            self.logger.debug(f"Added entity_id to parameters: {entity_id}")
        
        return job_data
    
    def _convert_uuids_to_strings(self, data: Any) -> Any:
        """
        Convert UUID objects to strings recursively in data structures.
        
        Args:
            data: Data structure potentially containing UUIDs
            
        Returns:
            Data with UUIDs converted to strings
        """
        if isinstance(data, uuid_module.UUID):
            return str(data)
        elif isinstance(data, dict):
            return {
                key: self._convert_uuids_to_strings(value) 
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._convert_uuids_to_strings(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self._convert_uuids_to_strings(item) for item in data)
        else:
            return data


# Backward compatibility: Export function for existing code
def convert_uuids_to_strings(data: Any) -> Any:
    """
    Convert UUID objects to strings recursively in data structures.
    
    Convenience function for backward compatibility.
    
    Args:
        data: Data structure potentially containing UUIDs
        
    Returns:
        Data with UUIDs converted to strings
    """
    handler = JobParameterHandler()
    return handler._convert_uuids_to_strings(data)


__all__ = ['JobParameterHandler', 'convert_uuids_to_strings']