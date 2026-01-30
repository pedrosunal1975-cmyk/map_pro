# Path: verification/engine/checks/checkers/__init__.py
"""
High-level verification checker implementations.

Contains:
- horizontal_checker: Within-statement checks
- vertical_checker: Cross-statement consistency checks
- library_checker: Standard taxonomy conformance checks
"""

from .horizontal_checker import HorizontalChecker
from .vertical_checker import VerticalChecker
from .library_checker import LibraryChecker

# Import CheckResult for convenience (commonly used with checkers)
from ..core import CheckResult

__all__ = [
    'HorizontalChecker',
    'VerticalChecker',
    'LibraryChecker',
    'CheckResult',
]
