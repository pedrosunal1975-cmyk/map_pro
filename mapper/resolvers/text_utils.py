"""
File: engines/mapper/resolvers/text_utils.py
Path: engines/mapper/resolvers/text_utils.py

Text Utilities
==============

Text processing utilities for concept name manipulation.
Includes functions for:
    - Generating labels from concept names
    - Extracting words from various naming conventions
    - Normalizing text for matching
"""

import re
from typing import List


def generate_label_from_name(concept_name: str) -> str:
    """
    Generate human-readable label from concept name.
    
    Converts CamelCase/snake_case/kebab-case to space-separated words.
    
    Args:
        concept_name: Concept identifier
        
    Returns:
        Human-readable label
        
    Examples:
        >>> generate_label_from_name("AccountsReceivable")
        "Accounts Receivable"
        >>> generate_label_from_name("total_revenue")
        "Total Revenue"
    """
    # Add space before capital letters following lowercase
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', concept_name)
    
    # Add space before capital letters followed by lowercase
    spaced = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', spaced)
    
    # Replace separators with spaces
    spaced = spaced.replace('_', ' ').replace('-', ' ')
    
    # Normalize whitespace
    spaced = re.sub(r'\s+', ' ', spaced)
    
    return spaced.strip()


def extract_words(text: str) -> List[str]:
    """
    Extract individual words from concept identifier.
    
    Handles CamelCase, snake_case, kebab-case, and namespace prefixes.
    Uses simple, reliable CamelCase splitting that preserves all words.
    
    Args:
        text: Concept identifier
        
    Returns:
        List of lowercase words
        
    Examples:
        >>> extract_words("us-gaap:AccountsReceivable")
        ["accounts", "receivable"]
        >>> extract_words("TotalRevenue")
        ["total", "revenue"]
        >>> extract_words("net_income")
        ["net", "income"]
    """
    # Strip namespace prefix if present
    if ':' in text:
        text = text.split(':', 1)[1]
    
    # Insert spaces before capital letters (handles CamelCase)
    text = re.sub(r'([A-Z])', r' \1', text)
    
    # Replace specific separators with spaces
    text = text.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    
    # Split into words, filter empty, convert to lowercase
    words = [word.lower() for word in text.split() if word.strip()]
    
    return words


__all__ = ['generate_label_from_name', 'extract_words']