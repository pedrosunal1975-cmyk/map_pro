"""
Map Pro Library Organizer
=========================

Organizes taxonomy library file structure and handles nested archives.
Inspired by xbrl_parser's recursive extraction patterns.

Architecture: Uses map_pro_paths for all file operations.
"""

import os
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, List

try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'engine')


class LibraryOrganizer:
    """
    Organizes taxonomy library file structure.
    
    Responsibilities:
    - Extract nested archives recursively
    - Clean up temporary files
    - Organize directory structure
    - Identify relevant taxonomy files
    
    Does NOT handle:
    - Initial downloads (taxonomy_downloader handles this)
    - Database operations (library_coordinator handles this)
    - File indexing (concept_indexer handles this)
    """
    
    # Relevant file extensions for XBRL taxonomies
    RELEVANT_EXTENSIONS = ['.xsd', '.xml', '.html', '.htm', '.xbri']
    
    # Archive extensions to extract
    ARCHIVE_EXTENSIONS = ['.zip', '.tar', '.tar.gz', '.tgz', '.7z']
    
    def __init__(self):
        """Initialize library organizer."""
        self.libraries_dir = map_pro_paths.data_taxonomies / "libraries"
        logger.info("Library organizer initialized")
    
    def extract_nested_archives(self, directory: Path) -> Dict[str, Any]:
        """
        Recursively extract all nested archives in directory.
        Inspired by xbrl_parser's recursive extraction pattern.
        
        Args:
            directory: Directory to scan for nested archives
            
        Returns:
            Dictionary with extraction results:
                - archives_found: Number of archives found
                - archives_extracted: Number successfully extracted
                - extraction_errors: List of errors
        """
        logger.info(f"Scanning for nested archives in: {directory}")
        
        archives_found = 0
        archives_extracted = 0
        extraction_errors = []
        
        # Keep extracting until no more archives found
        files_found = True
        iteration = 0
        max_iterations = 10  # Prevent infinite loops
        
        while files_found and iteration < max_iterations:
            files_found = False
            iteration += 1
            
            logger.info(f"Nested archive extraction iteration {iteration}")
            
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    file_path = Path(root) / filename
                    
                    if self._is_archive(file_path):
                        archives_found += 1
                        files_found = True
                        
                        try:
                            self._extract_archive(file_path, Path(root))
                            archives_extracted += 1
                            
                            # Remove extracted archive
                            file_path.unlink()
                            logger.info(f"Extracted and removed: {file_path}")
                            
                        except Exception as e:
                            error_msg = f"Failed to extract {file_path}: {e}"
                            logger.warning(error_msg)
                            extraction_errors.append(error_msg)
            
            if files_found:
                logger.info(f"Found {archives_found} archives in iteration {iteration}")
        
        if iteration >= max_iterations:
            logger.warning(f"Stopped after {max_iterations} iterations (max reached)")
        
        logger.info(f"Nested extraction complete: {archives_extracted}/{archives_found} archives extracted")
        
        return {
            'archives_found': archives_found,
            'archives_extracted': archives_extracted,
            'extraction_errors': extraction_errors,
            'iterations': iteration
        }
    
    def _extract_archive(self, archive_path: Path, extract_dir: Path):
        """
        Extract archive based on file type.
        
        Args:
            archive_path: Path to archive file
            extract_dir: Directory to extract to
        """
        suffix = archive_path.suffix.lower()
        
        if suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logger.debug(f"Extracted ZIP: {archive_path.name}")
            
        elif suffix in ['.tar', '.tgz'] or archive_path.name.endswith('.tar.gz'):
            if tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_dir, filter='data')
                logger.debug(f"Extracted TAR: {archive_path.name}")
            else:
                raise ValueError(f"Invalid TAR file: {archive_path}")
                
        elif suffix == '.7z':
            if not PY7ZR_AVAILABLE:
                raise ImportError("py7zr library not available for .7z extraction")
            
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                archive.extractall(extract_dir)
            logger.debug(f"Extracted 7Z: {archive_path.name}")
            
        else:
            raise ValueError(f"Unsupported archive type: {suffix}")
    
    def _is_archive(self, file_path: Path) -> bool:
        """Check if file is an archive that should be extracted."""
        suffix = file_path.suffix.lower()
        
        # Check standard extensions
        if suffix in self.ARCHIVE_EXTENSIONS:
            return True
        
        # Check .tar.gz pattern
        if file_path.name.endswith('.tar.gz'):
            return True
        
        return False
    
    def count_relevant_files(self, directory: Path) -> Dict[str, Any]:
        """
        Count relevant taxonomy files in directory.
        
        Args:
            directory: Directory to scan
            
        Returns:
            Dictionary with file counts by type
        """
        file_counts = {ext: 0 for ext in self.RELEVANT_EXTENSIONS}
        file_counts['total'] = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix in self.RELEVANT_EXTENSIONS:
                    file_counts[suffix] += 1
                    file_counts['total'] += 1
        
        return file_counts
    
    def find_relevant_files(self, directory: Path) -> List[Path]:
        """
        Find all relevant taxonomy files in directory.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of paths to relevant files
        """
        relevant_files = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.RELEVANT_EXTENSIONS:
                relevant_files.append(file_path)
        
        return relevant_files
    
    def clean_directory(self, directory: Path, remove_archives: bool = True) -> Dict[str, Any]:
        """
        Clean up directory by removing unwanted files.
        
        Args:
            directory: Directory to clean
            remove_archives: If True, remove archive files
            
        Returns:
            Dictionary with cleanup results
        """
        removed_count = 0
        removed_size = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                should_remove = False
                
                # Remove archives if requested
                if remove_archives and self._is_archive(file_path):
                    should_remove = True
                
                # Remove temp files
                if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
                    should_remove = True
                
                if should_remove:
                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        removed_count += 1
                        removed_size += size
                        logger.debug(f"Removed: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {file_path}: {e}")
        
        logger.info(f"Cleaned directory: removed {removed_count} files ({removed_size / 1024:.2f} KB)")
        
        return {
            'removed_count': removed_count,
            'removed_size_kb': removed_size / 1024
        }
    
    def get_directory_info(self, directory: Path) -> Dict[str, Any]:
        """
        Get comprehensive information about directory.
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Dictionary with directory information
        """
        if not directory.exists():
            return {
                'exists': False,
                'path': str(directory)
            }
        
        total_files = 0
        total_size = 0
        relevant_files = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size
                
                if file_path.suffix.lower() in self.RELEVANT_EXTENSIONS:
                    relevant_files += 1
        
        return {
            'exists': True,
            'path': str(directory),
            'total_files': total_files,
            'relevant_files': relevant_files,
            'total_size_mb': total_size / (1024 * 1024),
            'name': directory.name
        }


__all__ = ['LibraryOrganizer']