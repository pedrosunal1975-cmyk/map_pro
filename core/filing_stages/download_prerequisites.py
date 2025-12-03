# PATH: /map_pro/core/filing_stages/download_prerequisites.py

"""
Download Prerequisites Checker
==============================

Verifies that all prerequisites are met before download stage can proceed.
Downloader has 3 prerequisites: Filing URL, Entity ID, Download directory.

Architecture:
- 100% market-agnostic
- Uses PrerequisiteVerifier for file operations
- Checks metadata availability
- Returns clear status for troubleshooting

Responsibilities:
- Check filing information contains required data
- Verify download directory exists and is writable
- Validate entity ID is present
- Return detailed status

Does NOT:
- Create jobs
- Modify database
- Make workflow decisions
- Download files
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from .prerequisite_verifier import PrerequisiteVerifier

logger = get_logger(__name__, 'core')


class DownloadPrerequisitesChecker:
    """
    Checks download stage prerequisites.
    
    Downloader needs: Filing info (URL), entity ID, writable download directory.
    """
    
    def __init__(self):
        """Initialize prerequisites checker."""
        self.logger = logger
        self.verifier = PrerequisiteVerifier()
    
    def check_all_prerequisites(
        self,
        filing_info: Dict[str, Any],
        market_type: str
    ) -> Dict[str, Any]:
        """
        Check all download prerequisites.
        
        Args:
            filing_info: Filing information dictionary
            market_type: Market type identifier
            
        Returns:
            Dictionary with:
                - ready (bool): True if prerequisites met
                - filing_info (dict): Filing info check result
                - download_dir (dict): Download directory check result
                - summary (str): Human-readable summary
        """
        self.logger.info("Checking download prerequisites")
        
        # Check filing information
        filing_check = self.check_filing_info(filing_info)
        
        # Check download directory
        dir_check = self.check_download_directory(market_type)
        
        # Overall readiness
        ready = filing_check['ready'] and dir_check['ready']
        
        # Create summary
        if ready:
            summary = f"Filing info valid, download directory ready"
        else:
            missing = []
            if not filing_check['ready']:
                missing.append(f"filing info ({filing_check['reason']})")
            if not dir_check['ready']:
                missing.append(f"download dir ({dir_check['reason']})")
            summary = '; '.join(missing)
        
        return {
            'ready': ready,
            'filing_info': filing_check,
            'download_dir': dir_check,
            'summary': summary
        }
    
    def check_filing_info(self, filing_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if filing information contains required data.
        
        Required fields:
        - entity_id: Company identifier
        - url or filing_url: URL to download from
        
        Args:
            filing_info: Filing information dictionary
            
        Returns:
            Dictionary with:
                - ready (bool): True if filing info valid
                - entity_id (str): Entity ID if present
                - url (str): Download URL if present
                - reason (str): Status message
        """
        if not filing_info:
            return {
                'ready': False,
                'entity_id': None,
                'url': None,
                'reason': 'Filing info dictionary is empty'
            }
        
        # Check entity_id
        entity_id = filing_info.get('entity_id')
        if not entity_id:
            return {
                'ready': False,
                'entity_id': None,
                'url': None,
                'reason': 'Entity ID missing from filing info'
            }
        
        # Check URL (try multiple possible keys)
        url = (
            filing_info.get('url') or 
            filing_info.get('filing_url') or
            filing_info.get('download_url')
        )
        
        if not url:
            return {
                'ready': False,
                'entity_id': entity_id,
                'url': None,
                'reason': 'Download URL missing from filing info'
            }
        
        return {
            'ready': True,
            'entity_id': entity_id,
            'url': url,
            'reason': 'Filing info valid'
        }
    
    def check_download_directory(self, market_type: str) -> Dict[str, Any]:
        """
        Check if download directory exists and is writable.
        
        Args:
            market_type: Market type identifier
            
        Returns:
            Dictionary with:
                - ready (bool): True if directory ready
                - path (str): Directory path
                - writable (bool): Whether directory is writable
                - reason (str): Status message
        """
        try:
            # Get downloads directory
            downloads_dir = map_pro_paths.data_root / 'downloads'
            
            # Check directory exists
            dir_check = self.verifier.verify_directory_exists(
                str(downloads_dir),
                make_absolute=False
            )
            
            if not dir_check['exists']:
                return {
                    'ready': False,
                    'path': str(downloads_dir),
                    'writable': False,
                    'reason': 'Downloads directory does not exist'
                }
            
            # Check if writable (try to create a test file)
            test_file = downloads_dir / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
                writable = True
            except Exception:
                writable = False
            
            if not writable:
                return {
                    'ready': False,
                    'path': str(downloads_dir),
                    'writable': False,
                    'reason': 'Downloads directory is not writable'
                }
            
            return {
                'ready': True,
                'path': str(downloads_dir),
                'writable': True,
                'reason': 'Download directory ready'
            }
            
        except Exception as e:
            self.logger.error(f"Error checking download directory: {e}")
            return {
                'ready': False,
                'path': None,
                'writable': False,
                'reason': f'Error: {str(e)}'
            }


__all__ = ['DownloadPrerequisitesChecker']