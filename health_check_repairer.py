"""
Health Check Repairer
=====================

File: tools/health_check_repairer.py

Repairs database issues found during health checks.
"""

import json
from pathlib import Path
from typing import Dict, List

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.parsed_models import ParsedDocument

from .health_check_config import HealthCheckConfig

logger = get_logger(__name__, 'health_check')


class HealthCheckRepairer:
    """
    Repair database issues.
    
    Responsibilities:
    - Create missing database records
    - Delete phantom records
    - Update path mismatches
    - Track repair statistics
    """
    
    def __init__(self, config: HealthCheckConfig):
        """
        Initialize health check repairer.
        
        Args:
            config: Health check configuration
        """
        self.config = config
        self.logger = get_logger(__name__, 'health_check')
    
    def repair_parsed_issues(
        self,
        issues: Dict[str, List[Dict]],
        dry_run: bool = True
    ) -> Dict[str, int]:
        """
        Repair parsed database issues.
        
        Args:
            issues: Dictionary of issues to repair
            dry_run: If True, only simulate repairs
            
        Returns:
            Repair statistics
        """
        stats = {
            'records_created': 0,
            'records_deleted': 0,
            'paths_updated': 0
        }
        
        if self.config.create_missing_records:
            stats['records_created'] = self._create_missing_records(
                issues.get('missing_parsed_records', []),
                dry_run
            )
        
        if self.config.delete_phantom_records:
            stats['records_deleted'] = self._delete_phantom_records(
                issues.get('phantom_parsed_records', []),
                dry_run
            )
        
        if self.config.update_path_mismatches:
            stats['paths_updated'] = self._update_path_mismatches(
                issues.get('path_mismatches', []),
                dry_run
            )
        
        return stats
    
    def _create_missing_records(
        self,
        missing_records: List[Dict],
        dry_run: bool
    ) -> int:
        """
        Create missing database records.
        
        Args:
            missing_records: List of missing record issues
            dry_run: If True, only simulate
            
        Returns:
            Number of records created
        """
        created_count = 0
        
        for issue in missing_records:
            if dry_run:
                self.logger.info(
                    f"[DRY RUN] Would create record for {issue['filing_id']}"
                )
                created_count += 1
            else:
                if self._create_parsed_record(issue):
                    created_count += 1
        
        return created_count
    
    def _create_parsed_record(self, issue: Dict) -> bool:
        """
        Create a single ParsedDocument record.
        
        Args:
            issue: Issue dictionary with file information
            
        Returns:
            True if record was created successfully
        """
        try:
            # Read file to get metadata
            with open(issue['file_path'], 'r') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            
            with db_coordinator.get_session('parsed') as session:
                parsed_doc = ParsedDocument(
                    filing_universal_id=issue['filing_id'],
                    entity_universal_id=metadata.get('entity_id'),
                    document_name=metadata.get(
                        'document_name',
                        'reconstructed'
                    ),
                    facts_json_path=issue['file_path'],
                    parsing_engine='arelle',
                    facts_extracted=issue['facts_count'],
                    validation_status='completed'
                )
                
                session.add(parsed_doc)
                session.commit()
                
                self.logger.info(
                    f"Created ParsedDocument record for {issue['filing_id']}"
                )
                return True
        
        except Exception as e:
            self.logger.error(
                f"Failed to create record for {issue['filing_id']}: {e}"
            )
            return False
    
    def _delete_phantom_records(
        self,
        phantom_records: List[Dict],
        dry_run: bool
    ) -> int:
        """
        Delete phantom database records.
        
        Args:
            phantom_records: List of phantom record issues
            dry_run: If True, only simulate
            
        Returns:
            Number of records deleted
        """
        deleted_count = 0
        
        for issue in phantom_records:
            if dry_run:
                self.logger.info(
                    f"[DRY RUN] Would delete phantom record {issue['record_id']}"
                )
                deleted_count += 1
            else:
                if self._delete_parsed_record(issue):
                    deleted_count += 1
        
        return deleted_count
    
    def _delete_parsed_record(self, issue: Dict) -> bool:
        """
        Delete a single ParsedDocument record.
        
        Args:
            issue: Issue dictionary with record information
            
        Returns:
            True if record was deleted successfully
        """
        try:
            with db_coordinator.get_session('parsed') as session:
                session.query(ParsedDocument).filter_by(
                    parsed_document_id=issue['record_id']
                ).delete()
                session.commit()
                
                self.logger.info(f"Deleted phantom record {issue['record_id']}")
                return True
        
        except Exception as e:
            self.logger.error(
                f"Failed to delete record {issue['record_id']}: {e}"
            )
            return False
    
    def _update_path_mismatches(
        self,
        path_mismatches: List[Dict],
        dry_run: bool
    ) -> int:
        """
        Update path mismatches.
        
        Args:
            path_mismatches: List of path mismatch issues
            dry_run: If True, only simulate
            
        Returns:
            Number of paths updated
        """
        updated_count = 0
        
        for issue in path_mismatches:
            if dry_run:
                self.logger.info(
                    f"[DRY RUN] Would update path for {issue['filing_id']}"
                )
                updated_count += 1
            else:
                if self._update_parsed_path(issue):
                    updated_count += 1
        
        return updated_count
    
    def _update_parsed_path(self, issue: Dict) -> bool:
        """
        Update path for a single ParsedDocument record.
        
        Args:
            issue: Issue dictionary with path information
            
        Returns:
            True if path was updated successfully
        """
        try:
            with db_coordinator.get_session('parsed') as session:
                doc = session.query(ParsedDocument).filter_by(
                    filing_universal_id=issue['filing_id']
                ).first()
                
                if doc:
                    doc.facts_json_path = issue['file_path']
                    session.commit()
                    
                    self.logger.info(f"Updated path for {issue['filing_id']}")
                    return True
                else:
                    self.logger.warning(
                        f"Record not found for {issue['filing_id']}"
                    )
                    return False
        
        except Exception as e:
            self.logger.error(
                f"Failed to update path for {issue['filing_id']}: {e}"
            )
            return False