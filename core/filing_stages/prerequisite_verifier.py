# PATH: /map_pro/core/filing_stages/prerequisite_verifier.py

"""
Prerequisite Verifier
====================

Generic, reusable utility for verifying physical prerequisites.
Used by all workflow stages (parsing, mapping, extraction, etc.).

Architecture:
- 100% market-agnostic
- Pure utility functions
- No business logic
- Easily testable

Responsibilities:
- Verify files exist on filesystem
- Verify directories exist
- Check file content validity
- Return clear status dictionaries

Does NOT:
- Make business decisions
- Access job queues
- Create jobs
- Contain market-specific logic
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'core')


class PrerequisiteVerifier:
    """
    Generic prerequisite verification utility.
    
    All methods are pure functions - given inputs, return verification status.
    No side effects, no state, easily testable.
    """
    
    def __init__(self):
        """Initialize prerequisite verifier."""
        self.logger = logger
    
    def verify_directory_exists(
        self,
        directory_path: str,
        make_absolute: bool = True
    ) -> Dict[str, Any]:
        """
        Verify directory exists on filesystem.
        
        Args:
            directory_path: Path to directory (absolute or relative)
            make_absolute: If True and path is relative, make it absolute using data_root
            
        Returns:
            Dictionary with:
                - exists (bool): True if directory exists
                - path (str): Absolute path that was checked
                - error (str): Error message if check failed, None otherwise
        """
        try:
            dir_path = Path(directory_path)
            
            # Convert to absolute if needed
            if make_absolute and not dir_path.is_absolute():
                dir_path = map_pro_paths.data_root / directory_path
            
            exists = dir_path.exists() and dir_path.is_dir()
            
            return {
                'exists': exists,
                'path': str(dir_path),
                'error': None if exists else 'Directory does not exist'
            }
            
        except Exception as e:
            self.logger.error(f"Error checking directory {directory_path}: {e}")
            return {
                'exists': False,
                'path': directory_path,
                'error': f'Error checking directory: {str(e)}'
            }
    
    def verify_file_exists(
        self,
        file_path: str,
        make_absolute: bool = True,
        check_size: bool = True,
        min_size: int = 0
    ) -> Dict[str, Any]:
        """
        Verify file exists on filesystem.
        
        Args:
            file_path: Path to file (absolute or relative)
            make_absolute: If True and path is relative, make it absolute using data_root
            check_size: If True, also verify file is not empty
            min_size: Minimum file size in bytes (default 0)
            
        Returns:
            Dictionary with:
                - exists (bool): True if file exists and meets criteria
                - path (str): Absolute path that was checked
                - size (int): File size in bytes, or 0 if doesn't exist
                - error (str): Error message if check failed, None otherwise
        """
        try:
            f_path = Path(file_path)
            
            # Convert to absolute if needed
            if make_absolute and not f_path.is_absolute():
                f_path = map_pro_paths.data_root / file_path
            
            if not f_path.exists():
                return {
                    'exists': False,
                    'path': str(f_path),
                    'size': 0,
                    'error': 'File does not exist'
                }
            
            if not f_path.is_file():
                return {
                    'exists': False,
                    'path': str(f_path),
                    'size': 0,
                    'error': 'Path exists but is not a file'
                }
            
            file_size = f_path.stat().st_size
            
            if check_size and file_size < min_size:
                return {
                    'exists': False,
                    'path': str(f_path),
                    'size': file_size,
                    'error': f'File too small: {file_size} bytes (min: {min_size})'
                }
            
            return {
                'exists': True,
                'path': str(f_path),
                'size': file_size,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Error checking file {file_path}: {e}")
            return {
                'exists': False,
                'path': file_path,
                'size': 0,
                'error': f'Error checking file: {str(e)}'
            }
    
    def verify_json_file_valid(
        self,
        file_path: str,
        make_absolute: bool = True,
        required_keys: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Verify JSON file exists and is valid.
        
        Args:
            file_path: Path to JSON file
            make_absolute: If True and path is relative, make it absolute using data_root
            required_keys: List of keys that must exist in JSON root, or None
            
        Returns:
            Dictionary with:
                - valid (bool): True if file is valid JSON with required keys
                - path (str): Absolute path that was checked
                - data (dict): Parsed JSON data if valid, None otherwise
                - error (str): Error message if validation failed, None otherwise
        """
        # First check file exists
        file_check = self.verify_file_exists(file_path, make_absolute, True, 1)
        
        if not file_check['exists']:
            return {
                'valid': False,
                'path': file_check['path'],
                'data': None,
                'error': file_check['error']
            }
        
        # Try to parse JSON
        try:
            with open(file_check['path'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required keys if specified
            if required_keys:
                missing_keys = [key for key in required_keys if key not in data]
                if missing_keys:
                    return {
                        'valid': False,
                        'path': file_check['path'],
                        'data': data,
                        'error': f'Missing required keys: {", ".join(missing_keys)}'
                    }
            
            return {
                'valid': True,
                'path': file_check['path'],
                'data': data,
                'error': None
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_check['path']}: {e}")
            return {
                'valid': False,
                'path': file_check['path'],
                'data': None,
                'error': f'Invalid JSON: {str(e)}'
            }
        except Exception as e:
            self.logger.error(f"Error reading JSON file {file_check['path']}: {e}")
            return {
                'valid': False,
                'path': file_check['path'],
                'data': None,
                'error': f'Error reading file: {str(e)}'
            }
    
    def count_files_in_directory(
        self,
        directory_path: str,
        pattern: str = '*',
        make_absolute: bool = True
    ) -> Dict[str, Any]:
        """
        Count files matching pattern in directory.
        
        Args:
            directory_path: Path to directory
            pattern: File pattern (e.g., '*.xml', '*.htm')
            make_absolute: If True and path is relative, make it absolute using data_root
            
        Returns:
            Dictionary with:
                - count (int): Number of matching files
                - files (list): List of matching file paths
                - path (str): Directory path that was checked
                - error (str): Error message if check failed, None otherwise
        """
        # First check directory exists
        dir_check = self.verify_directory_exists(directory_path, make_absolute)
        
        if not dir_check['exists']:
            return {
                'count': 0,
                'files': [],
                'path': dir_check['path'],
                'error': dir_check['error']
            }
        
        try:
            dir_path = Path(dir_check['path'])
            matching_files = list(dir_path.glob(pattern))
            
            return {
                'count': len(matching_files),
                'files': [str(f) for f in matching_files],
                'path': str(dir_path),
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Error counting files in {dir_check['path']}: {e}")
            return {
                'count': 0,
                'files': [],
                'path': dir_check['path'],
                'error': f'Error counting files: {str(e)}'
            }


__all__ = ['PrerequisiteVerifier']