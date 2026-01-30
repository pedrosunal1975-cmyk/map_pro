# Path: verification/engine/checks/role_scoping.py
"""
Role Scoping Module for XBRL Calculations 1.1 Compliance

Per XBRL Calculations 1.1 specification:
"A calculation is the set of all summation-item relationships sharing a common
total concept, a common extended link role, and a common arcrole."

This module enforces role scoping to ensure calculations are verified within
their declared extended link role. Without role scoping, the same concept
appearing in different roles (e.g., IncomeTaxExpenseBenefit in Income Statement
vs Tax Disclosure) would have their children mixed together, causing massive
calculation mismatches.

KEY RULES:
1. Calculations are scoped by extended link role (e.g., IncomeStatement, TaxDisclosure)
2. Parent-child relationships only valid within the same role
3. Same concept can have different children in different roles
4. Binding checks must be performed within role boundaries

USAGE:
    from .role_scoping import RoleScopedCalculations

    # Create role-scoped calculations from networks
    scoped = RoleScopedCalculations.from_networks(calc_networks)

    # Get calculations for a specific role
    role_calcs = scoped.get_calculations_for_role('IncomeStatement')

    # Iterate by (parent, role) key
    for (parent, role), arcs in scoped.iter_calculations():
        # All arcs here are from the same role
        pass
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Iterator

from ...loaders.xbrl_reader import CalculationNetwork, CalculationArc
from ...loaders.constants import normalize_name


@dataclass
class RoleInfo:
    """
    Information about an extended link role.

    Attributes:
        role_uri: Full role URI (e.g., http://www.company.com/role/IncomeStatement)
        role_name: Short name extracted from URI (e.g., IncomeStatement)
        definition: Human-readable role definition if available
    """
    role_uri: str
    role_name: str = ""
    definition: str = ""

    def __post_init__(self):
        if not self.role_name and self.role_uri:
            # Extract short name from URI
            self.role_name = self._extract_role_name(self.role_uri)

    @staticmethod
    def _extract_role_name(role_uri: str) -> str:
        """Extract short role name from full URI."""
        if not role_uri:
            return ""
        # Handle common URI patterns
        # http://www.company.com/role/IncomeStatement -> IncomeStatement
        # http://fasb.org/us-gaap/role/statement/StatementOfIncome -> StatementOfIncome
        parts = role_uri.rstrip('/').split('/')
        return parts[-1] if parts else ""


@dataclass
class RoleScopedArc:
    """
    A calculation arc with its role context preserved.

    This ensures we always know which role an arc belongs to,
    preventing cross-role mixing of calculations.

    Attributes:
        parent_concept: Parent (total) concept name
        child_concept: Child (contributing) concept name
        weight: Calculation weight (+1.0 or -1.0)
        order: Arc order for display
        role: Role this arc belongs to
        arcrole: The arcrole (should be summation-item for calculations)
    """
    parent_concept: str
    child_concept: str
    weight: float
    order: float
    role: str
    arcrole: str = ""

    @classmethod
    def from_arc(cls, arc: CalculationArc, role: str) -> 'RoleScopedArc':
        """Create from CalculationArc with role context."""
        return cls(
            parent_concept=arc.parent_concept,
            child_concept=arc.child_concept,
            weight=arc.weight,
            order=arc.order,
            role=role,
            arcrole=getattr(arc, 'arcrole', ''),
        )


@dataclass
class CalculationKey:
    """
    Unique key for a calculation within a role.

    A calculation is uniquely identified by:
    - Parent concept (the total)
    - Extended link role

    Per XBRL Calculations 1.1: same concept can be a parent in different
    roles with completely different children.
    """
    parent_concept: str
    role: str

    def __hash__(self):
        return hash((self.parent_concept, self.role))

    def __eq__(self, other):
        if not isinstance(other, CalculationKey):
            return False
        return self.parent_concept == other.parent_concept and self.role == other.role


class RoleScopedCalculations:
    """
    Container for calculations scoped by extended link role.

    XBRL Calculations 1.1 requires that calculation verification be performed
    within the context of a single extended link role. This class ensures
    calculations from different roles are kept separate.

    Example:
        # IncomeTaxExpenseBenefit in Income Statement role:
        # children = [IncomeTaxExpenseContinuingOperations]
        # weight = -1

        # IncomeTaxExpenseBenefit in Tax Disclosure role:
        # children = [CurrentIncomeTaxExpense, DeferredIncomeTaxExpense, ...]
        # weight = 1

        # Without role scoping, these children would be mixed together,
        # causing massive calculation failures.
    """

    def __init__(self):
        """Initialize empty role-scoped calculations."""
        self.logger = logging.getLogger('process.role_scoping')
        # Map: CalculationKey -> list[RoleScopedArc]
        self._calculations: dict[CalculationKey, list[RoleScopedArc]] = {}
        # Map: role -> set of parent concepts in that role
        self._role_parents: dict[str, set[str]] = {}
        # Map: parent_concept -> list of roles it appears in
        self._parent_roles: dict[str, list[str]] = {}

    @classmethod
    def from_networks(cls, networks: list[CalculationNetwork]) -> 'RoleScopedCalculations':
        """
        Create role-scoped calculations from calculation networks.

        Args:
            networks: List of CalculationNetwork from XBRL reader

        Returns:
            RoleScopedCalculations with all arcs scoped by role
        """
        instance = cls()

        for network in networks:
            role = network.role
            if not role:
                instance.logger.warning(
                    f"Calculation network has no role, skipping {len(network.arcs)} arcs"
                )
                continue

            for arc in network.arcs:
                instance.add_arc(arc, role)

        instance.logger.info(
            f"Created role-scoped calculations: {len(instance._calculations)} unique "
            f"(parent, role) combinations across {len(instance._role_parents)} roles"
        )

        return instance

    def add_arc(self, arc: CalculationArc, role: str) -> None:
        """
        Add a calculation arc with role context.

        Args:
            arc: CalculationArc from XBRL reader
            role: Extended link role this arc belongs to
        """
        key = CalculationKey(parent_concept=arc.parent_concept, role=role)

        if key not in self._calculations:
            self._calculations[key] = []

        self._calculations[key].append(RoleScopedArc.from_arc(arc, role))

        # Track role -> parents mapping
        if role not in self._role_parents:
            self._role_parents[role] = set()
        self._role_parents[role].add(arc.parent_concept)

        # Track parent -> roles mapping
        if arc.parent_concept not in self._parent_roles:
            self._parent_roles[arc.parent_concept] = []
        if role not in self._parent_roles[arc.parent_concept]:
            self._parent_roles[arc.parent_concept].append(role)

    def get_children(
        self,
        parent_concept: str,
        role: str
    ) -> list[tuple[str, float]]:
        """
        Get children for a parent within a specific role.

        Args:
            parent_concept: Parent concept name
            role: Extended link role

        Returns:
            List of (child_concept, weight) tuples
        """
        key = CalculationKey(parent_concept=parent_concept, role=role)
        arcs = self._calculations.get(key, [])
        return [(arc.child_concept, arc.weight) for arc in arcs]

    def get_children_normalized(
        self,
        parent_concept: str,
        role: str,
        normalizer=None
    ) -> list[tuple[str, float]]:
        """
        Get children with normalized concept names for matching.

        Args:
            parent_concept: Parent concept name
            role: Extended link role
            normalizer: Optional function to normalize concept names

        Returns:
            List of (normalized_child_concept, weight) tuples
        """
        if normalizer is None:
            normalizer = lambda x: normalize_name(x.split(':')[-1] if ':' in x else x)

        children = self.get_children(parent_concept, role)
        return [(normalizer(child), weight) for child, weight in children]

    def get_roles_for_parent(self, parent_concept: str) -> list[str]:
        """
        Get all roles where a concept appears as a parent.

        This is useful for diagnostics - if a concept appears in multiple
        roles, its calculation children will differ by role.

        Args:
            parent_concept: Parent concept name

        Returns:
            List of role URIs/names where concept is a parent
        """
        return self._parent_roles.get(parent_concept, [])

    def get_parents_for_role(self, role: str) -> set[str]:
        """
        Get all parent concepts in a specific role.

        Args:
            role: Extended link role

        Returns:
            Set of parent concept names in that role
        """
        return self._role_parents.get(role, set())

    def iter_calculations(self) -> Iterator[tuple[CalculationKey, list[RoleScopedArc]]]:
        """
        Iterate over all calculations grouped by (parent, role).

        Yields:
            Tuple of (CalculationKey, list of RoleScopedArc)
        """
        yield from self._calculations.items()

    def iter_by_role(self, role: str) -> Iterator[tuple[str, list[RoleScopedArc]]]:
        """
        Iterate over calculations in a specific role.

        Args:
            role: Extended link role to filter by

        Yields:
            Tuple of (parent_concept, list of RoleScopedArc)
        """
        for key, arcs in self._calculations.items():
            if key.role == role:
                yield key.parent_concept, arcs

    def has_multi_role_parent(self, parent_concept: str) -> bool:
        """
        Check if a parent concept appears in multiple roles.

        This is a diagnostic flag - concepts in multiple roles need
        careful handling to avoid mixing calculations.

        Args:
            parent_concept: Parent concept name

        Returns:
            True if concept appears in more than one role
        """
        roles = self._parent_roles.get(parent_concept, [])
        return len(roles) > 1

    def get_multi_role_parents(self) -> dict[str, list[str]]:
        """
        Get all parent concepts that appear in multiple roles.

        Returns:
            Dict mapping parent_concept -> list of roles
        """
        return {
            parent: roles
            for parent, roles in self._parent_roles.items()
            if len(roles) > 1
        }

    def get_summary(self) -> dict:
        """
        Get summary of role-scoped calculations.

        Returns:
            Dict with statistics about the calculations
        """
        multi_role = self.get_multi_role_parents()
        return {
            'total_calculations': len(self._calculations),
            'total_roles': len(self._role_parents),
            'unique_parents': len(self._parent_roles),
            'multi_role_parents': len(multi_role),
            'multi_role_parent_list': list(multi_role.keys())[:20],  # First 20 for display
            'roles': list(self._role_parents.keys()),
        }

    def __len__(self) -> int:
        return len(self._calculations)


def group_arcs_by_role_and_parent(
    calc_networks: list[CalculationNetwork]
) -> dict[tuple[str, str], list[CalculationArc]]:
    """
    Group calculation arcs by (role, parent) tuple.

    This is the core function for role-scoped calculation verification.
    Instead of grouping arcs by parent alone (which mixes roles), we
    group by (role, parent) to keep calculations separate.

    Args:
        calc_networks: List of CalculationNetwork from XBRL reader

    Returns:
        Dict mapping (role, parent_concept) -> list of arcs
    """
    groups: dict[tuple[str, str], list[CalculationArc]] = {}

    for network in calc_networks:
        role = network.role
        for arc in network.arcs:
            key = (role, arc.parent_concept)
            if key not in groups:
                groups[key] = []
            groups[key].append(arc)

    return groups


def extract_role_name(role_uri: str) -> str:
    """
    Extract short role name from full role URI.

    Args:
        role_uri: Full role URI

    Returns:
        Short role name (last path segment)
    """
    return RoleInfo._extract_role_name(role_uri)


def is_same_role(role1: str, role2: str, strict: bool = False) -> bool:
    """
    Check if two role identifiers refer to the same role.

    Handles matching by:
    - Exact match
    - Short name match (if strict=False)

    Args:
        role1: First role URI or name
        role2: Second role URI or name
        strict: If True, require exact match

    Returns:
        True if roles match
    """
    if role1 == role2:
        return True

    if strict:
        return False

    # Try short name match
    name1 = extract_role_name(role1)
    name2 = extract_role_name(role2)
    return name1 == name2 and name1 != ""


__all__ = [
    'RoleInfo',
    'RoleScopedArc',
    'CalculationKey',
    'RoleScopedCalculations',
    'group_arcs_by_role_and_parent',
    'extract_role_name',
    'is_same_role',
]
