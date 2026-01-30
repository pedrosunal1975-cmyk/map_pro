# Path: verification/engine/checks/c_equal/__init__.py
"""
C-Equal (Context-Equal) module for XBRL verification.

Provides the CEqual class for grouping facts by context_id and ensuring
calculations only compare facts that are c-equal per XBRL 2.1 specification.
"""

from .c_equal import (
    CEqual,
    FactGroups,
    ContextGroup,
    FactEntry,
    DuplicateInfo,
    DuplicateType,
)

__all__ = [
    'CEqual',
    'FactGroups',
    'ContextGroup',
    'FactEntry',
    'DuplicateInfo',
    'DuplicateType',
]
