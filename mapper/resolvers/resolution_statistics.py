"""
File: engines/mapper/resolvers/resolution_statistics.py
Path: engines/mapper/resolvers/resolution_statistics.py

Resolution Statistics
=====================

Tracks resolution statistics across the 8-strategy chain.
Provides methods to increment counters and retrieve statistics.
"""

from typing import Dict, Any


class ResolutionStatistics:
    """
    Tracks resolution statistics for concept matching.
    
    Maintains counters for:
    - Total facts resolved
    - Successful matches by strategy
    - Unmapped facts
    """
    
    # ============================================================================
    # MODIFIED __init__ METHOD
    # ============================================================================

    def __init__(self):
        """Initialize statistics counters."""
        self.stats = {
            'total_resolved': 0,
            'exact_matches': 0,
            'prefix_detected': 0,
            'taxonomy_synonym': 0,           # NEW: Synonym resolution counter
            'taxonomy_synonym_prefixed': 0,  # NEW: Synonym with prefix counter
            'technology_transformed': 0,
            'financial_mapped': 0,
            'company_extension': 0,
            'fuzzy_matched': 0,
            'word_decomposed': 0,
            'similarity_matched': 0,
            'unmapped': 0
        }
    
    def reset(self) -> None:
        """
        Reset all statistics counters.
        
        Should be called at the start of each new resolution run
        to prevent accumulation errors.
        """
        for key in self.stats:
            self.stats[key] = 0
    
    def increment_total_resolved(self) -> None:
        """Increment total facts resolved counter."""
        self.stats['total_resolved'] += 1
    
    def increment_unmapped(self) -> None:
        """Increment unmapped facts counter."""
        self.stats['unmapped'] += 1
    
    # ============================================================================
    # MODIFIED increment_strategy METHOD
    # ============================================================================

    def increment_strategy(self, strategy_name: str) -> None:
        """
        Increment counter for specific matching strategy.
        
        Maps strategy method names to statistics keys.
        
        Args:
            strategy_name: Name of matching strategy
        """
        strategy_map = {
            'exact_match_case_insensitive': 'exact_matches',
            'prefix_detected': 'prefix_detected',
            'taxonomy_synonym': 'taxonomy_synonym',                    # NEW
            'taxonomy_synonym_prefixed': 'taxonomy_synonym',           # NEW - Map to same counter
            'technology_transformed': 'technology_transformed',
            'financial_mapped': 'financial_mapped',
            'company_extension': 'company_extension',
            'base_name_match': 'fuzzy_matched',
            'word_decomposition': 'word_decomposed',
            'semantic_similarity': 'similarity_matched'
        }
        
        stats_key = strategy_map.get(strategy_name)
        if stats_key:
            self.stats[stats_key] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get copy of current statistics.
        
        Returns:
            Dictionary containing all statistics counters
        """
        return self.stats.copy()


__all__ = ['ResolutionStatistics']