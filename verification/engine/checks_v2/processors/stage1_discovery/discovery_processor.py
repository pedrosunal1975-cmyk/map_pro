# Path: verification/engine/checks_v2/processors/stage1_discovery/discovery_processor.py
"""
Stage 1: Discovery Processor

Scans XBRL files to discover and extract raw data:
- Facts from instance document
- Contexts from instance document
- Units from instance document
- Calculations from linkbase
- Sign attributes from iXBRL

RESPONSIBILITY: Find and extract data. NO transformation or validation.
All data is passed as-is to Stage 2 for normalization.

TOOLS USED:
- None directly (reads from parsed.json or XBRL files)

OUTPUT: DiscoveryResult with all raw discovered elements
"""

import json
import logging
from pathlib import Path
from typing import Optional

from ..pipeline_data import (
    DiscoveryResult,
    DiscoveredFact,
    DiscoveredContext,
    DiscoveredUnit,
    DiscoveredCalculation,
)


class DiscoveryProcessor:
    """
    Stage 1: Discovers raw data from XBRL filing.

    Reads parsed.json or XBRL instance to extract:
    1. All facts with their raw values
    2. All contexts with period info
    3. All units
    4. Calculation relationships from linkbase
    5. Sign attributes from iXBRL

    Usage:
        processor = DiscoveryProcessor()
        result = processor.discover(filing_path)

        # Result contains all raw discovered data
        print(f"Found {len(result.facts)} facts")
        print(f"Found {len(result.contexts)} contexts")
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage1.discovery')

    def discover(self, filing_path: Path | str) -> DiscoveryResult:
        """
        Discover all data from a filing.

        Args:
            filing_path: Path to filing directory or parsed.json

        Returns:
            DiscoveryResult with all discovered elements
        """
        filing_path = Path(filing_path)
        self.logger.info(f"Stage 1: Discovering data from {filing_path}")

        result = DiscoveryResult(filing_path=filing_path)

        # Find parsed.json (primary source)
        parsed_json = self._find_parsed_json(filing_path)
        if parsed_json:
            self._discover_from_parsed_json(parsed_json, result)
        else:
            result.errors.append(f"No parsed.json found in {filing_path}")
            self.logger.warning(f"No parsed.json found in {filing_path}")

        # Build statistics
        result.stats = {
            'facts_discovered': len(result.facts),
            'contexts_discovered': len(result.contexts),
            'units_discovered': len(result.units),
            'calculations_discovered': len(result.calculations),
            'errors_count': len(result.errors),
            'warnings_count': len(result.warnings),
        }

        self.logger.info(
            f"Stage 1 complete: {result.stats['facts_discovered']} facts, "
            f"{result.stats['contexts_discovered']} contexts, "
            f"{result.stats['calculations_discovered']} calculations"
        )

        return result

    def _find_parsed_json(self, filing_path: Path) -> Optional[Path]:
        """Find parsed.json in filing directory."""
        if filing_path.is_file() and filing_path.name == 'parsed.json':
            return filing_path

        if filing_path.is_dir():
            parsed = filing_path / 'parsed.json'
            if parsed.exists():
                return parsed

        return None

    def _discover_from_parsed_json(self, parsed_json: Path, result: DiscoveryResult) -> None:
        """Extract data from parsed.json."""
        try:
            with open(parsed_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result.instance_file = parsed_json

            # Extract metadata
            metadata = data.get('metadata', {})
            result.entry_point = metadata.get('entry_point')
            result.taxonomy_refs = metadata.get('taxonomy_references', [])

            # Extract namespaces
            result.namespaces = data.get('namespaces', {})

            # Discover facts
            self._discover_facts(data, result)

            # Discover contexts
            self._discover_contexts(data, result)

            # Discover units
            self._discover_units(data, result)

            # Discover calculations
            self._discover_calculations(data, result)

        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON in {parsed_json}: {e}")
        except Exception as e:
            result.errors.append(f"Error reading {parsed_json}: {e}")

    def _discover_facts(self, data: dict, result: DiscoveryResult) -> None:
        """Discover facts from parsed data."""
        # Facts may be in different structures depending on parser output
        facts_data = data.get('facts', [])

        if isinstance(facts_data, list):
            for fact in facts_data:
                discovered = self._parse_fact_entry(fact)
                if discovered:
                    result.facts.append(discovered)

        elif isinstance(facts_data, dict):
            # Facts keyed by concept
            for concept, fact_list in facts_data.items():
                if isinstance(fact_list, list):
                    for fact in fact_list:
                        fact['concept'] = concept
                        discovered = self._parse_fact_entry(fact)
                        if discovered:
                            result.facts.append(discovered)

        # Also check statements for facts
        statements = data.get('statements', {})
        for stmt_name, stmt_data in statements.items():
            if isinstance(stmt_data, dict):
                line_items = stmt_data.get('line_items', [])
                for item in line_items:
                    facts = self._extract_facts_from_line_item(item, stmt_name)
                    result.facts.extend(facts)

    def _parse_fact_entry(self, fact: dict) -> Optional[DiscoveredFact]:
        """Parse a single fact entry."""
        concept = fact.get('concept') or fact.get('name')
        if not concept:
            return None

        return DiscoveredFact(
            concept=concept,
            value=fact.get('value'),
            context_id=fact.get('context_id') or fact.get('contextRef', ''),
            unit_ref=fact.get('unit_ref') or fact.get('unitRef'),
            decimals=self._parse_decimals(fact.get('decimals')),
            is_nil=fact.get('is_nil', False) or fact.get('nil', False),
            sign=fact.get('sign'),
            format=fact.get('format'),
            source_file=str(fact.get('source', '')),
        )

    def _extract_facts_from_line_item(self, item: dict, statement: str) -> list[DiscoveredFact]:
        """Extract facts from statement line item."""
        facts = []
        concept = item.get('concept') or item.get('name')
        if not concept:
            return facts

        # Line items may have values for multiple periods
        values = item.get('values', {})
        if isinstance(values, dict):
            for context_id, value_data in values.items():
                if isinstance(value_data, dict):
                    facts.append(DiscoveredFact(
                        concept=concept,
                        value=value_data.get('value'),
                        context_id=context_id,
                        unit_ref=value_data.get('unit'),
                        decimals=self._parse_decimals(value_data.get('decimals')),
                        is_nil=value_data.get('is_nil', False),
                        sign=value_data.get('sign'),
                    ))
                else:
                    # Simple value
                    facts.append(DiscoveredFact(
                        concept=concept,
                        value=value_data,
                        context_id=context_id,
                    ))

        return facts

    def _discover_contexts(self, data: dict, result: DiscoveryResult) -> None:
        """Discover contexts from parsed data."""
        contexts_data = data.get('contexts', {})

        if isinstance(contexts_data, dict):
            for ctx_id, ctx_data in contexts_data.items():
                if isinstance(ctx_data, dict):
                    discovered = DiscoveredContext(
                        context_id=ctx_id,
                        period_type=ctx_data.get('period_type', ''),
                        start_date=ctx_data.get('start_date'),
                        end_date=ctx_data.get('end_date'),
                        instant_date=ctx_data.get('instant'),
                        entity_id=ctx_data.get('entity', ''),
                        dimensions=ctx_data.get('dimensions', {}),
                    )
                    result.contexts.append(discovered)

    def _discover_units(self, data: dict, result: DiscoveryResult) -> None:
        """Discover units from parsed data."""
        units_data = data.get('units', {})

        if isinstance(units_data, dict):
            for unit_id, unit_data in units_data.items():
                if isinstance(unit_data, dict):
                    discovered = DiscoveredUnit(
                        unit_id=unit_id,
                        measure=unit_data.get('measure', ''),
                        numerator=unit_data.get('numerator'),
                        denominator=unit_data.get('denominator'),
                    )
                elif isinstance(unit_data, str):
                    discovered = DiscoveredUnit(
                        unit_id=unit_id,
                        measure=unit_data,
                    )
                else:
                    continue
                result.units.append(discovered)

    def _discover_calculations(self, data: dict, result: DiscoveryResult) -> None:
        """Discover calculation relationships from parsed data."""
        # Calculations from company linkbase
        calc_data = data.get('calculations', {})

        if isinstance(calc_data, dict):
            for role, role_data in calc_data.items():
                if isinstance(role_data, dict):
                    trees = role_data.get('trees', [])
                    for tree in trees:
                        self._extract_calculation_tree(tree, role, 'company', result)

        # Calculations from taxonomy (if available)
        taxonomy_calc = data.get('taxonomy_calculations', {})
        if isinstance(taxonomy_calc, dict):
            for role, role_data in taxonomy_calc.items():
                if isinstance(role_data, dict):
                    trees = role_data.get('trees', [])
                    for tree in trees:
                        self._extract_calculation_tree(tree, role, 'taxonomy', result)

    def _extract_calculation_tree(
        self,
        tree: dict,
        role: str,
        source: str,
        result: DiscoveryResult
    ) -> None:
        """Extract calculation relationships from a tree structure."""
        parent = tree.get('concept') or tree.get('parent')
        if not parent:
            return

        children = tree.get('children', [])
        for child in children:
            if isinstance(child, dict):
                child_concept = child.get('concept') or child.get('name')
                weight = child.get('weight', 1.0)
                order = child.get('order', 0.0)

                if child_concept:
                    result.calculations.append(DiscoveredCalculation(
                        parent_concept=parent,
                        child_concept=child_concept,
                        weight=float(weight),
                        order=float(order),
                        role=role,
                        source=source,
                    ))

                # Recurse for nested trees
                if child.get('children'):
                    self._extract_calculation_tree(child, role, source, result)

    def _parse_decimals(self, value) -> Optional[int]:
        """Parse decimals value."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            if value.upper() == 'INF':
                return None  # Infinite precision
            try:
                return int(value)
            except ValueError:
                return None
        return None


__all__ = ['DiscoveryProcessor']
