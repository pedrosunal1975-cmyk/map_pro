"""
Map Pro Library Operations - REALITY-AWARE VERSION
===================================================

CRITICAL CHANGE: Now verifies physical file existence before trusting database.
Database is a reflection of reality, not the source of truth.

Internal operations for library download, indexing, and management.
Used by LibraryCoordinator to handle detailed library processing tasks.

Save location: engines/librarian/library_operations.py
"""

import uuid
from typing import Dict, Any
from datetime import datetime, timezone, date
from pathlib import Path

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.library_models import TaxonomyLibrary

logger = get_logger(__name__, 'engine')


class LibraryOperations:
    """
    Helper class for library download and indexing operations.
    
    CRITICAL: All availability checks now verify physical files exist.
    """
    
    def __init__(self, downloader, organizer, indexer, validator):
        """Initialize library operations."""
        self.downloader = downloader
        self.organizer = organizer
        self.indexer = indexer
        self.validator = validator
        self.logger = logger
    
    async def download_and_index_library(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download and index a single taxonomy library.
        
        ENHANCED: Now checks physical reality before trusting database.
        
        Workflow:
        1. Check if library exists in database
        2. VERIFY files actually exist on disk
        3. If files missing -> download
        4. If files exist but not indexed -> re-index
        """
        taxonomy_name = config['taxonomy_name']
        version = config['version']
        
        try:
            with db_coordinator.get_session('library') as session:
                existing = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.taxonomy_name == taxonomy_name,
                    TaxonomyLibrary.taxonomy_version == version
                ).first()
                
                if existing:
                    # CRITICAL: Check if files actually exist
                    if existing.is_truly_available:
                        self.logger.info(
                            f"Library ready: {taxonomy_name}-{version} "
                            f"({existing.actual_file_count} files verified on disk)"
                        )
                        return {
                            'success': True,
                            'library_id': str(existing.library_id),
                            'already_exists': True,
                            'files_verified': existing.actual_file_count
                        }
                    
                    # Files missing or database wrong - sync with reality
                    sync_result = existing.sync_with_reality()
                    session.commit()
                    
                    if sync_result['actual_files'] == 0:
                        self.logger.warning(
                            f"Library {taxonomy_name}-{version} has no files on disk. "
                            f"Database said {sync_result['recorded_files']}, reality shows 0. "
                            "Proceeding with download..."
                        )
                        # Fall through to download
                    else:
                        self.logger.info(
                            f"Library {taxonomy_name}-{version} has files but not indexed. "
                            f"Re-indexing {sync_result['actual_files']} files..."
                        )
                        return await self.re_index_library(existing.library_id)
            
            # Library doesn't exist or has no files - download
            self.logger.info(f"Downloading taxonomy: {taxonomy_name}-{version}")
            
            # FIXED: Convert config to DownloadConfig format
            # DownloadConfig expects: url, folder_name, file_type, credentials_required
            download_config = self._prepare_download_config(config)
            
            # Download
            download_result = await self.downloader.download_taxonomy(download_config)
            
            if not download_result['success']:
                return {
                    'success': False,
                    'error': download_result.get('error', 'Download failed')
                }
            
            # Organize extracted files
            extract_path = Path(download_result['extract_path'])
            
            # Extract any nested archives
            extract_result = self.organizer.extract_nested_archives(extract_path)
            
            # Clean directory (remove archives after extraction)
            clean_result = self.organizer.clean_directory(extract_path, remove_archives=True)
            
            # Get final directory info
            dir_info = self.organizer.get_directory_info(extract_path)
            
            # Create library record
            library_id = await self._create_or_update_library_record(
                config, 
                download_result
            )
            
            # Index files
            index_result = self.indexer.index_library_files(
                library_id,
                Path(download_result['extract_path'])
            )
            
            if index_result['files_indexed'] == 0:
                self.logger.warning(
                    f"No files indexed for {taxonomy_name}-{version}. "
                    f"Errors: {index_result.get('errors', [])}"
                )
            
            # Update statistics
            self.indexer.update_library_statistics(library_id)
            
            # Validate
            validation_result = self.validator.validate_library(library_id)
            
            return {
                'success': True,
                'library_id': str(library_id),
                'files_indexed': index_result['files_indexed'],
                'validation_status': validation_result['status']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to download/index {taxonomy_name}-{version}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _prepare_download_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert library config to DownloadConfig format.
        
        Maps from library config keys to DownloadConfig keys:
        - taxonomy_name -> folder_name (with version appended)
        - url -> url
        - file_type -> file_type (default: zip)
        - credentials_required -> credentials_required (default: False)
        
        Args:
            config: Library configuration dictionary
            
        Returns:
            Dictionary formatted for DownloadConfig
        """
        # Create folder name from taxonomy name and version
        folder_name = f"{config['taxonomy_name']}-{config['version']}"
        
        return {
            'url': config['url'],
            'folder_name': folder_name,
            'file_type': config.get('file_type', 'zip'),
            'credentials_required': config.get('credentials_required', False)
        }
    
    async def _create_or_update_library_record(
        self, 
        config: Dict[str, Any], 
        download_result: Dict[str, Any]
    ) -> uuid.UUID:
        """Create or update library record in database."""
        with db_coordinator.get_session('library') as session:
            existing = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.taxonomy_name == config['taxonomy_name'],
                TaxonomyLibrary.taxonomy_version == config['version']
            ).first()
            
            if existing:
                self.logger.info(
                    f"Updating existing library: {config['taxonomy_name']}-{config['version']}"
                )
                
                existing.library_directory_path = download_result['extract_path']
                existing.library_size_mb = download_result.get('size_mb', 0)
                existing.download_date = date.today()
                existing.library_status = 'active'
                existing.validation_status = 'pending'
                
                session.commit()
                return existing.library_id
            
            # Create new library record
            library = TaxonomyLibrary(
                taxonomy_name=config['taxonomy_name'],
                taxonomy_version=config['version'],
                taxonomy_authority=config['authority'],
                base_namespace=config['namespace'],
                library_status='active',
                download_source_url=config['url'],
                library_directory_path=download_result['extract_path'],
                library_size_mb=download_result.get('size_mb', 0),
                download_date=date.today(),
                validation_status='pending',
                is_required_by_markets=config.get('market_types', [])
            )
            
            session.add(library)
            session.flush()
            library_id = library.library_id
            
            session.commit()
            
            self.logger.info(f"Created library record: {library_id}")
            return library_id
    
    async def re_index_library(self, library_id: uuid.UUID) -> Dict[str, Any]:
        """
        Re-index an existing library.
        
        ENHANCED: Verifies files exist before attempting to index.
        """
        try:
            with db_coordinator.get_session('library') as session:
                library = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.library_id == library_id
                ).first()
                
                if not library:
                    return {
                        'success': False,
                        'error': f'Library not found: {library_id}'
                    }
                
                # CRITICAL: Verify directory exists
                if not library.directory_exists:
                    return {
                        'success': False,
                        'error': f'Library directory not found: {library.library_directory_path}'
                    }
                
                # CRITICAL: Verify files exist
                if library.actual_file_count == 0:
                    return {
                        'success': False,
                        'error': f'Library directory is empty: {library.library_directory_path}'
                    }
                
                library_path = Path(library.library_directory_path)
                
                self.logger.info(
                    f"Re-indexing library: {library.taxonomy_name}-{library.taxonomy_version} "
                    f"({library.actual_file_count} files found on disk)"
                )
                
                # Index files
                index_result = self.indexer.index_library_files(library_id, library_path)
                
                if index_result['files_indexed'] == 0:
                    self.logger.error(
                        f"Re-indexing failed: No files indexed. "
                        f"Errors: {index_result.get('errors', [])}"
                    )
                
                # Update statistics
                self.indexer.update_library_statistics(library_id)
                
                # Validate
                validation_result = self.validator.validate_library(library_id)
                
                return {
                    'success': index_result['files_indexed'] > 0,
                    'library_id': str(library_id),
                    'files_indexed': index_result['files_indexed'],
                    'validation_status': validation_result['status']
                }
                
        except Exception as e:
            self.logger.error(f"Failed to re-index library {library_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def is_library_available(self, taxonomy_name: str, version: str) -> bool:
        """
        Check if library is available for use.
        
        CRITICAL CHANGE: Now verifies physical files exist.
        Returns True ONLY if:
        - Library record exists in database
        - Database says it has files
        - Files ACTUALLY exist on disk
        
        Args:
            taxonomy_name: Name of taxonomy
            version: Version string
            
        Returns:
            True if library is genuinely available
        """
        try:
            with db_coordinator.get_session('library') as session:
                library = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.taxonomy_name == taxonomy_name,
                    TaxonomyLibrary.taxonomy_version == version
                ).first()
                
                if not library:
                    self.logger.debug(f"Library not in database: {taxonomy_name}-{version}")
                    return False
                
                # Use the new reality-checking property
                if library.is_truly_available:
                    self.logger.info(
                        f"[OK] Library verified available: {taxonomy_name}-{version} "
                        f"({library.actual_file_count} files on disk)"
                    )
                    return True
                
                # Library not truly available - log why
                if not library.directory_exists:
                    self.logger.warning(
                        f"[FAIL] Library directory missing: {taxonomy_name}-{version} "
                        f"(expected at {library.library_directory_path})"
                    )
                elif library.actual_file_count == 0:
                    self.logger.warning(
                        f"[FAIL] Library directory empty: {taxonomy_name}-{version} "
                        f"(database says {library.total_files} files)"
                    )
                else:
                    self.logger.warning(
                        f"[FAIL] Library not ready: {taxonomy_name}-{version} "
                        f"(status: {library.library_status})"
                    )
                
                # Sync database with reality
                sync_result = library.sync_with_reality()
                if sync_result['changed']:
                    session.commit()
                    self.logger.info(
                        f"Database synchronized: {taxonomy_name}-{version} "
                        f"({sync_result['recorded_files']} -> {sync_result['actual_files']} files)"
                    )
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking library availability: {e}")
            return False


__all__ = ['LibraryOperations']