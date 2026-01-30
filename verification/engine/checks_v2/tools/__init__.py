# Path: verification/engine/checks_v2/tools/__init__.py
"""
Verification Tools Module

Specialized, reusable skill modules for XBRL verification.

Each tool provides focused functionality that can be used across all
processing stages. Tools are stateless and adaptable - processors
can pick up and drop them as needed.

Categories:
- naming: Concept name normalization and extraction
- period: Period extraction and comparison
- sign: Sign correction parsing and lookup
- hierarchy: Parent/child relationship handling
- context: Context classification and matching
- fact: Fact finding and parsing
- dimension: Dimensional structure handling
- calculation: Calculation weights and sum verification
- tolerance: Decimal tolerance and value comparison
"""

# Import all tools for easy access
from .naming import (
    Normalizer,
    LocalNameExtractor,
    normalize_name,
    extract_local_name,
)

from .period import (
    PeriodExtractor,
    PeriodComparator,
    PeriodInfo,
)

from .sign import (
    SignParser,
    SignLookup,
    SignInfo,
    SemanticSignInferrer,
)

from .context import (
    ContextClassifier,
    ContextGrouper,
    ContextGroup,
)

from .fact import (
    FactFinder,
    FactMatch,
    ValueParser,
    DuplicateHandler,
    DuplicateInfo,
    FactEntry,
)

from .dimension import (
    DimensionParser,
    DimensionInfo,
)

from .hierarchy import (
    TreeBuilder,
    ChildFinder,
    BindingChecker,
    BindingResult,
)

from .calculation import (
    WeightHandler,
    SumCalculator,
    CalculationResult,
)

from .tolerance import (
    DecimalTolerance,
    ToleranceResult,
    ToleranceChecker,
)


__all__ = [
    # Naming
    'Normalizer',
    'LocalNameExtractor',
    'normalize_name',
    'extract_local_name',
    # Period
    'PeriodExtractor',
    'PeriodComparator',
    'PeriodInfo',
    # Sign
    'SignParser',
    'SignLookup',
    'SignInfo',
    'SemanticSignInferrer',
    # Context
    'ContextClassifier',
    'ContextGrouper',
    'ContextGroup',
    # Fact
    'FactFinder',
    'FactMatch',
    'ValueParser',
    'DuplicateHandler',
    'DuplicateInfo',
    'FactEntry',
    # Dimension
    'DimensionParser',
    'DimensionInfo',
    # Hierarchy
    'TreeBuilder',
    'ChildFinder',
    'BindingChecker',
    'BindingResult',
    # Calculation
    'WeightHandler',
    'SumCalculator',
    'CalculationResult',
    # Tolerance
    'DecimalTolerance',
    'ToleranceResult',
    'ToleranceChecker',
]
