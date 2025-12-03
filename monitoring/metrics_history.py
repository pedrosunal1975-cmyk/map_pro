"""
Map Pro Metrics History Manager
================================

Manages in-memory history of metrics snapshots.

Save location: tools/monitoring/metrics_history.py
"""

from typing import Dict, Any, List, Optional

from core.system_logger import get_logger

logger = get_logger(__name__, 'monitoring')


class MetricsHistory:
    """
    Manages metrics history buffer.
    
    Responsibilities:
    - Store metrics snapshots in memory
    - Maintain maximum history size
    - Provide access to historical data
    """
    
    def __init__(self, max_size: int) -> None:
        """
        Initialize metrics history.
        
        Args:
            max_size: Maximum number of metrics snapshots to retain
        """
        self.max_size = max_size
        self.history: List[Dict[str, Any]] = []
    
    def add(self, metrics: Dict[str, Any]) -> None:
        """
        Add metrics snapshot to history.
        
        Args:
            metrics: Metrics snapshot to add
        """
        self.history.append(metrics)
        
        # Maintain size limit
        if len(self.history) > self.max_size:
            self.history.pop(0)
    
    def get(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get historical metrics.
        
        Args:
            limit: Optional limit on number of records to return
            
        Returns:
            List of historical metrics snapshots
        """
        if limit:
            return self.history[-limit:]
        return self.history.copy()
    
    def get_latest(self) -> Dict[str, Any]:
        """
        Get the most recent metrics snapshot.
        
        Returns:
            Latest metrics snapshot, or empty dict if none exist
        """
        if self.history:
            return self.history[-1]
        return {}
    
    def clear(self) -> None:
        """Clear all metrics history."""
        self.history.clear()
    
    def size(self) -> int:
        """
        Get current history size.
        
        Returns:
            Number of metrics snapshots in history
        """
        return len(self.history)