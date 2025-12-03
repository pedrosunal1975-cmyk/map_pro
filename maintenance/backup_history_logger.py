"""
Backup History Logger
=====================

Manages backup history logging and tracking.

Save location: tools/maintenance/backup_history_logger.py

Responsibilities:
- Log backup operation results to file
- Maintain backup history
- Rotate history logs
- Provide backup history queries

Dependencies:
- pathlib (path handling)
- json (history file format)
- core.system_logger (logging)
- tools.maintenance.backup_config (configuration)
"""

import json
from pathlib import Path
from typing import Dict, Any, List

from core.system_logger import get_logger
from tools.maintenance.backup_config import BackupConfig, MAX_BACKUP_HISTORY_ENTRIES


logger = get_logger(__name__, 'maintenance')


class BackupHistoryLogger:
    """
    Manages backup history logging.
    
    Maintains a persistent log of backup operations for audit and
    troubleshooting purposes.
    
    Attributes:
        config: Backup configuration instance
        logger: Logger instance for this manager
        history_file: Path to backup history log file
    """
    
    def __init__(self, config: BackupConfig):
        """
        Initialize history logger.
        
        Args:
            config: Backup configuration instance
        """
        self.config = config
        self.logger = logger
        self.history_file = self._get_history_file_path()
    
    def _get_history_file_path(self) -> Path:
        """
        Get path to backup history log file.
        
        Returns:
            Path to backup_history.json file
        """
        return self.config.get_log_dir() / 'backup_history.json'
    
    def log_backup_result(self, backup_result: Dict[str, Any]) -> None:
        """
        Log backup operation result to history file.
        
        Appends the backup result to the history log, maintaining a
        maximum number of entries as configured.
        
        Args:
            backup_result: Dictionary containing backup operation results
        """
        try:
            self._ensure_log_directory()
            history = self._load_history()
            history.append(backup_result)
            history = self._rotate_history(history)
            self._save_history(history)
            
        except Exception as e:
            self.logger.error(f"Failed to log backup summary: {e}", exc_info=True)
    
    def _ensure_log_directory(self) -> None:
        """Ensure backup log directory exists."""
        log_dir = self.config.get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """
        Load backup history from file.
        
        Returns:
            List of historical backup results
        """
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Could not load backup history: {e}")
            return []
    
    def _rotate_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rotate history to maintain maximum entry count.
        
        Args:
            history: Current history list
            
        Returns:
            Rotated history list with maximum entries
        """
        if len(history) > MAX_BACKUP_HISTORY_ENTRIES:
            return history[-MAX_BACKUP_HISTORY_ENTRIES:]
        return history
    
    def _save_history(self, history: List[Dict[str, Any]]) -> None:
        """
        Save backup history to file.
        
        Args:
            history: History list to save
        """
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    
    def get_recent_backups(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent backup entries.
        
        Args:
            count: Number of recent entries to retrieve
            
        Returns:
            List of recent backup results
        """
        history = self._load_history()
        return history[-count:] if history else []
    
    def get_failed_backups(self) -> List[Dict[str, Any]]:
        """
        Get all failed backup entries.
        
        Returns:
            List of failed backup results
        """
        history = self._load_history()
        return [entry for entry in history if not entry.get('success', False)]


__all__ = ['BackupHistoryLogger']