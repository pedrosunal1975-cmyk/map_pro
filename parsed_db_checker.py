"""
Parsed Database Checker
=======================

File: tools/parsed_db_checker.py

Checks synchronization between parsed facts filesystem and database.
"""

import json
from pathlib import Path
from typing import Dict, List

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.parsed_models import ParsedDocument

from .health_check_config import HealthCheckConfig

logger = get_logger(__name__, 'health_check')


class ParsedDatabaseChecker:
    """
    Check parsed database synchronization with filesystem.
    
    Responsibilities:
    - Scan filesystem for facts.json files
    - Compare with ParsedDocument records
    - Identify missing records, phantom records, and path mismatches
    """
    
    def __init__(self, config: HealthCheckConfig):
        """
        Initialize parsed database checker.
        
        Args:
            config: Health check configuration
        """
        self.config = config
        self.logger = get_logger(__name__, 'health_check')
    
    def check(self) -> Dict[str, List[Dict]]:
        """
        Check parsed database synchronization.
        
        Returns:
            Dictionary of issues found
        """
        issues = {
            'missing_parsed_records': [],
            'phantom_parsed_records': [],
            'path_mismatches': []
        }
        
        # Scan filesystem
        filesystem_facts = self._scan_filesystem()
        self.logger.info(
            f"Found {len(filesystem_facts)} facts.json files in filesystem"
        )
        
        # Query database
        database_records = self._query_database()
        self.logger.info(
            f"Found {len(database_records)} ParsedDocument records in database"
        )
        
        # Find mismatches
        self._find_missing_records(filesystem_facts, database_records, issues)
        self._find_phantom_records(filesystem_facts, database_records, issues)
        self._find_path_mismatches(filesystem_facts, database_records, issues)
        
        return issues
    
    def _scan_filesystem(self) -> Dict[str, Dict]:
        """
        Scan filesystem for facts.json files.
        
        Returns:
            Dictionary mapping filing_id to file information
        """
        if not self.config.parsed_facts_root.exists():
            self.logger.warning(
                f"Parsed facts directory doesn't exist: "
                f"{self.config.parsed_facts_root}"
            )
            return {}
        
        filesystem_facts = {}
        
        for json_file in self.config.parsed_facts_root.rglob("facts.json"):
            file_info = self._read_facts_file(json_file)
            if file_info:
                filing_id = file_info['filing_id']
                filesystem_facts[filing_id] = file_info
        
        return filesystem_facts
    
    def _read_facts_file(self, json_file: Path) -> Dict:
        """
        Read facts.json file and extract metadata.
        
        Args:
            json_file: Path to facts.json file
            
        Returns:
            Dictionary with file information or None if read fails
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            filing_id = metadata.get('filing_id')
            
            if not filing_id:
                return None
            
            return {
                'filing_id': filing_id,
                'path': str(json_file),
                'facts_count': len(data.get('facts', [])),
                'company': metadata.get('company', 'Unknown'),
                'filing_type': metadata.get('filing_type', 'Unknown')
            }
        
        except Exception as e:
            self.logger.warning(f"Failed to read {json_file}: {e}")
            return None
    
    def _query_database(self) -> Dict[str, Dict]:
        """
        Query database for ParsedDocument records.
        
        Returns:
            Dictionary mapping filing_id to database record information
        """
        database_records = {}
        
        with db_coordinator.get_session('parsed') as session:
            all_parsed_docs = session.query(ParsedDocument).all()
            
            for doc in all_parsed_docs:
                filing_id = str(doc.filing_universal_id)
                database_records[filing_id] = {
                    'record_id': str(doc.parsed_document_id),
                    'path': doc.facts_json_path,
                    'facts_count': doc.facts_extracted,
                    'document_name': doc.document_name
                }
        
        return database_records
    
    def _find_missing_records(
        self,
        filesystem_facts: Dict[str, Dict],
        database_records: Dict[str, Dict],
        issues: Dict[str, List[Dict]]
    ) -> None:
        """
        Find files that exist but have no database record.
        
        Args:
            filesystem_facts: Files in filesystem
            database_records: Records in database
            issues: Issues dictionary to update
        """
        for filing_id, file_info in filesystem_facts.items():
            if filing_id not in database_records:
                issues['missing_parsed_records'].append({
                    'filing_id': filing_id,
                    'file_path': file_info['path'],
                    'facts_count': file_info['facts_count'],
                    'company': file_info['company'],
                    'filing_type': file_info['filing_type'],
                    'action': 'CREATE_DB_RECORD'
                })
    
    def _find_phantom_records(
        self,
        filesystem_facts: Dict[str, Dict],
        database_records: Dict[str, Dict],
        issues: Dict[str, List[Dict]]
    ) -> None:
        """
        Find database records that have no corresponding file.
        
        Args:
            filesystem_facts: Files in filesystem
            database_records: Records in database
            issues: Issues dictionary to update
        """
        for filing_id, db_info in database_records.items():
            if filing_id not in filesystem_facts:
                # Check if file exists at recorded path
                file_path = Path(db_info['path']) if db_info['path'] else None
                file_exists = file_path.exists() if file_path else False
                
                if not file_exists:
                    issues['phantom_parsed_records'].append({
                        'filing_id': filing_id,
                        'record_id': db_info['record_id'],
                        'missing_file': db_info['path'],
                        'document_name': db_info['document_name'],
                        'action': 'DELETE_DB_RECORD'
                    })
    
    def _find_path_mismatches(
        self,
        filesystem_facts: Dict[str, Dict],
        database_records: Dict[str, Dict],
        issues: Dict[str, List[Dict]]
    ) -> None:
        """
        Find records where database path doesn't match filesystem path.
        
        Args:
            filesystem_facts: Files in filesystem
            database_records: Records in database
            issues: Issues dictionary to update
        """
        common_ids = set(filesystem_facts.keys()) & set(database_records.keys())
        
        for filing_id in common_ids:
            file_path = filesystem_facts[filing_id]['path']
            db_path = database_records[filing_id]['path']
            
            if self._is_path_mismatch(file_path, db_path):
                issues['path_mismatches'].append({
                    'filing_id': filing_id,
                    'file_path': file_path,
                    'db_path': db_path,
                    'action': 'UPDATE_DB_PATH'
                })
    
    def _is_path_mismatch(self, file_path: str, db_path: str) -> bool:
        """
        Check if database path doesn't match file path.
        
        Args:
            file_path: Path from filesystem
            db_path: Path from database
            
        Returns:
            True if paths don't match
        """
        if not db_path or file_path == db_path:
            return False
        
        # Handle relative vs absolute path comparison
        if not Path(db_path).is_absolute():
            abs_db_path = str(
                (self.config.data_root / db_path).absolute()
            )
            return abs_db_path != file_path
        
        return True