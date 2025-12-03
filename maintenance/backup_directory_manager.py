"""
Backup Directory Manager
=========================

Manages backup directory structure and initialization.

Save location: tools/maintenance/backup_directory_manager.py

Responsibilities:
- Create and maintain backup directory structure
- Validate directory permissions
- Handle directory creation errors

Dependencies:
- pathlib (path handling)
- core.system_logger (logging)
- tools.maintenance.backup_config (configuration)
"""

from pathlib import Path
from typing import List, Tuple

from core.system_logger import get_logger
from tools.maintenance.backup_config import BackupConfig


logger = get_logger(__name__, 'maintenance')


class BackupDirectoryManager:
    """
    Manages backup directory structure.
    
    Handles creation and validation of all directories required
    for backup operations.
    
    Attributes:
        config: Backup configuration instance
        logger: Logger instance for this manager
    """
    
    def __init__(self, config: BackupConfig):
        """
        Initialize directory manager.
        
        Args:
            config: Backup configuration instance
        """
        self.config = config
        self.logger = logger
    
    def ensure_backup_directories(self) -> Tuple[bool, List[str]]:
        """
        Create all necessary backup directories.
        
        Creates the root backup directory and all subdirectories
        required for backup operations. Handles permission errors
        gracefully.
        
        Returns:
            Tuple of (success flag, list of error messages)
        """
        directories = self.config.get_backup_directories()
        errors = []
        
        for directory in directories:
            success, error = self._create_directory(directory)
            if not success:
                errors.append(error)
        
        overall_success = len(errors) == 0
        
        if overall_success:
            self.logger.info("All backup directories created successfully")
        else:
            self.logger.warning(
                f"Some directories could not be created: {len(errors)} errors"
            )
        
        return overall_success, errors
    
    def _create_directory(self, directory: Path) -> Tuple[bool, str]:
        """
        Create a single directory.
        
        Args:
            directory: Path to directory to create
            
        Returns:
            Tuple of (success flag, error message if failed)
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Directory ensured: {directory}")
            return True, ""
            
        except PermissionError as e:
            error_msg = f"Permission denied for {directory}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
            
        except OSError as e:
            error_msg = f"OS error creating {directory}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def validate_directory_permissions(self, directory: Path) -> Tuple[bool, str]:
        """
        Validate that directory is writable.
        
        Args:
            directory: Path to directory to validate
            
        Returns:
            Tuple of (is_writable flag, error message if not writable)
        """
        if not directory.exists():
            return False, f"Directory does not exist: {directory}"
        
        if not directory.is_dir():
            return False, f"Path is not a directory: {directory}"
        
        test_file = directory / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
            return True, ""
            
        except (PermissionError, OSError) as e:
            error_msg = f"Directory not writable: {directory} - {e}"
            return False, error_msg


__all__ = ['BackupDirectoryManager']