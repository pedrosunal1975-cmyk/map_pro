# PATH: /map_pro/core/filing_stages/parsing_prerequisites.py

"""
Parsing Prerequisites Checker
=============================

Verifies that all prerequisites are met before parsing stage can proceed.
Parser has 1 physical dependency: XBRL files must exist.

Architecture:
- 100% market-agnostic
- Uses PrerequisiteVerifier for file operations
- Uses database as journalist (read-only metadata)
- Returns clear status for troubleshooting

Responsibilities:
- Check XBRL files exist and are readable
- Verify files are not empty
- Count total files to parse
- Return detailed status

Does NOT:
- Create jobs
- Modify database
- Make workflow decisions
- Download missing files
"""

from typing import Dict, Any
from pathlib import Path

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.core_models import Filing, Document
from .prerequisite_verifier import PrerequisiteVerifier

logger = get_logger(__name__, 'core')


class ParsingPrerequisitesChecker:
    """
    Checks parsing stage prerequisites.
    
    Parser needs only one thing: XBRL files to parse.
    """
    
    def __init__(self):
        """Initialize prerequisites checker."""
        self.logger = logger
        self.verifier = PrerequisiteVerifier()
    
    def check_all_prerequisites(self, filing_id: str) -> Dict[str, Any]:
        """
        Check all parsing prerequisites for a filing.
        
        For parser: Just verify XBRL files exist.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - ready (bool): True if prerequisites met
                - xbrl (dict): XBRL files check result
                - summary (str): Human-readable summary
        """
        self.logger.info(f"Checking parsing prerequisites for filing {filing_id}")
        
        # Parser only needs XBRL files
        xbrl_result = self.check_xbrl_files(filing_id)
        
        # Overall readiness = XBRL files ready
        ready = xbrl_result['ready']
        
        # Create summary
        summary = xbrl_result['reason']
        
        return {
            'ready': ready,
            'xbrl': xbrl_result,
            'summary': summary
        }
    
    def check_xbrl_files(self, filing_id: str) -> Dict[str, Any]:
        """
        Check if XBRL files exist for filing.
        
        Process:
        1. Query database for filing directory path (journalist report)
        2. Use verifier to check directory exists
        3. Use verifier to count XBRL files (.htm, .xml)
        4. Verify files are not empty
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - ready (bool): True if XBRL files found and readable
                - count (int): Number of XBRL files
                - total_size (int): Total size of files in bytes
                - path (str): Directory path checked
                - reason (str): Status message
        """
        try:
            # Get directory path from database (journalist)
            filing_dir_path = self._get_filing_directory_path(filing_id)
            
            if not filing_dir_path:
                return {
                    'ready': False,
                    'count': 0,
                    'total_size': 0,
                    'path': None,
                    'reason': 'Filing directory path not in database'
                }
            
            # Check directory exists
            dir_check = self.verifier.verify_directory_exists(filing_dir_path)
            
            if not dir_check['exists']:
                return {
                    'ready': False,
                    'count': 0,
                    'total_size': 0,
                    'path': dir_check['path'],
                    'reason': 'Filing directory does not exist'
                }
            
            # Count and verify XBRL files
            xbrl_files = self._find_and_verify_xbrl_files(dir_check['path'])
            
            if not xbrl_files['files']:
                return {
                    'ready': False,
                    'count': 0,
                    'total_size': 0,
                    'path': dir_check['path'],
                    'reason': 'No XBRL files found in directory'
                }
            
            return {
                'ready': True,
                'count': xbrl_files['count'],
                'total_size': xbrl_files['total_size'],
                'path': dir_check['path'],
                'reason': f"{xbrl_files['count']} XBRL files ready ({xbrl_files['total_size']} bytes)"
            }
            
        except Exception as e:
            self.logger.error(f"Error checking XBRL files for {filing_id}: {e}")
            return {
                'ready': False,
                'count': 0,
                'total_size': 0,
                'path': None,
                'reason': f'Error: {str(e)}'
            }
    
    def _find_and_verify_xbrl_files(self, directory_path: str) -> Dict[str, Any]:
        """
        Find and verify XBRL files in directory.
        
        Checks for both .htm and .xml files, verifies they're not empty.
        
        Args:
            directory_path: Directory to search
            
        Returns:
            Dictionary with:
                - count (int): Number of valid XBRL files
                - files (list): List of file paths
                - total_size (int): Total size of all files
        """
        valid_files = []
        total_size = 0
        
        # Count .htm files
        htm_result = self.verifier.count_files_in_directory(
            directory_path,
            '*.htm',
            make_absolute=False
        )
        
        # Count .xml files
        xml_result = self.verifier.count_files_in_directory(
            directory_path,
            '*.xml',
            make_absolute=False
        )
        
        # Combine both lists
        all_files = htm_result['files'] + xml_result['files']
        
        # Verify each file is not empty
        for file_path in all_files:
            file_check = self.verifier.verify_file_exists(
                file_path,
                make_absolute=False,
                check_size=True,
                min_size=1  # At least 1 byte
            )
            
            if file_check['exists']:
                valid_files.append(file_path)
                total_size += file_check['size']
        
        return {
            'count': len(valid_files),
            'files': valid_files,
            'total_size': total_size
        }
    
    def _get_filing_directory_path(self, filing_id: str) -> str:
        """
        Get filing directory path from database, pointing to extracted files.
        
        Database as journalist: Just reading reported metadata.
        Extracted XBRL files are in filing_directory_path/extracted/
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Path to extracted files directory, or None if not found
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter_by(
                    filing_universal_id=filing_id
                ).first()
                
                if not filing or not filing.filing_directory_path:
                    return None
                
                # Construct path to extracted directory
                base_path = filing.filing_directory_path
                
                # Check if path is absolute
                if Path(base_path).is_absolute():
                    extracted_path = Path(base_path) / 'extracted'
                else:
                    extracted_path = map_pro_paths.data_root / base_path / 'extracted'
                
                return str(extracted_path)
                
        except Exception as e:
            self.logger.error(f"Error getting filing directory path: {e}")
            return None


__all__ = ['ParsingPrerequisitesChecker']