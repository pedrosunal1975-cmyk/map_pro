# File: /map_pro/tools/maintenance/cleanup_history_logger.py

"""
Cleanup History Logger
======================

Manages cleanup history logging to dedicated log file.
Maintains rolling history of cleanup operations.

SINGLE RESPONSIBILITY: Log cleanup history to file.
"""

import json
from typing import Dict, Any, List

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

from .cleanup_scheduler_constants import MAX_HISTORY_ENTRIES, HISTORY_LOG_FILENAME

logger = get_logger(__name__, 'maintenance')


class CleanupHistoryLogger:
    """
    Logs cleanup history to dedicated file.
    
    SINGLE RESPONSIBILITY: Manage cleanup history logging.
    
    Responsibilities:
    - Write cleanup results to history file
    - Maintain rolling history limit
    - Handle file I/O errors gracefully
    
    Does NOT:
    - Execute cleanup (cleanup_executor does this)
    - Generate recommendations (recommendation_engine does this)
    - Gather statistics (cleanup_statistics does this)
    """
    
    def __init__(self):
        """Initialize cleanup history logger."""
        self.logger = logger
        self.history_file = map_pro_paths.logs_system / HISTORY_LOG_FILENAME
    
    def log_cleanup(self, results: Dict[str, Any]) -> None:
        """
        Log cleanup results to history file.
        
        Maintains a rolling history of the last N cleanup operations.
        
        Args:
            results: Cleanup results dictionary
        """
        try:
            history = self._read_history()
            history = self._append_result(history, results)
            history = self._trim_history(history)
            self._write_history(history)
            
        except Exception as exception:
            self.logger.error(
                f"Failed to log cleanup summary: {exception}",
                exc_info=True
            )
    
    def _read_history(self) -> List[Dict[str, Any]]:
        """
        Read existing cleanup history from file.
        
        Returns:
            List of historical cleanup results
        """
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r') as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError) as exception:
            self.logger.warning(
                f"Could not read cleanup history, starting fresh: {exception}"
            )
            return []
    
    def _append_result(
        self,
        history: List[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Append new result to history.
        
        Args:
            history: Existing history list
            result: New cleanup result
            
        Returns:
            Updated history list
        """
        history.append(result)
        return history
    
    def _trim_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Trim history to maximum entries.
        
        Args:
            history: Full history list
            
        Returns:
            Trimmed history list
        """
        return history[-MAX_HISTORY_ENTRIES:]
    
    def _write_history(self, history: List[Dict[str, Any]]) -> None:
        """
        Write history to file.
        
        Args:
            history: History list to write
        """
        with open(self.history_file, 'w') as file:
            json.dump(history, file, indent=2)


__all__ = ['CleanupHistoryLogger']