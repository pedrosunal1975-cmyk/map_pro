# PATH: /map_pro/core/filing_stages/extraction_prerequisites.py

"""
Extraction Prerequisites Checker
================================

Verifies that all prerequisites are met before extraction stage can proceed.
Extractor has 1 physical dependency: Downloaded archive file must exist.

Architecture:
- 100% market-agnostic
- Uses PrerequisiteVerifier for file operations
- Uses database as journalist (read-only metadata)
- Returns clear status for troubleshooting

Responsibilities:
- Check downloaded archive file exists
- Verify file is not empty
- Check file is readable
- Return detailed status

Does NOT:
- Create jobs
- Modify database
- Make workflow decisions
- Download missing files
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.core_models import Filing, Document
from .prerequisite_verifier import PrerequisiteVerifier

logger = get_logger(__name__, 'core')


class ExtractionPrerequisitesChecker:
    """
    Checks extraction stage prerequisites.
    
    Extractor needs only one thing: Downloaded archive file to extract.
    """
    
    def __init__(self):
        """Initialize prerequisites checker."""
        self.logger = logger
        self.verifier = PrerequisiteVerifier()
    
    def check_all_prerequisites(self, filing_id: str) -> Dict[str, Any]:
        """
        Check all extraction prerequisites for a filing.
        
        For extractor: Just verify downloaded archive file exists.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - ready (bool): True if prerequisites met
                - archive (dict): Archive file check result
                - summary (str): Human-readable summary
        """
        self.logger.info(f"Checking extraction prerequisites for filing {filing_id}")
        
        # Extractor only needs downloaded archive
        archive_result = self.check_archive_file(filing_id)
        
        # Overall readiness = archive ready
        ready = archive_result['ready']
        
        # Create summary
        summary = archive_result['reason']
        
        return {
            'ready': ready,
            'archive': archive_result,
            'summary': summary
        }
    
    def check_archive_file(self, filing_id: str) -> Dict[str, Any]:
        """
        Check if downloaded archive file exists for filing.
        
        Process:
        1. Query database for downloaded file path (journalist report)
        2. Use verifier to check file exists
        3. Verify file is not empty
        4. Return file details
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - ready (bool): True if archive file found and readable
                - size (int): File size in bytes
                - path (str): File path checked
                - reason (str): Status message
        """
        try:
            # Get downloaded file path from database (journalist)
            archive_path = self._get_downloaded_file_path(filing_id)
            
            if not archive_path:
                return {
                    'ready': False,
                    'size': 0,
                    'path': None,
                    'reason': 'Downloaded file path not in database'
                }
            
            # Check file exists and is not empty
            file_check = self.verifier.verify_file_exists(
                archive_path,
                check_size=True,
                min_size=1  # At least 1 byte
            )
            
            if not file_check['exists']:
                return {
                    'ready': False,
                    'size': 0,
                    'path': file_check['path'],
                    'reason': file_check['error']
                }
            
            return {
                'ready': True,
                'size': file_check['size'],
                'path': file_check['path'],
                'reason': f"Archive file ready ({file_check['size']} bytes)"
            }
            
        except Exception as e:
            self.logger.error(f"Error checking archive file for {filing_id}: {e}")
            return {
                'ready': False,
                'size': 0,
                'path': None,
                'reason': f'Error: {str(e)}'
            }
    
    def _get_downloaded_file_path(self, filing_id: str) -> str:
        """Get downloaded file path from database."""
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter_by(
                    filing_universal_id=filing_id
                ).first()
                
                if filing and filing.filing_directory_path and filing.original_url:
                    # Construct full path from directory + filename from URL
                    from pathlib import Path
                    from core.data_paths import map_pro_paths
                    
                    filename = Path(filing.original_url).name
                    full_path = map_pro_paths.data_root / filing.filing_directory_path / filename
                    
                    return str(full_path)
                
                # Fallback to document table
                document = session.query(Document).filter_by(
                    filing_universal_id=filing_id
                ).first()
                
                if document and document.download_path:
                    return document.download_path
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting downloaded file path: {e}")
            return None


__all__ = ['ExtractionPrerequisitesChecker']