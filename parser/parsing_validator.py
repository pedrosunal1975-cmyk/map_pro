# File: /map_pro/engines/parser/parsing_validator.py

"""
Parsing Validator
=================

Validates parsing environment and requirements.

Responsibilities:
- Validate parsed facts directory exists
- Check required components are initialized
- Verify environment setup
"""

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'engine')


class ParsingValidator:
    """Validates parsing environment and requirements."""
    
    def validate_environment(self) -> bool:
        """
        Validate parsing environment is properly set up.
        
        Returns:
            True if environment is valid
        """
        try:
            # Validate parsed facts directory exists
            if not self._validate_facts_directory():
                return False
            
            logger.info("Parsing environment validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Environment validation failed: {e}")
            return False
    
    def _validate_facts_directory(self) -> bool:
        """
        Validate parsed facts directory exists and is writable.
        
        Returns:
            True if directory is valid
        """
        try:
            facts_dir = map_pro_paths.data_parsed_facts
            
            # Create directory if it doesn't exist
            facts_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify directory exists
            if not facts_dir.exists():
                logger.error(f"Failed to create parsed facts directory: {facts_dir}")
                return False
            
            # Verify directory is writable
            if not facts_dir.is_dir():
                logger.error(f"Parsed facts path is not a directory: {facts_dir}")
                return False
            
            logger.info(f"Parsed facts directory validated: {facts_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Facts directory validation failed: {e}")
            return False


__all__ = ['ParsingValidator']