# Path: library/engine/manual_processor.py
"""
Manual Processor

Handles manually downloaded taxonomy files.
Three-directory pattern for safe processing.

Directories:
- manual_downloads/  - User places ZIP files here
- libraries/         - Extracted taxonomies
- manual_processed/  - Timestamped archives (never lost)

Architecture:
1. User downloads taxonomy ZIP manually
2. Places in manual_downloads/
3. System processes and extracts
4. Registers in database
5. Moves original to manual_processed/ with timestamp

100% AGNOSTIC - no hardcoded taxonomy logic.

Usage:
    from library.engine.manual_processor import ManualProcessor
    
    processor = ManualProcessor()
    
    # Process file
    result = processor.process_manual_file(
        'us-gaap-2024.zip',
        taxonomy_name='us-gaap',
        version='2024'
    )
"""

import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from library.core.config_loader import LibraryConfig
from library.core.data_paths import LibraryPaths
from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class ManualProcessor:
    """
    Process manually downloaded taxonomy files.
    
    Three-directory pattern:
    - manual_downloads/: User drops files
    - libraries/: Extracted taxonomies
    - manual_processed/: Timestamped archives
    
    Example:
        processor = ManualProcessor()
        
        # Scan for new files
        files = processor.scan_manual_directory()
        
        # Process file
        result = processor.process_manual_file(
            'us-gaap-2024.zip',
            'us-gaap',
            '2024'
        )
    """
    
    def __init__(
        self,
        config: Optional[LibraryConfig] = None,
        paths: Optional[LibraryPaths] = None
    ):
        """
        Initialize manual processor.
        
        Args:
            config: Optional LibraryConfig instance
            paths: Optional LibraryPaths instance
        """
        self.config = config if config else LibraryConfig()
        self.paths = paths if paths else LibraryPaths(self.config)
        
        logger.debug(f"{LOG_PROCESS} Manual processor initialized")
    
    def scan_manual_directory(self) -> List[Dict[str, Any]]:
        """
        Scan manual downloads directory for files.
        
        Returns:
            List of file information dictionaries
        """
        logger.info(f"{LOG_INPUT} Scanning manual downloads directory")
        
        if not self.paths.manual_downloads.exists():
            logger.warning("Manual downloads directory does not exist")
            return []
        
        files = []
        for file_path in self.paths.manual_downloads.iterdir():
            if file_path.is_file():
                files.append({
                    'filename': file_path.name,
                    'path': file_path,
                    'size_mb': file_path.stat().st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                })
        
        logger.info(f"{LOG_OUTPUT} Found {len(files)} files in manual downloads")
        
        return files
    
    def process_manual_file(
        self,
        filename: str,
        taxonomy_name: str,
        version: str,
        namespace: Optional[str] = None,
        authority: Optional[str] = None,
        market_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process manually downloaded taxonomy file.
        
        Steps:
        1. Extract ZIP to libraries directory
        2. Count files
        3. Move original to processed directory (timestamped)
        
        Args:
            filename: File in manual_downloads directory
            taxonomy_name: Taxonomy name (e.g., 'us-gaap')
            version: Taxonomy version (e.g., '2024')
            namespace: Optional namespace URI
            authority: Optional authority (e.g., 'FASB')
            market_types: Optional list of markets (e.g., ['sec'])
            
        Returns:
            Dictionary with processing result
        """
        logger.info(f"{LOG_INPUT} Processing manual file: {filename}")
        
        source_path = self.paths.get_manual_file_path(filename)
        
        if not source_path.exists():
            return {
                'success': False,
                'error': f'File not found: {filename}',
            }
        
        try:
            # Step 1: Extract to libraries directory
            target_dir = self.paths.get_library_directory(taxonomy_name, version)
            
            logger.debug(f"{LOG_PROCESS} Extracting to {target_dir}")
            
            extract_result = self._extract_archive(source_path, target_dir)
            
            if not extract_result['success']:
                return extract_result
            
            # Step 2: Move original to processed (timestamped)
            processed_path = self.paths.get_processed_file_path(filename)
            
            logger.debug(f"{LOG_PROCESS} Archiving original to {processed_path}")
            
            shutil.move(str(source_path), str(processed_path))
            
            logger.info(f"{LOG_OUTPUT} Successfully processed {filename}")
            
            return {
                'success': True,
                'extract_path': str(target_dir),
                'file_count': extract_result['file_count'],
                'processed_file_moved_to': str(processed_path),
            }
            
        except Exception as e:
            logger.error(f"Error processing manual file {filename}: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def register_manual_library(
        self,
        taxonomy_name: str,
        version: str,
        namespace: str,
        download_url: str,
        authority: str,
        market_types: List[str]
    ) -> Dict[str, Any]:
        """
        Register manually processed library in database.
        
        Delegates to DatabaseConnector → searcher.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            namespace: Namespace URI
            download_url: Download URL (can be manual source)
            authority: Authority
            market_types: List of markets
            
        Returns:
            Dictionary with registration result
        """
        logger.info(
            f"{LOG_INPUT} Registering manual library: "
            f"{taxonomy_name} v{version}"
        )
        
        try:
            from library.engine.db_connector import DatabaseConnector
            
            db = DatabaseConnector(self.config)
            
            metadata = {
                'taxonomy_name': taxonomy_name,
                'version': version,
                'namespace': namespace,
                'download_url': download_url,
                'market_type': ','.join(market_types) if market_types else 'unknown',
                'authority': authority,
            }
            
            result = db.save_taxonomy(metadata)
            
            if result['success']:
                logger.info(f"{LOG_OUTPUT} Registered {taxonomy_name} v{version}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error registering manual library: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _extract_archive(
        self,
        archive_path: Path,
        target_dir: Path
    ) -> Dict[str, Any]:
        """
        Extract ZIP archive to target directory.
        
        Args:
            archive_path: Path to ZIP file
            target_dir: Target extraction directory
            
        Returns:
            Dictionary with extraction result
        """
        try:
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            # Count extracted files
            file_count = sum(1 for _ in target_dir.rglob('*') if _.is_file())
            
            logger.debug(f"{LOG_OUTPUT} Extracted {file_count} files")
            
            return {
                'success': True,
                'file_count': file_count,
            }
            
        except zipfile.BadZipFile:
            return {
                'success': False,
                'error': 'Invalid ZIP file',
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def get_manual_instructions(self) -> str:
        """
        Get formatted manual download instructions.
        
        Returns:
            Formatted instructions string
        """
        return f"""
MANUAL TAXONOMY DOWNLOAD INSTRUCTIONS
{'=' * 80}

If automatic download fails, you can manually download taxonomies:

1. Download the taxonomy ZIP file from the official source
   
2. Place it in the manual downloads directory:
   {self.paths.manual_downloads}

3. Run the library module to process it:
   python library.py --process-manual <filename> \\
       --name <taxonomy_name> \\
       --version <version>

4. The system will:
   - Extract the taxonomy to {self.paths.taxonomies_libraries}
   - Validate contents
   - Register in database
   - Move original to {self.paths.manual_processed}

Example:
   python library.py --process-manual us-gaap-2024.zip \\
       --name us-gaap \\
       --version 2024

Common taxonomy sources:
  • SEC:  https://xbrl.sec.gov/
  • FASB: https://xbrl.fasb.org/
  • IFRS: https://www.ifrs.org/
  • ESMA: https://www.esma.europa.eu/

{'=' * 80}
"""


__all__ = ['ManualProcessor']