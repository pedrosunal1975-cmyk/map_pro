# File: /map_pro/engines/librarian/library_availability_checker.py

"""
Library Availability Checker
=============================

Checks availability of taxonomy libraries and coordinates downloads.
Verifies both database records and disk-based availability.

Features:
- Database availability checking
- Disk-based library verification
- Download coordination
- Download result tracking
"""

import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from core.database_coordinator import db_coordinator
from database.models.library_models import TaxonomyLibrary

logger = get_logger(__name__, 'engine')

# Library status constants
LIBRARY_STATUS_ACTIVE = 'active'
# FIX: Increase the minimum file threshold to a non-zero value 
# to prevent empty/placeholder folders from being considered 'available' on disk.
MIN_FILES_THRESHOLD = 10 


class LibraryAvailabilityChecker:
    """
    Checks and manages taxonomy library availability.
    
    Checks both:
    1. Database records (TaxonomyLibrary table) - MUST be Active and Healthy
    2. Disk-based availability (library directory structure) - MUST have enough files
    
    A library is only considered 'available' if both checks pass.
    """
    
    def __init__(self, library_operations=None):
        """
        Initialize availability checker.
        
        Args:
            library_operations: LibraryOperations instance for downloads
        """
        self.library_operations = library_operations
        logger.debug("Library availability checker initialized")
    
    async def check_library_availability(
        self, 
        required_libraries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check which required libraries are available.
        
        A library is available only if its DB record is READY (Active + Healthy) 
        AND its files exist on disk (count > MIN_FILES_THRESHOLD).
        
        Args:
            required_libraries: List of library configurations with
                               taxonomy_name and version
        
        Returns:
            Dictionary with:
                - available_libraries: List of available library configs
                - missing_libraries: List of missing library configs
                - total_required: Total number of required libraries
                - available_count: Number of available libraries
                - missing_count: Number of missing libraries
        """
        available_libraries = []
        missing_libraries = []
        
        logger.info(f"Checking availability for {len(required_libraries)} required libraries.")
        
        try:
            with db_coordinator.get_session('library') as session:
                for lib_config in required_libraries:
                    taxonomy_name = lib_config['taxonomy_name']
                    version = lib_config['version']
                    
                    db_ready = self._is_in_database(session, taxonomy_name, version)
                    disk_exists = self._is_on_disk(taxonomy_name, version)
                    
                    if db_ready and disk_exists:
                        # Success: DB is ready AND files are confirmed to exist
                        available_libraries.append(lib_config)
                        logger.info(
                            f"Available (DB Ready + Disk OK): {taxonomy_name}-{version}"
                        )
                    else:
                        # Failure: Treat as missing to force re-processing
                        missing_libraries.append(lib_config)
                        
                        if db_ready and not disk_exists:
                            logger.warning(
                                f"Missing (DB Ready, but DISK EMPTY): {taxonomy_name}-{version}. Will queue for re-download."
                            )
                        elif not db_ready and disk_exists:
                            logger.warning(
                                f"Missing (Disk OK, but DB Not Ready): {taxonomy_name}-{version}. Will queue for re-index."
                            )
                        else:
                            logger.debug(f"Missing (DB Not Ready + Disk Empty): {taxonomy_name}-{version}")
                        
        except Exception as e:
            logger.error(f"Failed to check library availability: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        logger.info(
            f"Availability check complete: {len(available_libraries)} available, "
            f"{len(missing_libraries)} missing."
        )
        
        return {
            'available_libraries': available_libraries,
            'missing_libraries': missing_libraries,
            'total_required': len(required_libraries),
            'available_count': len(available_libraries),
            'missing_count': len(missing_libraries)
        }
    
    def _is_in_database(
        self, 
        session, 
        taxonomy_name: str, 
        version: str
    ) -> bool:
        """
        Check if library exists in database with active and HEALTHY status.
        
        Args:
            session: Database session
            taxonomy_name: Name of taxonomy
            version: Version of taxonomy
            
        Returns:
            True if library exists, is active, is healthy, and has files
        """
        try:
            library = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.taxonomy_name == taxonomy_name,
                TaxonomyLibrary.taxonomy_version == version
            ).first()
            
            # Strictest possible check for DB readiness
            is_ready = (
                library is not None and 
                library.library_status == LIBRARY_STATUS_ACTIVE and
                # Require explicit 'healthy' status to be considered fully ready
                getattr(library, 'validation_status', 'unknown') == 'healthy' and 
                library.total_files > MIN_FILES_THRESHOLD
            )
            
            if library is not None and not is_ready:
                 logger.debug(
                     f"DB record for {taxonomy_name}-{version} found but not ready: "
                     f"Status={library.library_status}, Validation={getattr(library, 'validation_status', 'N/A')}"
                 )
            
            return is_ready
            
        except Exception as e:
            logger.error(
                f"Database check error for {taxonomy_name}-{version}: {e}"
            )
            return False
    
    def _is_on_disk(self, taxonomy_name: str, version: str) -> bool:
        """
        Check if library exists on disk and contains a sufficient number of files.
        
        Uses MIN_FILES_THRESHOLD to distinguish between a complete download 
        and an empty or placeholder directory.
        
        Args:
            taxonomy_name: Name of taxonomy
            version: Version of taxonomy
            
        Returns:
            True if library directory exists with sufficient files
        """
        try:
            library_dir = (
                map_pro_paths.data_taxonomies / 
                "libraries" / 
                f"{taxonomy_name}-{version}"
            )
            
            if not library_dir.exists():
                return False
            
            # FIX: Count all files in the directory recursively and compare to the threshold
            file_count = sum(
                1 for item in library_dir.rglob("*") 
                if item.is_file()
            )
            
            if file_count > MIN_FILES_THRESHOLD:
                logger.debug(
                    f"Found {file_count} files in {library_dir}. Threshold is {MIN_FILES_THRESHOLD}."
                )
                return True
            
            logger.debug(
                f"Found only {file_count} files in {library_dir}. Not enough to pass threshold of {MIN_FILES_THRESHOLD}."
            )
            return False
            
        except Exception as e:
            logger.warning(
                f"Error checking disk for {taxonomy_name}-{version}: {e}"
            )
            return False
    
    async def ensure_required_libraries(
        self, 
        missing_libraries: List[Dict[str, Any]], 
        market_type: str
    ) -> Dict[str, Any]:
        """
        Trigger download of missing libraries.
        
        Args:
            missing_libraries: List of missing library configurations
            market_type: Market type for context
            
        Returns:
            Dictionary with:
                - downloaded_count: Number successfully downloaded
                - failed_count: Number that failed
                - manual_required: List of libraries requiring manual download
                - download_details: Detailed results for each library
        """
        if not missing_libraries:
            return {
                'downloaded_count': 0,
                'failed_count': 0,
                'manual_required': [],
                'download_details': []
            }
        
        if self.library_operations is None:
            logger.error("Library operations not configured, cannot download")
            return {
                'downloaded_count': 0,
                'failed_count': len(missing_libraries),
                'manual_required': [],
                'download_details': [],
                'error': 'Download system not configured'
            }
        
        logger.info(
            f"Triggering download/re-index for {len(missing_libraries)} missing libraries"
        )
        
        downloaded_count = 0
        failed_count = 0
        manual_required = []
        download_details = []
        
        for lib_config in missing_libraries:
            try:
                result = await self._download_single_library(lib_config)
                
                download_details.append(result)
                
                if result['success']:
                    downloaded_count += 1
                else:
                    failed_count += 1
                    if result.get('requires_manual', False):
                        manual_required.append(lib_config)
                
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Processing error for {lib_config['taxonomy_name']}: {e}"
                )
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'downloaded_count': downloaded_count,
            'failed_count': failed_count,
            'manual_required': manual_required,
            'download_details': download_details
        }
    
    async def _download_single_library(
        self, 
        lib_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Download/Re-index a single library.
        
        The decision to download or re-index is handled internally by
        library_operations.download_and_index_library, which is called
        for all 'missing' libraries.
        
        Args:
            lib_config: Library configuration
            
        Returns:
            Dictionary with download result
        """
        taxonomy_name = lib_config['taxonomy_name']
        version = lib_config['version']
        
        # Check if files exist to determine if we are downloading or re-indexing
        action = "re-indexing" if self._is_on_disk(taxonomy_name, version) else "downloading"

        logger.info(f"Initiating {action} {taxonomy_name}-{version}")
        
        try:
            # library_operations.download_and_index_library is assumed to handle 
            # the internal check: if files exist, skip download and start indexing.
            result = await self.library_operations.download_and_index_library(
                lib_config
            )
            
            if result['success']:
                logger.info(
                    f"Successfully processed {taxonomy_name}-{version}"
                )
            else:
                logger.warning(
                    f"Failed to process {taxonomy_name}-{version}: "
                    f"{result.get('error')}"
                )
            
            return self._create_download_detail(
                taxonomy_name,
                version,
                success=result['success'],
                error=result.get('error'),
                requires_manual=lib_config.get('credentials_required', False)
            )
            
        except Exception as e:
            logger.error(f"Processing exception for {taxonomy_name}-{version}: {e}")
            return self._create_download_detail(
                taxonomy_name,
                version,
                success=False,
                error=str(e),
                requires_manual=False
            )
    
    def _create_download_detail(
        self,
        taxonomy_name: str,
        version: str,
        success: bool,
        error: Optional[str],
        requires_manual: bool,
        skipped: bool = False
    ) -> Dict[str, Any]:
        """
        Create standardized download detail dictionary.
        
        Args:
            taxonomy_name: Name of taxonomy
            version: Version of taxonomy
            success: Whether download succeeded
            error: Error message if failed
            requires_manual: Whether manual download is needed
            skipped: Whether download was skipped (already on disk)
            
        Returns:
            Dictionary with download details
        """
        detail = {
            'taxonomy_name': taxonomy_name,
            'version': version,
            'success': success,
            'error': error,
            'requires_manual': requires_manual
        }
        
        if skipped:
            detail['skipped_disk_available'] = True
        
        return detail


__all__ = ['LibraryAvailabilityChecker']