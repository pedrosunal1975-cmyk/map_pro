"""
Variance Calculator
===================

Location: map_pro/engines/mapper/analysis/variance_calculator.py

Calculates variance between duplicate values and classifies severity.
"""

from typing import List, Tuple, Any
from decimal import Decimal, InvalidOperation
from .duplicate_constants import (
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    SEVERITY_REDUNDANT,
    CRITICAL_VARIANCE_THRESHOLD,
    MAJOR_VARIANCE_THRESHOLD
)


def calculate_variance(values: List[Any]) -> Tuple[float, float]:
    """
    Calculate variance between values.
    
    Args:
        values: List of values (numeric or non-numeric)
        
    Returns:
        Tuple of (variance_percentage, max_variance_amount)
    """
    # Try to convert to numeric
    numeric_values = []
    for val in values:
        try:
            if val is None or val == '':
                continue
            numeric_val = Decimal(str(val))
            numeric_values.append(numeric_val)
        except (InvalidOperation, ValueError, TypeError):
            continue
    
    if len(numeric_values) < 2:
        return 0.0, 0.0
    
    # Calculate variance
    min_val = min(numeric_values)
    max_val = max(numeric_values)
    variance_amount = abs(max_val - min_val)
    
    # Avoid division by zero
    if min_val == 0 and max_val == 0:
        return 0.0, 0.0
    
    # Calculate percentage variance
    base = max(abs(min_val), abs(max_val))
    if base == 0:
        return 0.0, float(variance_amount)
    
    variance_pct = float(variance_amount / base)
    
    return variance_pct, float(variance_amount)


def classify_severity(
    variance_pct: float,
    unique_values: List[Any]
) -> str:
    """
    Classify duplicate severity based on variance.
    
    Args:
        variance_pct: Variance percentage (0.0 to 1.0+)
        unique_values: List of unique values
        
    Returns:
        Severity level: CRITICAL, MAJOR, MINOR, or REDUNDANT
    """
    # All values identical -> REDUNDANT
    if len(unique_values) == 1:
        return SEVERITY_REDUNDANT
    
    # Non-numeric or zero variance -> MINOR
    if variance_pct == 0.0:
        return SEVERITY_MINOR
    
    # Classify by variance threshold
    if variance_pct >= CRITICAL_VARIANCE_THRESHOLD:
        return SEVERITY_CRITICAL
    elif variance_pct >= MAJOR_VARIANCE_THRESHOLD:
        return SEVERITY_MAJOR
    else:
        return SEVERITY_MINOR


__all__ = [
    'calculate_variance',
    'classify_severity'
]