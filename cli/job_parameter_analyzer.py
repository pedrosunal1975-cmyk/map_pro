"""
Database Schema Verification - Job Parameter Analyzer
======================================================

Location: tools/cli/job_parameter_analyzer.py

Analyzes job parameters for debugging purposes.
"""

import json
from typing import Dict, Any, Optional

from .db_check_constants import DiagnosticMessages
from .db_check_models import EntityAnalysis


class JobParameterAnalyzer:
    """Analyzes job parameters for debugging purposes."""
    
    @staticmethod
    def parse_parameters(parameters_json: Any) -> Dict[str, Any]:
        """
        Parse job parameters from various formats.
        
        Args:
            parameters_json: Parameters in JSON or dict format
            
        Returns:
            Parsed parameters dictionary
        """
        if isinstance(parameters_json, dict):
            return parameters_json
        
        if parameters_json:
            try:
                return json.loads(parameters_json)
            except json.JSONDecodeError as e:
                print(DiagnosticMessages.ERROR_JSON_PARSE.format(e))
                return {}
        
        return {}
    
    @staticmethod
    def print_parameter_details(parameters: Dict[str, Any]) -> None:
        """
        Print detailed information about job parameters.
        
        Args:
            parameters: Dictionary of parameters
        """
        print(DiagnosticMessages.INFO_PARSED_PARAMS)
        if parameters:
            for key, value in parameters.items():
                print(f"   {key}: {value} (type: {type(value).__name__})")
        else:
            print(DiagnosticMessages.WARNING_NO_PARAMETERS)
    
    @staticmethod
    def analyze_entity_id(
        entity_id_raw: Optional[str], 
        parameters: Dict[str, Any]
    ) -> EntityAnalysis:
        """
        Analyze entity ID from both database column and parameters.
        
        Args:
            entity_id_raw: Entity ID from database column
            parameters: Job parameters dictionary
            
        Returns:
            EntityAnalysis object with analysis results
        """
        entity_id_from_params = parameters.get('entity_id')
        
        return EntityAnalysis(
            db_column=entity_id_raw,
            from_parameters=entity_id_from_params,
            param_type=type(entity_id_from_params).__name__ if entity_id_from_params else 'None',
            param_valid=bool(entity_id_from_params) if entity_id_from_params is not None else False
        )