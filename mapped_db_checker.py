"""
Mapped Database Checker
=======================

File: tools/mapped_db_checker.py

Checks synchronization between mapped statements filesystem and database.
"""

import json
from pathlib import Path
from typing import Dict, List

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.mapped_models import MappedStatement

from .health_check_config import HealthCheckConfig

logger = get_logger(__name__, 'health_check')


class MappedDatabaseChecker:
    """
    Check mapped database synchronization with filesystem.
    
    Responsibilities:
    - Scan filesystem for statement JSON files
    - Compare with MappedStatement records
    - Identify missing and phantom records
    """
    
    def __init__(self, config: HealthCheckConfig):
        """
        Initialize mapped database checker.
        
        Args:
            config: Health check configuration
        """
        self.config = config
        self.logger = get_logger(__name__, 'health_check')
    
    def check(self) -> Dict[str, List[Dict]]:
        """
        Check mapped database synchronization.
        
        Returns:
            Dictionary of issues found
        """
        issues = {
            'missing_mapped_records': [],
            'phantom_mapped_records': []
        }
        
        # Scan filesystem
        filesystem_statements = self._scan_filesystem()
        self.logger.info(
            f"Found statement files for {len(filesystem_statements)} "
            f"filings in filesystem"
        )
        
        # Query database
        database_statements = self._query_database()
        self.logger.info(
            f"Found statement records for {len(database_statements)} "
            f"filings in database"
        )
        
        # Find mismatches
        self._find_missing_records(filesystem_statements, database_statements, issues)
        self._find_phantom_records(filesystem_statements, database_statements, issues)
        
        return issues
    
    def _scan_filesystem(self) -> Dict[str, List[Dict]]:
        """
        Scan filesystem for statement JSON files.
        
        Returns:
            Dictionary mapping filing_id to list of statement files
        """
        if not self.config.mapped_statements_root.exists():
            self.logger.warning(
                f"Mapped statements directory doesn't exist: "
                f"{self.config.mapped_statements_root}"
            )
            return {}
        
        filesystem_statements = {}
        
        for json_file in self.config.mapped_statements_root.rglob("*.json"):
            # Skip null_quality files
            if 'null_quality' in json_file.name:
                continue
            
            statement_info = self._read_statement_file(json_file)
            if statement_info:
                filing_id = statement_info['filing_id']
                
                if filing_id not in filesystem_statements:
                    filesystem_statements[filing_id] = []
                
                filesystem_statements[filing_id].append(statement_info)
        
        return filesystem_statements
    
    def _read_statement_file(self, json_file: Path) -> Dict:
        """
        Read statement JSON file and extract metadata.
        
        Args:
            json_file: Path to statement JSON file
            
        Returns:
            Dictionary with statement information or None if read fails
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
                'statement_type': data.get('statement_type', 'unknown'),
                'facts_count': len(data.get('facts', []))
            }
        
        except Exception as e:
            self.logger.warning(f"Failed to read {json_file}: {e}")
            return None
    
    def _query_database(self) -> Dict[str, List[Dict]]:
        """
        Query database for MappedStatement records.
        
        Returns:
            Dictionary mapping filing_id to list of database records
        """
        database_statements = {}
        
        with db_coordinator.get_session('mapped') as session:
            all_mapped_statements = session.query(MappedStatement).all()
            
            for stmt in all_mapped_statements:
                filing_id = str(stmt.filing_universal_id)
                
                if filing_id not in database_statements:
                    database_statements[filing_id] = []
                
                database_statements[filing_id].append({
                    'record_id': str(stmt.statement_id),
                    'path': stmt.statement_json_path,
                    'statement_type': stmt.statement_type
                })
        
        return database_statements
    
    def _find_missing_records(
        self,
        filesystem_statements: Dict[str, List[Dict]],
        database_statements: Dict[str, List[Dict]],
        issues: Dict[str, List[Dict]]
    ) -> None:
        """
        Find files that exist but have no database records.
        
        Args:
            filesystem_statements: Files in filesystem
            database_statements: Records in database
            issues: Issues dictionary to update
        """
        for filing_id in filesystem_statements.keys():
            if filing_id not in database_statements:
                issues['missing_mapped_records'].append({
                    'filing_id': filing_id,
                    'file_count': len(filesystem_statements[filing_id]),
                    'action': 'CREATE_DB_RECORDS'
                })
    
    def _find_phantom_records(
        self,
        filesystem_statements: Dict[str, List[Dict]],
        database_statements: Dict[str, List[Dict]],
        issues: Dict[str, List[Dict]]
    ) -> None:
        """
        Find database records that have no corresponding files.
        
        Args:
            filesystem_statements: Files in filesystem
            database_statements: Records in database
            issues: Issues dictionary to update
        """
        for filing_id in database_statements.keys():
            if filing_id not in filesystem_statements:
                issues['phantom_mapped_records'].append({
                    'filing_id': filing_id,
                    'record_count': len(database_statements[filing_id]),
                    'action': 'DELETE_DB_RECORDS'
                })