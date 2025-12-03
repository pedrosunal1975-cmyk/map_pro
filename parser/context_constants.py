# File: engines/parser/context_constants.py

"""
Context Processing Constants
============================

Constants used in context and unit processing.
Centralizes magic numbers and type definitions.

Architecture: Configuration module - reduces magic numbers in codebase.
"""

# Measure count thresholds
SINGLE_MEASURE_COUNT = 1
DIVIDE_MEASURE_COUNT = 2

# Period type constants
PERIOD_TYPE_INSTANT = 'instant'
PERIOD_TYPE_DURATION = 'duration'
PERIOD_TYPE_FOREVER = 'forever'

# Unit type constants
UNIT_TYPE_MEASURE = 'measure'
UNIT_TYPE_DIVIDE = 'divide'
UNIT_TYPE_COMPLEX = 'complex'

# Statistics keys
STAT_CONTEXTS_EXTRACTED = 'contexts_extracted'
STAT_INSTANT_CONTEXTS = 'instant_contexts'
STAT_DURATION_CONTEXTS = 'duration_contexts'
STAT_CONTEXTS_WITH_DIMENSIONS = 'contexts_with_dimensions'
STAT_UNITS_EXTRACTED = 'units_extracted'

# Initial statistics template
INITIAL_STATISTICS = {
    STAT_CONTEXTS_EXTRACTED: 0,
    STAT_INSTANT_CONTEXTS: 0,
    STAT_DURATION_CONTEXTS: 0,
    STAT_CONTEXTS_WITH_DIMENSIONS: 0,
    STAT_UNITS_EXTRACTED: 0
}


__all__ = [
    'SINGLE_MEASURE_COUNT',
    'DIVIDE_MEASURE_COUNT',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_FOREVER',
    'UNIT_TYPE_MEASURE',
    'UNIT_TYPE_DIVIDE',
    'UNIT_TYPE_COMPLEX',
    'STAT_CONTEXTS_EXTRACTED',
    'STAT_INSTANT_CONTEXTS',
    'STAT_DURATION_CONTEXTS',
    'STAT_CONTEXTS_WITH_DIMENSIONS',
    'STAT_UNITS_EXTRACTED',
    'INITIAL_STATISTICS'
]