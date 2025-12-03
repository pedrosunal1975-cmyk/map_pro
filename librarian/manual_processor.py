"""
Map Pro Manual Processor
========================

Handles manually downloaded taxonomy files (e.g., IFRS that couldn't be auto-downloaded).
Processes files placed in manual downloads directory.

Architecture: Uses map_pro_paths for all file operations.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from core.database_coordinator import db_coordinator
from database.models.library_models import TaxonomyLibrary
from .library_organizer import LibraryOrganizer
from .concept_indexer import ConceptIndexer

logger = get_logger(__name__, 'engine')


class ManualProcessor:
    """
    Processes manually downloaded taxonomy files.
    
    Use case: When automatic downloads fail (e.g., IFRS requiring credentials),
    user can manually download ZIP files and place them in the manual directory.
    This processor will extract, organize, and index them.
    
    Responsibilities:
    - Scan manual downloads directory
    - Match files to taxonomy configurations
    - Extract and organize files
    - Trigger indexing
    
    Does NOT handle:
    - Automatic downloads (taxonomy_downloader handles this)
    - Complex parsing (future enhancement)
    """
    
    def __init__(self):
        """Initialize manual processor."""
        self.manual_dir = map_pro_paths.data_taxonomies / "manual_downloads"
        self.libraries_dir = map_pro_paths.data_taxonomies / "libraries"
        self.processed_dir = map_pro_paths.data_taxonomies / "manual_processed"
        
        # Create directories
        self.manual_dir.mkdir(parents=True, exist_ok=True)
        self.libraries_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize helper components
        self.organizer = LibraryOrganizer()
        self.indexer = ConceptIndexer()
        
        logger.info("Manual processor initialized")
    
    def scan_manual_directory(self) -> List[Dict[str, Any]]:
        """
        Scan manual downloads directory for files to process.
        
        Returns:
            List of dictionaries with file information
        """
        manual_files = []
        
        for file_path in self.manual_dir.iterdir():
            if file_path.is_file():
                manual_files.append({
                    'filename': file_path.name,
                    'path': str(file_path),
                    'size_mb': file_path.stat().st_size / (1024 * 1024),
                    'extension': file_path.suffix.lower()
                })
        
        logger.info(f"Found {len(manual_files)} files in manual directory")
        return manual_files
    
    def process_manual_file(self, filename: str, target_library_name: str, 
                           target_version: str) -> Dict[str, Any]:
        """
        Process a manually downloaded file.
        
        Args:
            filename: Name of file in manual directory
            target_library_name: Target taxonomy name (e.g., 'ifrs', 'us-gaap')
            target_version: Target version (e.g., '2025', '2024')
            
        Returns:
            Dictionary with processing results
        """
        file_path = self.manual_dir / filename
        
        if not file_path.exists():
            return {
                'success': False,
                'error': f'File not found: {filename}'
            }
        
        logger.info(f"Processing manual file: {filename} for {target_library_name}-{target_version}")
        
        # Determine extract directory
        folder_name = f"{target_library_name}-{target_version}"
        extract_path = self.libraries_dir / folder_name
        extract_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extract file
            if file_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                logger.info(f"Extracted to: {extract_path}")
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_path.suffix}'
                }
            
            # Extract nested archives
            nested_result = self.organizer.extract_nested_archives(extract_path)
            
            # Get file counts
            file_counts = self.organizer.count_relevant_files(extract_path)
            
            # Move processed file to processed directory
            processed_path = self.processed_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{filename}"
            shutil.move(file_path, processed_path)
            
            logger.info(f"Successfully processed {filename}: {file_counts['total']} relevant files")
            
            return {
                'success': True,
                'extract_path': str(extract_path),
                'folder_name': folder_name,
                'file_count': file_counts['total'],
                'nested_archives': nested_result['archives_extracted'],
                'processed_file_moved_to': str(processed_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def register_manual_library(self, folder_name: str, taxonomy_name: str, 
                               version: str, authority: str, 
                               namespace: str, market_types: List[str]) -> Dict[str, Any]:
        """
        Register a manually processed library in the database.
        
        Args:
            folder_name: Name of folder in libraries directory
            taxonomy_name: Taxonomy name (e.g., 'ifrs')
            version: Version string
            authority: Authority name (e.g., 'IFRS Foundation')
            namespace: XML namespace
            market_types: List of market types using this taxonomy
            
        Returns:
            Dictionary with registration results including library_id
        """
        library_path = self.libraries_dir / folder_name
        
        if not library_path.exists():
            return {
                'success': False,
                'error': f'Library directory not found: {folder_name}'
            }
        
        logger.info(f"Registering manual library: {taxonomy_name}-{version}")
        
        try:
            with db_coordinator.get_session('library') as session:
                # Check if library already exists
                existing = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.taxonomy_name == taxonomy_name,
                    TaxonomyLibrary.taxonomy_version == version
                ).first()
                
                if existing:
                    logger.info(f"Library already registered: {taxonomy_name}-{version}")
                    library_id = existing.library_id
                else:
                    # Create new library record
                    library = TaxonomyLibrary(
                        taxonomy_name=taxonomy_name,
                        taxonomy_version=version,
                        taxonomy_authority=authority,
                        base_namespace=namespace,
                        library_status='active',
                        download_source_url='manual',
                        library_directory_path=str(library_path),
                        download_date=datetime.now(timezone.utc).date(),
                        validation_status='pending',
                        is_required_by_markets=market_types
                    )
                    
                    session.add(library)
                    session.flush()
                    library_id = library.library_id
                    
                    logger.info(f"Created library record: {library_id}")
                
                session.commit()
            
            # Index files
            logger.info("Indexing library files...")
            index_result = self.indexer.index_library_files(library_id, library_path)
            
            # Update statistics
            stats_result = self.indexer.update_library_statistics(library_id)
            
            return {
                'success': True,
                'library_id': str(library_id),
                'files_indexed': index_result['files_indexed'],
                'total_files': stats_result.get('total_files', 0),
                'size_mb': stats_result.get('size_mb', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to register manual library: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_manual_instructions(self) -> str:
        """
        Get instructions for manual taxonomy downloads.
        
        Returns:
            Formatted instruction string
        """
        instructions = f"""
Manual Taxonomy Download Instructions
=====================================

If automatic downloads fail (e.g., IFRS requiring credentials), follow these steps:

1. **Download the taxonomy ZIP file** manually from the source website
   
2. **Place the ZIP file** in this directory:
   {self.manual_dir}
   
3. **Use the manual processor** to extract and register the library:
   
   Example for IFRS 2025:
   ```python
   from engines.librarian import ManualProcessor
   
   processor = ManualProcessor()
   
   # Process the file
   result = processor.process_manual_file(
       filename='IFRSAT-2025.zip',
       target_library_name='ifrs',
       target_version='2025'
   )
   
   # Register in database
   if result['success']:
       reg_result = processor.register_manual_library(
           folder_name='ifrs-2025',
           taxonomy_name='ifrs',
           version='2025',
           authority='IFRS Foundation',
           namespace='http://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full',
           market_types=['fca', 'esma', 'asic']
       )
   ```

Common Manual Downloads:
- IFRS taxonomies (require IFRS account)
- Some regional taxonomies with access restrictions
- Historical taxonomy versions no longer available online

Processed files are automatically moved to:
{self.processed_dir}
"""
        return instructions


__all__ = ['ManualProcessor']