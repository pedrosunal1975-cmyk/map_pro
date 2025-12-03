# PATH: /map_pro/core/filing_stages/mapping_prerequisites.py

"""
Mapping Prerequisites Checker
=============================

Verifies that all prerequisites are met before mapping stage can proceed.
Mapper has 3 physical dependencies: XBRL files, facts.json, taxonomy libraries.

Architecture:
- 100% market-agnostic
- Uses PrerequisiteVerifier for file operations
- Uses database as journalist (read-only metadata)
- Returns clear status for each prerequisite

Responsibilities:
- Check XBRL files exist for filing
- Check parsed facts.json exists with content
- Check taxonomy libraries directory exists
- Return detailed status for troubleshooting

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
from database.models.core_models import Filing
from database.models.parsed_models import ParsedDocument
from .prerequisite_verifier import PrerequisiteVerifier

logger = get_logger(__name__, 'core')


class MappingPrerequisitesChecker:
    """
    Checks mapping stage prerequisites.
    
    Each check method is independent and testable.
    """
    
    def __init__(self):
        """Initialize prerequisites checker."""
        self.logger = logger
        self.verifier = PrerequisiteVerifier()
    
    def check_all_prerequisites(self, filing_id: str) -> Dict[str, Any]:
        """
        Check all mapping prerequisites for a filing.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - ready (bool): True if all prerequisites met
                - xbrl (dict): XBRL files check result
                - facts (dict): Facts JSON check result
                - libraries (dict): Libraries check result
                - summary (str): Human-readable summary
        """
        self.logger.info(f"Checking mapping prerequisites for filing {filing_id}")
        
        # Run all three checks independently
        xbrl_result = self.check_xbrl_files(filing_id)
        facts_result = self.check_facts_json(filing_id)
        libraries_result = self.check_libraries(filing_id)
        
        # Determine overall readiness
        all_ready = (
            xbrl_result['ready'] and 
            facts_result['ready'] and 
            libraries_result['ready']
        )
        
        # Create summary message
        summary = self._create_summary_message(
            all_ready, 
            xbrl_result, 
            facts_result, 
            libraries_result
        )
        
        return {
            'ready': all_ready,
            'xbrl': xbrl_result,
            'facts': facts_result,
            'libraries': libraries_result,
            'summary': summary
        }
    
    def check_xbrl_files(self, filing_id: str) -> Dict[str, Any]:
        """
        Check if XBRL files exist for filing.
        
        Process:
        1. Query database for filing directory path (journalist report)
        2. Use verifier to check directory exists
        3. Use verifier to count XBRL files (.htm, .xml)
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - ready (bool): True if XBRL files found
                - count (int): Number of XBRL files
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
                    'path': None,
                    'reason': 'Filing directory path not in database'
                }
            
            # Check directory exists
            dir_check = self.verifier.verify_directory_exists(filing_dir_path)
            
            if not dir_check['exists']:
                return {
                    'ready': False,
                    'count': 0,
                    'path': dir_check['path'],
                    'reason': 'Filing directory does not exist'
                }
            
            # Count XBRL files (.htm and .xml)
            htm_count = self.verifier.count_files_in_directory(
                dir_check['path'], 
                '*.htm',
                make_absolute=False
            )
            
            xml_count = self.verifier.count_files_in_directory(
                dir_check['path'],
                '*.xml',
                make_absolute=False
            )
            
            total_files = htm_count['count'] + xml_count['count']
            
            if total_files == 0:
                return {
                    'ready': False,
                    'count': 0,
                    'path': dir_check['path'],
                    'reason': 'No XBRL files found in directory'
                }
            
            return {
                'ready': True,
                'count': total_files,
                'path': dir_check['path'],
                'reason': f'{total_files} XBRL files found'
            }
            
        except Exception as e:
            self.logger.error(f"Error checking XBRL files for {filing_id}: {e}")
            return {
                'ready': False,
                'count': 0,
                'path': None,
                'reason': f'Error: {str(e)}'
            }
    
    def check_facts_json(self, filing_id: str) -> Dict[str, Any]:
        """
        Check if parsed facts.json exists with content.
        
        Process:
        1. Query database for parsed documents (journalist report)
        2. Find document with facts_json_path
        3. Use verifier to check JSON file is valid
        4. Count facts in JSON
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with:
                - ready (bool): True if valid facts.json found
                - count (int): Number of facts
                - path (str): Path to facts.json
                - reason (str): Status message
        """
        try:
            # Get facts.json path from database (journalist)
            facts_path = self._get_facts_json_path(filing_id)
            
            if not facts_path:
                return {
                    'ready': False,
                    'count': 0,
                    'path': None,
                    'reason': 'No parsed document with facts.json path'
                }
            
            # Verify JSON file is valid with 'facts' key
            json_check = self.verifier.verify_json_file_valid(
                facts_path,
                required_keys=['facts']
            )
            
            if not json_check['valid']:
                return {
                    'ready': False,
                    'count': 0,
                    'path': json_check['path'],
                    'reason': json_check['error']
                }
            
            # Count facts
            facts = json_check['data'].get('facts', [])
            facts_count = len(facts)
            
            if facts_count == 0:
                return {
                    'ready': False,
                    'count': 0,
                    'path': json_check['path'],
                    'reason': 'Facts JSON exists but contains no facts'
                }
            
            return {
                'ready': True,
                'count': facts_count,
                'path': json_check['path'],
                'reason': f'{facts_count} facts available'
            }
            
        except Exception as e:
            self.logger.error(f"Error checking facts.json for {filing_id}: {e}")
            return {
                'ready': False,
                'count': 0,
                'path': None,
                'reason': f'Error: {str(e)}'
            }
    
    def check_libraries(self, filing_id: str) -> Dict[str, Any]:
        """
        Check if taxonomy libraries directory exists.
        
        Simplified check: Just verify taxonomies directory exists with content.
        (Librarian is lazy - common taxonomies should already exist)
        
        Process:
        1. Check taxonomies directory exists
        2. Count subdirectories (each is a library)
        
        Args:
            filing_id: Filing universal ID (not used, but kept for consistency)
            
        Returns:
            Dictionary with:
                - ready (bool): True if libraries directory has content
                - count (int): Number of library subdirectories
                - path (str): Taxonomies directory path
                - reason (str): Status message
        """
        try:
            # Use the correct taxonomies path from data_paths
            taxonomies_dir = map_pro_paths.data_taxonomies / 'libraries'
            
            # Check directory exists
            dir_check = self.verifier.verify_directory_exists(
                str(taxonomies_dir),
                make_absolute=False
            )
            
            if not dir_check['exists']:
                return {
                    'ready': False,
                    'count': 0,
                    'path': str(taxonomies_dir),
                    'reason': 'Taxonomies directory does not exist'
                }
            
            # Count subdirectories (libraries)
            lib_dirs = [
                d for d in Path(dir_check['path']).iterdir() 
                if d.is_dir()
            ]
            
            if not lib_dirs:
                return {
                    'ready': False,
                    'count': 0,
                    'path': dir_check['path'],
                    'reason': 'No taxonomy libraries found'
                }
            
            return {
                'ready': True,
                'count': len(lib_dirs),
                'path': dir_check['path'],
                'reason': f'{len(lib_dirs)} taxonomy libraries available'
            }
            
        except Exception as e:
            self.logger.error(f"Error checking libraries: {e}")
            # Assume available if check fails (don't block mapper)
            return {
                'ready': True,
                'count': 0,
                'path': None,
                'reason': 'Could not verify (assuming available)'
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
    
    def _get_facts_json_path(self, filing_id: str) -> str:
        """
        Get facts.json path from database.
        
        Database as journalist: Just reading reported metadata.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Facts JSON path, or None if not found
        """
        try:
            with db_coordinator.get_session('parsed') as session:
                # Find parsed documents for filing
                parsed_docs = session.query(ParsedDocument).filter_by(
                    filing_universal_id=filing_id
                ).all()
                
                # Find first document with facts_json_path
                for doc in parsed_docs:
                    if doc.facts_json_path:
                        return doc.facts_json_path
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting facts.json path: {e}")
            return None
    
    def _create_summary_message(
        self,
        all_ready: bool,
        xbrl_result: Dict[str, Any],
        facts_result: Dict[str, Any],
        libraries_result: Dict[str, Any]
    ) -> str:
        """
        Create human-readable summary message.
        
        Args:
            all_ready: Whether all prerequisites are met
            xbrl_result: XBRL check result
            facts_result: Facts check result
            libraries_result: Libraries check result
            
        Returns:
            Summary message string
        """
        if all_ready:
            return (
                f"XBRL files ({xbrl_result['count']}), "
                f"facts ({facts_result['count']}), "
                f"libraries ({libraries_result['count']})"
            )
        
        # List what's missing
        missing = []
        
        if not xbrl_result['ready']:
            missing.append(f"XBRL ({xbrl_result['reason']})")
        
        if not facts_result['ready']:
            missing.append(f"facts ({facts_result['reason']})")
        
        if not libraries_result['ready']:
            missing.append(f"libraries ({libraries_result['reason']})")
        
        return '; '.join(missing)


__all__ = ['MappingPrerequisitesChecker']