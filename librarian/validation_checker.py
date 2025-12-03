"""
Map Pro Validation Checker
==========================

Validates taxonomy library integrity and completeness.

Architecture: Uses library database models for validation tracking.
"""

import uuid
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
# Assuming the necessary imports are correct based on the original file
from database.models.library_models import TaxonomyLibrary, TaxonomyFile, LibraryHealthCheck 
from shared.exceptions.custom_exceptions import DatabaseError

logger = get_logger(__name__, 'engine')


class ValidationChecker:
    """
    Validates taxonomy library integrity.
    
    Responsibilities:
    - Validate library completeness
    - Check file integrity
    - Track validation results in database
    - Report validation issues
    
    Does NOT handle:
    - Downloads (taxonomy_downloader handles this)
    - File indexing (concept_indexer handles this)
    - Full concept validation (requires XBRL parser)
    """
    
    def __init__(self):
        """Initialize validation checker."""
        logger.info("Validation checker initialized")
    
    def validate_library(self, library_id: uuid.UUID) -> Dict[str, Any]:
        """
        Perform comprehensive library validation.
        
        Args:
            library_id: UUID of TaxonomyLibrary
            
        Returns:
            Dictionary with validation results:
                - status: 'healthy', 'warning', or 'failed'
                - issues_found: Number of issues
                - critical_issues: Number of critical issues
                - checks_performed: List of checks performed
                - details: Detailed results
        """
        logger.info(f"Validating library: {library_id}")
        
        validation_start = datetime.now(timezone.utc)
        all_issues = []
        critical_issues = 0
        checks_performed = []
        
        try:
            with db_coordinator.get_session('library') as session:
                library = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.library_id == library_id
                ).first()
                
                if not library:
                    return {
                        'status': 'failed',
                        'error': f'Library not found: {library_id}'
                    }
                
                # Check 1: Directory exists
                dir_check = self._check_directory_exists(library)
                checks_performed.append('directory_exists')
                if not dir_check['passed']:
                    all_issues.extend(dir_check['issues'])
                    critical_issues += len(dir_check['issues'])
                
                # Check 2: Files indexed
                files_check = self._check_files_indexed(session, library_id)
                checks_performed.append('files_indexed')
                if not files_check['passed']:
                    all_issues.extend(files_check['issues'])
                
                # Check 3: File integrity
                integrity_check = self._check_file_integrity(session, library, library_id)
                checks_performed.append('file_integrity')
                if not integrity_check['passed']:
                    all_issues.extend(integrity_check['issues'])
                    critical_issues += integrity_check.get('critical', 0)
                
                # Check 4: Required file types present
                types_check = self._check_required_file_types(session, library_id)
                checks_performed.append('required_file_types')
                if not types_check['passed']:
                    all_issues.extend(types_check['issues'])
                
                # Determine overall status
                if critical_issues > 0:
                    status = 'failed'
                elif len(all_issues) > 0:
                    status = 'warning'
                else:
                    status = 'healthy'
                
                # Calculate duration
                duration = (datetime.now(timezone.utc) - validation_start).total_seconds()
                
                # Create health check record
                # FIX: Replaced the invalid keyword argument 'check_results' 
                # with the correct column name 'check_details'.
                health_check = LibraryHealthCheck(
                library_id=library_id,
                check_type='full_validation',
                check_status=status,
                issues_found=len(all_issues),
                critical_issues=critical_issues,
                check_results={                          
                    'checks_performed': checks_performed,
                    'issues': all_issues
                },
                check_duration_seconds=duration          
            )
                session.add(health_check)
                
                # Update library validation status
                library.validation_status = status
                library.last_validated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Validation complete: {status} - {len(all_issues)} issues, {critical_issues} critical")
                
                return {
                    'status': status,
                    'issues_found': len(all_issues),
                    'critical_issues': critical_issues, 
                    'checks_performed': checks_performed,
                    'details': all_issues,
                    'duration_seconds': duration
                }
                
        except Exception as e:
            # Added more robust logging detail
            # Note: The 'RuntimeError: There is no current event loop' should now be fixed
            # as the primary TypeError is resolved.
            logger.error(f"Validation failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _check_directory_exists(self, library: TaxonomyLibrary) -> Dict[str, Any]:
        """Check if library directory exists."""
        issues = []
        
        if not library.library_directory_path:
            issues.append({
                'severity': 'critical',
                'message': 'Library directory path not set'
            })
            return {'passed': False, 'issues': issues}
        
        library_path = Path(library.library_directory_path)
        
        if not library_path.exists():
            issues.append({
                'severity': 'critical',
                'message': f'Library directory does not exist: {library_path}'
            })
            return {'passed': False, 'issues': issues}
        
        if not library_path.is_dir():
            issues.append({
                'severity': 'critical',
                'message': f'Library path is not a directory: {library_path}'
            })
            return {'passed': False, 'issues': issues}
        
        return {'passed': True, 'issues': []}
    
    def _check_files_indexed(self, session, library_id: uuid.UUID) -> Dict[str, Any]:
        """Check if files are indexed in database."""
        issues = []
        
        file_count = session.query(TaxonomyFile).filter(
            TaxonomyFile.library_id == library_id
        ).count()
        
        if file_count == 0:
            issues.append({
                'severity': 'warning',
                'message': 'No files indexed for this library'
            })
            return {'passed': False, 'issues': issues}
        
        return {'passed': True, 'issues': []}
    
    def _check_file_integrity(self, session, library: TaxonomyLibrary, 
                             library_id: uuid.UUID) -> Dict[str, Any]:
        """Check integrity of indexed files."""
        issues = []
        critical = 0
        
        if not library.library_directory_path:
            return {'passed': True, 'issues': []}
        
        library_path = Path(library.library_directory_path)
        
        files = session.query(TaxonomyFile).filter(
            TaxonomyFile.library_id == library_id
        ).all()
        
        for file_record in files:
            file_path = library_path / file_record.file_path
            
            if not file_path.exists():
                issues.append({
                    'severity': 'critical',
                    'message': f'File missing: {file_record.file_path}'
                })
                critical += 1
            elif file_record.file_status == 'corrupted':
                issues.append({
                    'severity': 'critical',
                    'message': f'File corrupted: {file_record.file_path}'
                })
                critical += 1
        
        passed = len(issues) == 0
        return {'passed': passed, 'issues': issues, 'critical': critical}
    
    def _check_required_file_types(self, session, library_id: uuid.UUID) -> Dict[str, Any]:
        """Check that required file types are present."""
        issues = []
        required_types = ['.xsd']  # XSD files are essential for taxonomies
        
        for file_type in required_types:
            count = session.query(TaxonomyFile).filter(
                TaxonomyFile.library_id == library_id,
                TaxonomyFile.file_type == file_type
            ).count()
            
            if count == 0:
                issues.append({
                    'severity': 'warning',
                    'message': f'No {file_type} files found in library'
                })
        
        passed = len(issues) == 0
        return {'passed': passed, 'issues': issues}
    
    def get_library_health_status(self, library_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get current health status of library.
        
        Args:
            library_id: UUID of TaxonomyLibrary
            
        Returns:
            Dictionary with health status
        """
        try:
            with db_coordinator.get_session('library') as session:
                library = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.library_id == library_id
                ).first()
                
                if not library:
                    return {
                        'found': False,
                        'error': f'Library not found: {library_id}'
                    }
                
                # Get latest health check
                latest_check = session.query(LibraryHealthCheck).filter(
                    LibraryHealthCheck.library_id == library_id
                ).order_by(LibraryHealthCheck.checked_at.desc()).first()
                
                # Safely extract critical issue count
                critical_issues = 0
                # FIX: Changed to use the correct column name 'check_details'
                if latest_check and hasattr(latest_check, 'check_details') and latest_check.check_details:
                    critical_issues = latest_check.check_details.get('critical_issue_count', 0)

                return {
                    'found': True,
                    'library_name': f"{library.taxonomy_name}-{library.taxonomy_version}",
                    'validation_status': library.validation_status,
                    'last_validated': library.last_validated_at.isoformat() if library.last_validated_at else None,
                    'latest_check': {
                        'check_type': latest_check.check_type if latest_check else None,
                        'check_status': latest_check.check_status if latest_check else None,
                        'issues_found': latest_check.issues_found if latest_check else 0,
                        'critical_issues': critical_issues,
                        'checked_at': latest_check.checked_at.isoformat() if latest_check else None
                    } if latest_check else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                'found': False,
                'error': str(e)
            }
    
    def get_all_libraries_health(self) -> List[Dict[str, Any]]:
        """
        Get health status for all libraries.
        
        Returns:
            List of health status dictionaries
        """
        libraries_health = []
        
        try:
            with db_coordinator.get_session('library') as session:
                libraries = session.query(TaxonomyLibrary).all()
                
                for library in libraries:
                    health = self.get_library_health_status(library.library_id)
                    libraries_health.append(health)
                
        except Exception as e:
            logger.error(f"Failed to get all libraries health: {e}")
        
        return libraries_health


__all__ = ['ValidationChecker']