# File: engines/parser/context_statistics.py

"""
Context Statistics Manager
==========================

Manages statistics tracking for context and unit processing.
Provides statistics collection, updates, and reporting.

Architecture: Single Responsibility - Focuses only on statistics management.
"""

from typing import Dict, Any

from engines.parser.context_constants import (
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_DURATION,
    STAT_CONTEXTS_EXTRACTED,
    STAT_INSTANT_CONTEXTS,
    STAT_DURATION_CONTEXTS,
    STAT_CONTEXTS_WITH_DIMENSIONS,
    STAT_UNITS_EXTRACTED,
    INITIAL_STATISTICS
)


class ContextStatistics:
    """
    Tracks statistics for context and unit processing.
    
    Responsibilities:
    - Track context extraction counts
    - Track period type distribution
    - Track dimensional context counts
    - Track unit extraction counts
    - Provide statistics reporting
    
    Does NOT handle:
    - Context extraction (context_extractor handles this)
    - Context processing (context_processor handles this)
    """
    
    def __init__(self):
        """Initialize context statistics with zero counts."""
        self.stats = INITIAL_STATISTICS.copy()
    
    def update_context_statistics(self, context_dict: Dict[str, Any]) -> None:
        """
        Update statistics based on extracted context.
        
        Args:
            context_dict: Extracted context dictionary
        """
        self.stats[STAT_CONTEXTS_EXTRACTED] += 1
        
        period_type = context_dict.get('period_type')
        if period_type == PERIOD_TYPE_INSTANT:
            self.stats[STAT_INSTANT_CONTEXTS] += 1
        elif period_type == PERIOD_TYPE_DURATION:
            self.stats[STAT_DURATION_CONTEXTS] += 1
        
        if context_dict.get('dimensions'):
            self.stats[STAT_CONTEXTS_WITH_DIMENSIONS] += 1
    
    def increment_units_extracted(self) -> None:
        """Increment the count of successfully extracted units."""
        self.stats[STAT_UNITS_EXTRACTED] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get copy of current statistics.
        
        Returns:
            Dictionary containing all statistics
        """
        return self.stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset all statistics to initial values."""
        self.stats = INITIAL_STATISTICS.copy()
    
    def get_context_count(self) -> int:
        """
        Get total number of contexts extracted.
        
        Returns:
            Count of extracted contexts
        """
        return self.stats[STAT_CONTEXTS_EXTRACTED]
    
    def get_unit_count(self) -> int:
        """
        Get total number of units extracted.
        
        Returns:
            Count of extracted units
        """
        return self.stats[STAT_UNITS_EXTRACTED]
    
    def get_instant_context_count(self) -> int:
        """
        Get number of instant-type contexts.
        
        Returns:
            Count of instant contexts
        """
        return self.stats[STAT_INSTANT_CONTEXTS]
    
    def get_duration_context_count(self) -> int:
        """
        Get number of duration-type contexts.
        
        Returns:
            Count of duration contexts
        """
        return self.stats[STAT_DURATION_CONTEXTS]
    
    def get_dimensional_context_count(self) -> int:
        """
        Get number of contexts with dimensions.
        
        Returns:
            Count of contexts with dimensional information
        """
        return self.stats[STAT_CONTEXTS_WITH_DIMENSIONS]


__all__ = [
    'ContextStatistics'
]