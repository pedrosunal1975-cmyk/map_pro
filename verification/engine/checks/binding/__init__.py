# Path: verification/engine/checks/binding/__init__.py
"""
Calculation binding rules for XBRL verification.

Contains:
- binding_checker: Determines if calculations should bind per XBRL spec
- role_scoping: XBRL Calculations 1.1 role scoping
"""

from .binding_checker import BindingChecker, BindingResult, BindingStatus
from .role_scoping import (
    RoleInfo,
    RoleScopedArc,
    CalculationKey,
    RoleScopedCalculations,
    group_arcs_by_role_and_parent,
    extract_role_name,
    is_same_role,
)

__all__ = [
    # Binding checker
    'BindingChecker',
    'BindingResult',
    'BindingStatus',
    # Role scoping
    'RoleInfo',
    'RoleScopedArc',
    'CalculationKey',
    'RoleScopedCalculations',
    'group_arcs_by_role_and_parent',
    'extract_role_name',
    'is_same_role',
]
