"""
Fact Grouper
============

Location: map_pro/engines/mapper/analysis/fact_grouper.py

Groups facts by (concept, context) pairs to identify duplicates.
"""

from typing import Dict, List, Tuple
from collections import defaultdict
from .fact_extractor import extract_concept, extract_context


def group_facts_by_concept_and_context(
    facts: List[dict]
) -> Dict[Tuple[str, str], List[dict]]:
    """
    Group facts by (concept, context) key.
    
    Args:
        facts: List of fact dictionaries
        
    Returns:
        Dictionary mapping (concept, context) to list of facts
    """
    groups = defaultdict(list)
    
    for fact in facts:
        concept = extract_concept(fact)
        context = extract_context(fact)
        
        if concept and context:
            key = (concept, context)
            groups[key].append(fact)
    
    return dict(groups)


def find_duplicate_groups(
    facts: List[dict]
) -> Dict[Tuple[str, str], List[dict]]:
    """
    Find groups with 2+ facts (duplicates).
    
    Args:
        facts: List of fact dictionaries
        
    Returns:
        Dictionary of duplicate groups only
    """
    all_groups = group_facts_by_concept_and_context(facts)
    
    # Keep only groups with 2+ facts
    duplicate_groups = {
        key: facts_list
        for key, facts_list in all_groups.items()
        if len(facts_list) > 1
    }
    
    return duplicate_groups


def count_facts_in_groups(
    groups: Dict[Tuple[str, str], List[dict]]
) -> int:
    """
    Count total facts across all groups.
    
    Args:
        groups: Dictionary of fact groups
        
    Returns:
        Total fact count
    """
    return sum(len(facts) for facts in groups.values())


__all__ = [
    'group_facts_by_concept_and_context',
    'find_duplicate_groups',
    'count_facts_in_groups'
]