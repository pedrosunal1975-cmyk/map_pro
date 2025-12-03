# File: /map_pro/engines/librarian/dependency_analysis_validator.py

"""
Dependency Analysis Validator
==============================

Validates filings and locates required data files for dependency analysis.
Handles filing validation, facts.json file discovery, and database checks.

Responsibilities:
- Filing existence validation
- Facts.json file discovery
- Parsed data verification
- Error reporting
"""

import traceback
from typing import Dict, Any, List
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from core.database_coordinator import db_coordinator
from database.models.core_models import Filing

logger = get_logger(__name__, 'engine')

# File search constants
FACTS_JSON_FILENAME = 'facts.json'


class DependencyAnalysisValidator:
    """
    Validates filing requirements for dependency analysis.
    
    Workflow:
    1. Check filing exists in database
    2. Locate parsed facts directory
    3. Find facts.json files
    4. Return validation result with file path
    """
    
    def __init__(self):
        """Initialize validator."""
        logger.debug("Dependency analysis validator initialized")
    
    async def validate_filing(self, filing_id: str) -> Dict[str, Any]:
        """
        Validate filing and locate facts.json file.
        
        Uses flexible search to find JSON files regardless of database entity info.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - valid: bool
                - error: Optional[str]
                - facts_json_path: Optional[str]
        """
        try:
            # Step 1: Verify filing exists in database
            filing_exists = self._check_filing_exists(filing_id)
            if not filing_exists['valid']:
                return filing_exists
            
            # Step 2: Locate facts directory
            facts_dir = map_pro_paths.data_parsed_facts
            if not facts_dir.exists():
                return {
                    'valid': False,
                    'error': f'Parsed facts directory not found: {facts_dir}'
                }
            
            # Step 3: Find facts.json files
            facts_json_files = self._find_facts_json_files(facts_dir)
            if not facts_json_files:
                return {
                    'valid': False,
                    'error': f'No facts JSON files found in {facts_dir}'
                }
            
            # Use first available facts.json file
            facts_json_path = facts_json_files[0]
            
            logger.info(
                f"Found {len(facts_json_files)} facts.json files, "
                f"using: {facts_json_path}"
            )
            
            return {
                'valid': True,
                'facts_json_path': str(facts_json_path)
            }
            
        except Exception as e:
            logger.error(f"Filing validation error for {filing_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }
    
    def _check_filing_exists(self, filing_id: str) -> Dict[str, Any]:
        """
        Check if filing exists in database.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with validation result
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter(
                    Filing.filing_universal_id == filing_id
                ).first()
                
                if not filing:
                    logger.warning(f"Filing {filing_id} not found in database")
                    return {
                        'valid': False,
                        'error': f'Filing {filing_id} not found'
                    }
                
                logger.debug(f"Filing {filing_id} found in database")
                return {'valid': True}
                
        except Exception as e:
            logger.error(f"Database error checking filing {filing_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'valid': False,
                'error': f'Database error: {str(e)}'
            }
    
    def _find_facts_json_files(self, facts_dir: Path) -> List[Path]:
        """
        Find all facts.json files in directory tree.
        
        Args:
            facts_dir: Root directory to search
            
        Returns:
            List of Path objects for found facts.json files
        """
        try:
            facts_json_files = []
            
            for json_file in facts_dir.rglob(FACTS_JSON_FILENAME):
                if json_file.is_file():
                    facts_json_files.append(json_file)
            
            logger.debug(
                f"Found {len(facts_json_files)} facts.json files "
                f"in {facts_dir}"
            )
            
            return facts_json_files
            
        except Exception as e:
            logger.error(f"Error searching for facts.json files: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def validate_facts_json_path(self, facts_json_path: str) -> Dict[str, Any]:
        """
        Validate that facts.json file exists and is readable.
        
        Args:
            facts_json_path: Path to facts.json file
            
        Returns:
            Dictionary with validation result
        """
        try:
            path = Path(facts_json_path)
            
            if not path.exists():
                return {
                    'valid': False,
                    'error': f'Facts JSON file not found: {facts_json_path}'
                }
            
            if not path.is_file():
                return {
                    'valid': False,
                    'error': f'Path is not a file: {facts_json_path}'
                }
            
            # Check if file is readable
            try:
                with open(path, 'r') as f:
                    f.read(1)  # Read one byte to verify readability
            except IOError as e:
                return {
                    'valid': False,
                    'error': f'Cannot read file: {str(e)}'
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating facts.json path: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }


__all__ = ['DependencyAnalysisValidator']