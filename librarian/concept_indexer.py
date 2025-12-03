# File: /map_pro/engines/librarian/concept_indexer.py

"""
Map Pro Concept Indexer
=======================

Indexes taxonomy files and concepts into PostgreSQL library database.

Architecture: Uses library database models and map_pro_paths.
"""

import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from core.database_coordinator import db_coordinator
from database.models.library_models import TaxonomyLibrary, TaxonomyConcept, TaxonomyFile
from shared.exceptions.custom_exceptions import DatabaseError

logger = get_logger(__name__, 'engine')

BYTES_PER_MB = 1024 * 1024
FILE_READ_CHUNK_SIZE = 4096


class ConceptIndexer:
    """
    Indexes taxonomy files and concepts into PostgreSQL.
    
    Responsibilities:
    - Index taxonomy files in database
    - Track file metadata (size, hash, type)
    - Create concept records (basic info)
    - Update library statistics
    
    Does NOT handle:
    - Full concept parsing (requires XBRL parser)
    - Concept relationships (future enhancement)
    - Downloads (taxonomy_downloader handles this)
    """
    
    RELEVANT_EXTENSIONS = ['.xsd', '.xml', '.html', '.htm', '.xbri']
    
    def __init__(self):
        """Initialize concept indexer."""
        logger.info("Concept indexer initialized")
    
    def index_library_files(self, library_id: uuid.UUID, library_path: Path) -> Dict[str, Any]:
        """
        Index all relevant files in taxonomy library directory.
        
        Args:
            library_id: UUID of TaxonomyLibrary record
            library_path: Path to library directory
            
        Returns:
            Dictionary with indexing results:
                - files_indexed: Number of files indexed
                - files_skipped: Number of files skipped
                - total_size_mb: Total size of indexed files
                - errors: List of errors encountered
        """
        if not library_path.exists():
            logger.error(f"Library path does not exist: {library_path}")
            return {
                'files_indexed': 0,
                'files_skipped': 0,
                'total_size_mb': 0,
                'errors': [f"Library path not found: {library_path}"]
            }
        
        logger.info(f"Indexing library files: {library_path}")
        
        files_indexed = 0
        files_skipped = 0
        total_size = 0
        errors = []
        
        try:
            with db_coordinator.get_session('library') as session:
                for file_path in library_path.rglob('*'):
                    if not file_path.is_file():
                        continue
                    
                    if file_path.suffix.lower() not in self.RELEVANT_EXTENSIONS:
                        files_skipped += 1
                        continue
                    
                    try:
                        self._index_single_file(session, library_id, file_path, library_path)
                        files_indexed += 1
                        total_size += file_path.stat().st_size
                        
                    except Exception as e:
                        error_msg = f"Failed to index {file_path}: {e}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        files_skipped += 1
                
                session.commit()
        
        except Exception as e:
            logger.error(f"Database error during indexing: {e}")
            errors.append(f"Database error: {e}")
        
        logger.info(f"Indexing complete: {files_indexed} files indexed, {files_skipped} skipped")
        
        return {
            'files_indexed': files_indexed,
            'files_skipped': files_skipped,
            'total_size_mb': total_size / BYTES_PER_MB,
            'errors': errors
        }
    
    def _index_single_file(self, session, library_id: uuid.UUID, 
                          file_path: Path, library_root: Path):
        """
        Index single taxonomy file.
        
        Args:
            session: Database session
            library_id: UUID of parent library
            file_path: Path to file
            library_root: Root path of library (for relative path)
        """
        try:
            relative_path = file_path.relative_to(library_root)
        except ValueError:
            relative_path = file_path
        
        file_size = file_path.stat().st_size
        file_hash = self._calculate_file_hash(file_path)
        
        existing_file = session.query(TaxonomyFile).filter(
            TaxonomyFile.library_id == library_id,
            TaxonomyFile.file_path == str(relative_path)
        ).first()
        
        if existing_file:
            existing_file.file_size_bytes = file_size
            existing_file.file_hash_sha256 = file_hash
            existing_file.file_status = 'healthy'
            existing_file.last_validated_at = datetime.now(timezone.utc)
            logger.debug(f"Updated existing file record: {file_path.name}")
        else:
            taxonomy_file = TaxonomyFile(
                library_id=library_id,
                file_name=file_path.name,
                file_type=file_path.suffix.lower(),
                file_path=str(relative_path),
                file_size_bytes=file_size,
                file_hash_sha256=file_hash,
                concepts_defined=0,
                file_status='healthy'
            )
            session.add(taxonomy_file)
            logger.debug(f"Created new file record: {file_path.name}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for byte_block in iter(lambda: f.read(FILE_READ_CHUNK_SIZE), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def update_library_statistics(self, library_id: uuid.UUID) -> Dict[str, Any]:
        """
        Update library statistics based on indexed files.
        
        Args:
            library_id: UUID of TaxonomyLibrary
            
        Returns:
            Dictionary with updated statistics
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
                
                file_count = session.query(TaxonomyFile).filter(
                    TaxonomyFile.library_id == library_id
                ).count()
                
                files = session.query(TaxonomyFile).filter(
                    TaxonomyFile.library_id == library_id
                ).all()
                
                total_size = sum(f.file_size_bytes or 0 for f in files)
                
                concept_count = session.query(TaxonomyConcept).filter(
                    TaxonomyConcept.library_id == library_id
                ).count()
                
                library.total_files = file_count
                library.total_concepts = concept_count
                library.library_size_mb = total_size / BYTES_PER_MB
                library.last_validated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                logger.info(f"Updated library statistics: {file_count} files, {concept_count} concepts")
                
                return {
                    'success': True,
                    'total_files': file_count,
                    'total_concepts': concept_count,
                    'size_mb': library.library_size_mb
                }
                
        except Exception as e:
            logger.error(f"Failed to update library statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_file_integrity(self, library_id: uuid.UUID) -> Dict[str, Any]:
        """
        Verify integrity of indexed files by checking if they still exist and match hashes.
        
        Args:
            library_id: UUID of TaxonomyLibrary
            
        Returns:
            Dictionary with verification results
        """
        missing_files = []
        corrupted_files = []
        verified_files = 0
        
        try:
            with db_coordinator.get_session('library') as session:
                library = session.query(TaxonomyLibrary).filter(
                    TaxonomyLibrary.library_id == library_id
                ).first()
                
                if not library or not library.library_directory_path:
                    return {
                        'success': False,
                        'error': 'Library or directory path not found'
                    }
                
                library_path = Path(library.library_directory_path)
                
                files = session.query(TaxonomyFile).filter(
                    TaxonomyFile.library_id == library_id
                ).all()
                
                for file_record in files:
                    file_path = library_path / file_record.file_path
                    
                    if not file_path.exists():
                        missing_files.append(str(file_record.file_path))
                        file_record.file_status = 'missing'
                        continue
                    
                    if file_record.file_hash_sha256:
                        current_hash = self._calculate_file_hash(file_path)
                        if current_hash != file_record.file_hash_sha256:
                            corrupted_files.append(str(file_record.file_path))
                            file_record.file_status = 'corrupted'
                            continue
                    
                    file_record.file_status = 'healthy'
                    file_record.last_validated_at = datetime.now(timezone.utc)
                    verified_files += 1
                
                session.commit()
                
                logger.info(f"File integrity check: {verified_files} verified, "
                          f"{len(missing_files)} missing, {len(corrupted_files)} corrupted")
                
                return {
                    'success': True,
                    'verified_files': verified_files,
                    'missing_files': missing_files,
                    'corrupted_files': corrupted_files,
                    'total_checked': len(files)
                }
                
        except Exception as e:
            logger.error(f"File integrity verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


__all__ = ['ConceptIndexer']