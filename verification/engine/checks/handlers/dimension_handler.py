# Path: verification/engine/checks/dimension_handler.py
"""
XBRL Dimension Handler for Verification

Parses definition linkbase to understand dimensional structures and
determine context relationships.

XBRL DIMENSIONAL CONCEPTS:
1. Hypercube (Table): Container for dimensional structure
2. Dimension (Axis): A dimensional qualifier (e.g., ClassOfStockAxis)
3. Domain: The set of allowed values for a dimension
4. Member: A specific value in a domain (e.g., CommonClassAMember)
5. Default Member: The member that applies when no explicit qualifier is given

CONTEXT CLASSIFICATION:
- Default Context: No dimensional qualifiers, or only default members
- Dimensional Context: Has explicit non-default dimension members

USAGE:
    handler = DimensionHandler()
    handler.parse_definition_linkbase('path/to/_def.xml')

    # Check if context is default for a role
    is_default = handler.is_default_context('c-4', role_dimensions)

    # Get related contexts for dimensional aggregation
    related = handler.get_related_contexts(context_id, all_contexts)

This module is AGNOSTIC - works with any XBRL filing that follows the
dimensional specification (XBRL Dimensions 1.0).
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from ...loaders.constants import normalize_name


@dataclass
class DimensionMember:
    """A member of a dimension domain."""
    name: str
    namespace: str = ""
    is_default: bool = False
    parent_member: Optional[str] = None


@dataclass
class Dimension:
    """An XBRL dimension (axis) with its members."""
    name: str
    namespace: str = ""
    domain: str = ""
    default_member: str = ""
    members: dict[str, DimensionMember] = field(default_factory=dict)

    def is_default_value(self, member: str) -> bool:
        """Check if a member is the default (or domain) for this dimension."""
        if not member:
            return True  # No value means default
        # Extract local name from member
        member_local = member.split(':')[-1] if ':' in member else member
        member_local = member_local.split('_')[-1] if '_' in member_local else member_local

        # Extract local name from default member
        default_local = self.default_member.split('_')[-1] if self.default_member else ''

        # Extract local name from domain
        domain_local = self.domain.split('_')[-1] if self.domain else ''

        # Use canonical normalize_name for comparison
        member_norm = normalize_name(member_local)
        default_norm = normalize_name(default_local) if default_local else ''
        domain_norm = normalize_name(domain_local) if domain_local else ''

        return member_norm == default_norm or member_norm == domain_norm


@dataclass
class RoleDimensions:
    """Dimensions applicable to a specific role (statement)."""
    role: str
    role_name: str = ""
    hypercube: str = ""
    dimensions: dict[str, Dimension] = field(default_factory=dict)

    def get_dimension_names(self) -> list[str]:
        """Get list of dimension names for this role."""
        return list(self.dimensions.keys())


@dataclass
class ContextDimensions:
    """Dimensional qualifiers for a specific context."""
    context_id: str
    dimensions: dict[str, str] = field(default_factory=dict)  # dimension -> member
    period_type: str = ""  # 'instant' or 'duration'
    period_value: str = ""  # date or start-end
    entity: str = ""

    def has_dimension(self, dimension_name: str) -> bool:
        """Check if context has a specific dimension."""
        dim_local = dimension_name.split('_')[-1] if dimension_name else ''
        dim_norm = normalize_name(dim_local)
        for dim in self.dimensions.keys():
            stored_local = dim.split('_')[-1]
            if normalize_name(stored_local) == dim_norm:
                return True
        return False

    def get_member(self, dimension_name: str) -> Optional[str]:
        """Get the member value for a dimension."""
        dim_local = dimension_name.split('_')[-1] if dimension_name else ''
        dim_norm = normalize_name(dim_local)
        for dim, member in self.dimensions.items():
            stored_local = dim.split('_')[-1]
            if normalize_name(stored_local) == dim_norm:
                return member
        return None


class DimensionHandler:
    """
    Handles XBRL dimensional structures for verification.

    Parses definition linkbase to understand:
    - Which dimensions apply to which roles
    - Default members for each dimension
    - How to classify contexts as default vs dimensional
    """

    # XML namespaces
    NS = {
        'link': 'http://www.xbrl.org/2003/linkbase',
        'xlink': 'http://www.w3.org/1999/xlink',
        'xbrldt': 'http://xbrl.org/2005/xbrldt',
        'xbrli': 'http://www.xbrl.org/2003/instance',
    }

    def __init__(self):
        self.logger = logging.getLogger('process.dimension_handler')
        self.roles: dict[str, RoleDimensions] = {}
        self.contexts: dict[str, ContextDimensions] = {}
        self._parsed = False

    def parse_definition_linkbase(self, def_file: str | Path) -> bool:
        """
        Parse definition linkbase to extract dimensional structure.

        Args:
            def_file: Path to _def.xml file

        Returns:
            True if parsed successfully
        """
        try:
            tree = ET.parse(def_file)
            root = tree.getroot()

            for def_link in root.findall('.//link:definitionLink', self.NS):
                role_uri = def_link.get('{http://www.w3.org/1999/xlink}role', '')
                role_name = role_uri.split('/')[-1]

                role_dims = RoleDimensions(role=role_uri, role_name=role_name)

                # Build locator map
                locators = {}
                for loc in def_link.findall('link:loc', self.NS):
                    label = loc.get('{http://www.w3.org/1999/xlink}label', '')
                    href = loc.get('{http://www.w3.org/1999/xlink}href', '')
                    if '#' in href:
                        concept = href.split('#')[-1]
                        locators[label] = concept

                # Process arcs
                for arc in def_link.findall('link:definitionArc', self.NS):
                    arcrole = arc.get('{http://www.w3.org/1999/xlink}arcrole', '')
                    from_label = arc.get('{http://www.w3.org/1999/xlink}from', '')
                    to_label = arc.get('{http://www.w3.org/1999/xlink}to', '')

                    from_concept = locators.get(from_label, from_label)
                    to_concept = locators.get(to_label, to_label)

                    # Hypercube-dimension: identifies dimensions for a hypercube
                    if 'hypercube-dimension' in arcrole:
                        dim = Dimension(name=to_concept)
                        role_dims.dimensions[to_concept] = dim

                    # Dimension-default: sets the default member
                    elif 'dimension-default' in arcrole:
                        if from_concept in role_dims.dimensions:
                            role_dims.dimensions[from_concept].default_member = to_concept

                    # Dimension-domain: sets the domain
                    elif 'dimension-domain' in arcrole:
                        if from_concept in role_dims.dimensions:
                            role_dims.dimensions[from_concept].domain = to_concept

                    # All: links line items to hypercube
                    elif arcrole.endswith('/all'):
                        role_dims.hypercube = to_concept

                if role_dims.dimensions:
                    self.roles[role_name] = role_dims

            self._parsed = True
            self.logger.info(f"Parsed {len(self.roles)} roles with dimensions")
            return True

        except Exception as e:
            self.logger.error(f"Failed to parse definition linkbase: {e}")
            return False

    def parse_instance_contexts(self, instance_file: str | Path) -> bool:
        """
        Parse XBRL instance document to extract context definitions.

        Args:
            instance_file: Path to XBRL instance document (.xml or .htm)

        Returns:
            True if parsed successfully
        """
        try:
            tree = ET.parse(instance_file)
            root = tree.getroot()

            # Find all context elements
            for ctx in root.findall('.//{http://www.xbrl.org/2003/instance}context'):
                ctx_id = ctx.get('id', '')
                if not ctx_id:
                    continue

                ctx_dims = ContextDimensions(context_id=ctx_id)

                # Extract period
                period = ctx.find('{http://www.xbrl.org/2003/instance}period')
                if period is not None:
                    instant = period.find('{http://www.xbrl.org/2003/instance}instant')
                    if instant is not None:
                        ctx_dims.period_type = 'instant'
                        ctx_dims.period_value = instant.text or ''
                    else:
                        start = period.find('{http://www.xbrl.org/2003/instance}startDate')
                        end = period.find('{http://www.xbrl.org/2003/instance}endDate')
                        if start is not None and end is not None:
                            ctx_dims.period_type = 'duration'
                            ctx_dims.period_value = f"{start.text}_{end.text}"

                # Extract entity
                entity = ctx.find('.//{http://www.xbrl.org/2003/instance}identifier')
                if entity is not None:
                    ctx_dims.entity = entity.text or ''

                # Extract dimensional qualifiers from segment
                segment = ctx.find('.//{http://www.xbrl.org/2003/instance}segment')
                if segment is not None:
                    for explicit in segment.findall('.//{http://xbrl.org/2006/xbrldi}explicitMember'):
                        dimension = explicit.get('dimension', '')
                        member = explicit.text or ''
                        if dimension:
                            ctx_dims.dimensions[dimension] = member

                self.contexts[ctx_id] = ctx_dims

            self.logger.info(f"Parsed {len(self.contexts)} contexts")
            return True

        except Exception as e:
            self.logger.error(f"Failed to parse instance contexts: {e}")
            return False

    def is_default_context(
        self,
        context_id: str,
        role_name: str = None,
        context_dimensions: dict[str, str] = None
    ) -> bool:
        """
        Check if a context is a "default" context (no non-default dimensions).

        A context is default if:
        1. It has no dimensional qualifiers, OR
        2. All its dimensional qualifiers are default members

        Args:
            context_id: The context ID to check
            role_name: Optional role name to check against
            context_dimensions: Optional dict of dimension->member for the context

        Returns:
            True if context is default (no non-default dimensions)
        """
        # Get context dimensions
        dims = context_dimensions
        if dims is None and context_id in self.contexts:
            dims = self.contexts[context_id].dimensions

        if not dims:
            return True  # No dimensions = default

        # Check each dimension against role's defaults
        if role_name and role_name in self.roles:
            role_dims = self.roles[role_name]
            for dim_name, member in dims.items():
                dim_local = dim_name.split(':')[-1] if ':' in dim_name else dim_name
                # Find matching dimension in role
                for role_dim_name, role_dim in role_dims.dimensions.items():
                    if self._names_match(dim_local, role_dim_name):
                        if not role_dim.is_default_value(member):
                            return False  # Non-default member found
        else:
            # No role info - any dimension makes it non-default
            return len(dims) == 0

        return True

    def get_role_for_statement(self, statement_name: str) -> Optional[RoleDimensions]:
        """
        Get the role dimensions for a statement by name matching.

        Args:
            statement_name: Name like "ConsolidatedBalanceSheets"

        Returns:
            RoleDimensions if found
        """
        statement_norm = normalize_name(statement_name)
        for role_name, role_dims in self.roles.items():
            role_norm = normalize_name(role_name)
            if statement_norm in role_norm or role_norm in statement_norm:
                return role_dims
        return None

    def get_dimensions_for_role(self, role_name: str) -> list[str]:
        """
        Get list of dimension names for a role.

        Args:
            role_name: Role name

        Returns:
            List of dimension names
        """
        if role_name in self.roles:
            return self.roles[role_name].get_dimension_names()
        return []

    def find_default_context(
        self,
        dimensional_context: str,
        all_context_ids: list[str],
        role_name: str = None
    ) -> Optional[str]:
        """
        Find the default context that corresponds to a dimensional context.

        Matches by period and entity, but without dimensional qualifiers.

        Args:
            dimensional_context: The dimensional context ID
            all_context_ids: List of all available context IDs
            role_name: Optional role name for dimension checking

        Returns:
            Default context ID if found
        """
        if dimensional_context not in self.contexts:
            return None

        dim_ctx = self.contexts[dimensional_context]

        for ctx_id in all_context_ids:
            if ctx_id == dimensional_context:
                continue
            if ctx_id not in self.contexts:
                continue

            other_ctx = self.contexts[ctx_id]

            # Match period
            if other_ctx.period_value != dim_ctx.period_value:
                continue

            # Match entity
            if other_ctx.entity != dim_ctx.entity:
                continue

            # Check if it's default
            if self.is_default_context(ctx_id, role_name):
                return ctx_id

        return None

    def group_contexts_by_period(self) -> dict[str, list[str]]:
        """
        Group context IDs by their period.

        Returns:
            Dict mapping period_value -> list of context IDs
        """
        groups = {}
        for ctx_id, ctx_dims in self.contexts.items():
            period = ctx_dims.period_value
            if period not in groups:
                groups[period] = []
            groups[period].append(ctx_id)
        return groups

    def get_context_info(self, context_id: str) -> Optional[ContextDimensions]:
        """Get context dimension information."""
        return self.contexts.get(context_id)

    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two names match (ignoring namespace prefixes)."""
        local1 = name1.split('_')[-1] if name1 else ''
        local2 = name2.split('_')[-1] if name2 else ''
        return normalize_name(local1) == normalize_name(local2)

    def get_summary(self) -> dict:
        """Get summary of parsed dimensional structure."""
        return {
            'roles_with_dimensions': len(self.roles),
            'total_contexts': len(self.contexts),
            'contexts_with_dimensions': sum(
                1 for ctx in self.contexts.values() if ctx.dimensions
            ),
            'roles': {
                name: {
                    'dimensions': list(role.dimensions.keys()),
                    'hypercube': role.hypercube,
                }
                for name, role in self.roles.items()
            }
        }


__all__ = [
    'DimensionHandler',
    'Dimension',
    'DimensionMember',
    'RoleDimensions',
    'ContextDimensions',
]
