# File: /map_pro/engines/extractor/archive_handlers.py

"""
Map Pro Archive Handlers
========================

Handles extraction of different archive formats (ZIP, TAR, GZ, etc.).
Provides format-specific extraction logic with error handling.

Architecture: Protocol-agnostic archive extraction handlers.
"""

import zipfile
import tarfile
import gzip
import shutil
from pathlib import Path
from typing import Dict, Any, List
from abc import ABC, abstractmethod

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')

GZIP_READ_TEST_BYTES = 1


class ArchiveHandler(ABC):
    """Base class for archive handlers."""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}", 'engine')
    
    @abstractmethod
    async def extract(self, archive_path: Path, destination: Path) -> Dict[str, Any]:
        """
        Extract archive to destination.
        
        Args:
            archive_path: Path to archive file
            destination: Path to extract to
            
        Returns:
            Dictionary with extraction results:
            {
                'success': bool,
                'files_extracted': int,
                'files': List[Path],
                'error': Optional[str]
            }
        """
        pass
    
    @abstractmethod
    def validate_archive(self, archive_path: Path) -> bool:
        """
        Validate that file is a valid archive of this type.
        
        Args:
            archive_path: Path to archive file
            
        Returns:
            True if valid archive, False otherwise
        """
        pass


class ZipHandler(ArchiveHandler):
    """Handler for ZIP archives."""
    
    async def extract(self, archive_path: Path, destination: Path) -> Dict[str, Any]:
        """Extract ZIP archive."""
        try:
            destination.mkdir(parents=True, exist_ok=True)
            
            extracted_files = []
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                zip_ref.extractall(destination)
                
                for file_name in file_list:
                    file_path = destination / file_name
                    if file_path.is_file():
                        extracted_files.append(file_path)
                
                self.logger.info(f"Extracted {len(extracted_files)} files from {archive_path.name}")
                
                return {
                    'success': True,
                    'files_extracted': len(extracted_files),
                    'files': extracted_files
                }
        
        except zipfile.BadZipFile as e:
            error_msg = f"Invalid ZIP file: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        except Exception as e:
            error_msg = f"ZIP extraction error: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def validate_archive(self, archive_path: Path) -> bool:
        """Validate ZIP archive."""
        try:
            return zipfile.is_zipfile(archive_path)
        except Exception:
            return False


class TarHandler(ArchiveHandler):
    """Handler for TAR archives (including .tar.gz, .tar.bz2)."""
    
    async def extract(self, archive_path: Path, destination: Path) -> Dict[str, Any]:
        """Extract TAR archive."""
        try:
            destination.mkdir(parents=True, exist_ok=True)
            
            extracted_files = []
            
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                members = tar_ref.getmembers()
                tar_ref.extractall(destination, filter='data')
                
                for member in members:
                    if member.isfile():
                        file_path = destination / member.name
                        if file_path.is_file():
                            extracted_files.append(file_path)
                
                self.logger.info(f"Extracted {len(extracted_files)} files from {archive_path.name}")
                
                return {
                    'success': True,
                    'files_extracted': len(extracted_files),
                    'files': extracted_files
                }
        
        except tarfile.TarError as e:
            error_msg = f"Invalid TAR file: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        except Exception as e:
            error_msg = f"TAR extraction error: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def validate_archive(self, archive_path: Path) -> bool:
        """Validate TAR archive."""
        try:
            return tarfile.is_tarfile(archive_path)
        except Exception:
            return False


class GzipHandler(ArchiveHandler):
    """Handler for GZIP compressed files (.gz)."""
    
    async def extract(self, archive_path: Path, destination: Path) -> Dict[str, Any]:
        """Extract GZIP file."""
        try:
            destination.mkdir(parents=True, exist_ok=True)
            
            output_name = archive_path.stem
            output_path = destination / output_name
            
            with gzip.open(archive_path, 'rb') as gz_ref:
                with open(output_path, 'wb') as out_file:
                    shutil.copyfileobj(gz_ref, out_file)
            
            self.logger.info(f"Extracted {output_path.name} from {archive_path.name}")
            
            return {
                'success': True,
                'files_extracted': 1,
                'files': [output_path]
            }
        
        except (gzip.BadGzipFile, OSError) as e:
            error_msg = f"Invalid GZIP file: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        except Exception as e:
            error_msg = f"GZIP extraction error: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def validate_archive(self, archive_path: Path) -> bool:
        """Validate GZIP file."""
        try:
            with gzip.open(archive_path, 'rb') as gz_ref:
                gz_ref.read(GZIP_READ_TEST_BYTES)
            return True
        except Exception:
            return False


class ArchiveHandlerFactory:
    """
    Factory for creating appropriate archive handlers.
    
    Responsibilities:
    - Map archive formats to handlers
    - Provide handler instances
    - Report supported formats
    """
    
    def __init__(self):
        self.handlers = {
            'zip': ZipHandler(),
            'tar': TarHandler(),
            'tar.gz': TarHandler(),
            'tgz': TarHandler(),
            'tar.bz2': TarHandler(),
            'tbz2': TarHandler(),
            'gz': GzipHandler()
        }
        self.logger = get_logger(__name__, 'engine')
    
    def get_handler(self, format_type: str) -> ArchiveHandler:
        """
        Get handler for archive format.
        
        Args:
            format_type: Archive format (e.g., 'zip', 'tar', 'gz')
            
        Returns:
            ArchiveHandler instance
            
        Raises:
            ValueError: If format not supported
        """
        format_lower = format_type.lower()
        
        if format_lower not in self.handlers:
            raise ValueError(f"Unsupported archive format: {format_type}")
        
        return self.handlers[format_lower]
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported archive formats.
        
        Returns:
            List of format strings
        """
        return list(self.handlers.keys())
    
    def is_format_supported(self, format_type: str) -> bool:
        """
        Check if format is supported.
        
        Args:
            format_type: Archive format to check
            
        Returns:
            True if supported, False otherwise
        """
        return format_type.lower() in self.handlers