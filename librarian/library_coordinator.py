"""
Map Pro Library Coordinator
===========================

Main librarian engine coordinator - inherits from BaseEngine.
Manages standard XBRL taxonomy library downloads, indexing, and validation.

Architecture: Follows map_pro BaseEngine pattern, uses library database.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date
import uuid
from pathlib import Path

from engines.base.engine_base import BaseEngine
from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.library_models import TaxonomyLibrary
from shared.constants.job_constants import JobType
from shared.exceptions.custom_exceptions import EngineError

from engines.librarian.taxonomy_downloader import TaxonomyDownloader
from engines.librarian.library_organizer import LibraryOrganizer
from engines.librarian.concept_indexer import ConceptIndexer
from engines.librarian.validation_checker import ValidationChecker
from engines.librarian.manual_processor import ManualProcessor
from engines.librarian.taxonomy_config import get_taxonomies_for_market, get_all_taxonomies
from engines.librarian.library_operations import LibraryOperations

logger = get_logger(__name__, 'engine')


class LibraryCoordinator(BaseEngine):
    """
    Main librarian engine - manages taxonomy libraries.
    
    Responsibilities:
    - Download missing taxonomy libraries
    - Extract and organize taxonomy files
    - Index taxonomy files into database
    - Validate library integrity
    - Support manual taxonomy processing
    
    Does NOT handle:
    - Company-specific XBRL parsing (parser engine handles this)
    - Concept mapping (mapper engine handles this)
    - Job queue processing (librarian works on-demand, not job-based)
    """
    
    def __init__(self):
        """Initialize library coordinator engine."""
        super().__init__("librarian")
        
        # Initialize components
        self.downloader = TaxonomyDownloader()
        self.organizer = LibraryOrganizer()
        self.indexer = ConceptIndexer()
        self.validator = ValidationChecker()
        self.manual_processor = ManualProcessor()
        
        # Initialize operations helper
        self.operations = LibraryOperations(
            self.downloader,
            self.organizer,
            self.indexer,
            self.validator
        )
        
        # Track failed downloads for user notification
        self.failed_downloads = []
        
        self.logger.info("Library coordinator initialized")
    
    def get_primary_database(self) -> str:
        """Return primary database name."""
        return 'library'
    
    def get_supported_job_types(self) -> List[str]:
            """
            Return supported job types.
            
            Updated: Now supports library dependency analysis jobs.
            """
            return [JobType.ANALYZE_LIBRARY_DEPENDENCIES.value]
        
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process library dependency analysis job.
        
        Delegates to LibraryDependencyAnalyzer component.
        """
        job_type = job_data.get('job_type')
        
        if job_type == JobType.ANALYZE_LIBRARY_DEPENDENCIES.value:
            # Delegate to library dependency analyzer
            from engines.librarian.library_dependency_analyzer import LibraryDependencyAnalyzer
            analyzer = LibraryDependencyAnalyzer()
            return await analyzer.process_job(job_data)
        else:
            raise NotImplementedError(f"Librarian engine does not support job type: {job_type}")
    
    async def ensure_market_taxonomies(self, market_type: str) -> Dict[str, Any]:
        """
        Ensure all required taxonomies for market are available.
        
        Args:
            market_type: Market identifier (sec, fca, esma, asic)
            
        Returns:
            Dictionary with results
        """
        self.logger.info(f"Ensuring taxonomies for market: {market_type}")
        
        required_taxonomies = get_taxonomies_for_market(market_type, required_only=True)
        self.logger.info(f"Found {len(required_taxonomies)} required taxonomies")
        
        available_count = 0
        downloaded_count = 0
        failed_count = 0
        self.failed_downloads = []
        
        for config in required_taxonomies:
            taxonomy_name = config['taxonomy_name']
            version = config['version']
            
            # Check if already available
            if await self.operations.is_library_available(taxonomy_name, version):
                available_count += 1
                self.logger.info(f"Already available: {taxonomy_name}-{version}")
                continue
            
            # Download and process
            result = await self.operations.download_and_index_library(config)
            
            if result['success']:
                downloaded_count += 1
                self.logger.info(f"Successfully downloaded: {taxonomy_name}-{version}")
            else:
                failed_count += 1
                self.failed_downloads.append({
                    'taxonomy_name': taxonomy_name,
                    'version': version,
                    'url': config['url'],
                    'error': result.get('error', 'Unknown error'),
                    'requires_manual': config.get('credentials_required', False)
                })
                self.logger.warning(f"Failed to download: {taxonomy_name}-{version}")
        
        # Notify user of failures
        if self.failed_downloads:
            self._log_download_failures()
        
        return {
            'market_type': market_type,
            'required_count': len(required_taxonomies),
            'available_count': available_count,
            'downloaded_count': downloaded_count,
            'failed_count': failed_count,
            'failed_downloads': self.failed_downloads
        }
    
    async def download_all_taxonomies(self) -> Dict[str, Any]:
        """
        Download all configured taxonomies.
        
        Returns:
            Dictionary with download results
        """
        self.logger.info("Downloading all configured taxonomies")
        
        all_taxonomies = get_all_taxonomies()
        total_count = len(all_taxonomies)
        
        available_count = 0
        downloaded_count = 0
        failed_count = 0
        self.failed_downloads = []
        
        for config in all_taxonomies:
            taxonomy_name = config['taxonomy_name']
            version = config['version']
            
            # Check if already available
            if await self.operations.is_library_available(taxonomy_name, version):
                available_count += 1
                continue
            
            # Download and process
            result = await self.operations.download_and_index_library(config)
            
            if result['success']:
                downloaded_count += 1
            else:
                failed_count += 1
                self.failed_downloads.append({
                    'taxonomy_name': taxonomy_name,
                    'version': version,
                    'url': config['url'],
                    'error': result.get('error', 'Unknown error'),
                    'requires_manual': config.get('credentials_required', False)
                })
        
        # Notify user of failures
        if self.failed_downloads:
            self._log_download_failures()
        
        return {
            'total_count': total_count,
            'available_count': available_count,
            'downloaded_count': downloaded_count,
            'failed_count': failed_count,
            'failed_downloads': self.failed_downloads
        }
    
    async def re_index_library(self, library_id: uuid.UUID) -> Dict[str, Any]:
        """
        Re-index an existing library that has no files indexed.
        
        Args:
            library_id: UUID of library to re-index
            
        Returns:
            Dictionary with re-indexing results
        """
        return await self.operations.re_index_library(library_id)
    
    def _log_download_failures(self):
        """Log download failures for user notification."""
        self.logger.warning(f"\n{'='*70}")
        self.logger.warning("TAXONOMY DOWNLOAD FAILURES")
        self.logger.warning(f"{'='*70}")
        
        for failure in self.failed_downloads:
            self.logger.warning(f"\nTaxonomy: {failure['taxonomy_name']}-{failure['version']}")
            self.logger.warning(f"URL: {failure['url']}")
            self.logger.warning(f"Error: {failure['error']}")
            
            if failure.get('requires_manual', False):
                self.logger.warning("[WARNING]  This taxonomy requires manual download (credentials needed)")
                self.logger.warning(f"   See manual processor instructions for details")
        
        self.logger.warning(f"\n{'='*70}")
        self.logger.warning(f"Total failed: {len(self.failed_downloads)}")
        self.logger.warning(f"Manual downloads may be required for some taxonomies")
        self.logger.warning(f"{'='*70}\n")
    
    def get_library_status(self) -> Dict[str, Any]:
        """Get status of all libraries."""
        try:
            with db_coordinator.get_session('library') as session:
                total_libraries = session.query(TaxonomyLibrary).count()
                active_libraries = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.library_status == 'active'
                ).count()
                
                libraries = session.query(TaxonomyLibrary).all()
                
                libraries_info = []
                for lib in libraries:
                    libraries_info.append({
                        'name': f"{lib.taxonomy_name}-{lib.taxonomy_version}",
                        'status': lib.library_status,
                        'validation': lib.validation_status,
                        'files': lib.total_files,
                        'size_mb': float(lib.library_size_mb) if lib.library_size_mb else 0,
                        'downloaded': lib.download_date.isoformat() if lib.download_date else None
                    })
                
                return {
                    'total_libraries': total_libraries,
                    'active_libraries': active_libraries,
                    'libraries': libraries_info
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get library status: {e}")
            return {
                'error': str(e)
            }
    
    def validate_all_libraries(self) -> Dict[str, Any]:
        """Validate all libraries."""
        validation_results = []
        
        try:
            with db_coordinator.get_session('library') as session:
                libraries = session.query(TaxonomyLibrary).all()
                
                for library in libraries:
                    result = self.validator.validate_library(library.library_id)
                    validation_results.append({
                        'library': f"{library.taxonomy_name}-{library.taxonomy_version}",
                        'status': result['status'],
                        'issues': result.get('issues_found', 0)
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to validate libraries: {e}")
            return {'error': str(e)}
        
        return {
            'libraries_validated': len(validation_results),
            'results': validation_results
        }
    
    # Expose internal methods through operations for backward compatibility
    async def _is_library_available(self, taxonomy_name: str, version: str) -> bool:
        """Check if library is available (for backward compatibility)."""
        return await self.operations.is_library_available(taxonomy_name, version)
    
    async def _download_and_index_library(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Download and index library (for backward compatibility)."""
        return await self.operations.download_and_index_library(config)


__all__ = ['LibraryCoordinator']

def create_librarian_engine() -> LibraryCoordinator:
    """Factory function to create librarian engine."""
    return LibraryCoordinator()