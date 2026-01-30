# Path: verification/engine/checks_v2/processors/stage2_preparation/preparation_processor.py
"""
Stage 2: Preparation Processor

Transforms discovered data into verified, normalized form ready for verification:
- Normalizes concept names using naming tools
- Classifies contexts using context tools
- Parses and validates fact values using fact tools
- Groups facts by context (C-Equal)
- Parses sign corrections using sign tools
- Detects duplicates using duplicate handler

RESPONSIBILITY: Transform and organize. NO verification logic.
All data is prepared for Stage 3 to verify.

TOOLS USED:
- naming/: Normalizer for concept names
- context/: ContextClassifier, ContextGrouper for context handling
- period/: PeriodExtractor for period normalization
- fact/: ValueParser for value parsing, DuplicateHandler
- sign/: SignParser for sign correction extraction

OUTPUT: PreparationResult with normalized, grouped data
"""

import logging
from typing import Optional

from ..pipeline_data import (
    DiscoveryResult,
    PreparationResult,
    PreparedFact,
    PreparedContext,
    PreparedCalculation,
    FactGroup,
)

# Import tools
from ...tools.naming import Normalizer
from ...tools.context import ContextClassifier, ContextGrouper
from ...tools.period import PeriodExtractor
from ...tools.fact import ValueParser, DuplicateHandler
from ...tools.sign import SignParser


class PreparationProcessor:
    """
    Stage 2: Prepares discovered data for verification.

    Transforms raw discovered data using specialized tools:
    1. Normalize concept names (multiple strategies available)
    2. Classify contexts as dimensional or default
    3. Parse fact values to numeric form
    4. Group facts by context (C-Equal principle)
    5. Extract sign corrections from iXBRL
    6. Detect duplicate facts

    Tools are configurable - different strategies can be selected
    for different filing types.

    Usage:
        processor = PreparationProcessor()

        # Use default tools
        result = processor.prepare(discovery_result)

        # Or configure tools
        processor.set_naming_strategy('local_name')
        result = processor.prepare(discovery_result)
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage2.preparation')

        # Initialize tools with defaults
        self._normalizer = Normalizer()
        self._classifier = ContextClassifier()
        self._period_extractor = PeriodExtractor()
        self._value_parser = ValueParser()
        self._duplicate_handler = DuplicateHandler()
        self._sign_parser = SignParser()

        # Configuration
        self._naming_strategy = 'canonical'
        self._context_strategy = 'default'

    def set_naming_strategy(self, strategy: str) -> None:
        """
        Set the naming normalization strategy.

        Options: 'canonical', 'local_name', 'full_qualified', 'auto'
        """
        self._naming_strategy = strategy
        self.logger.info(f"Naming strategy set to: {strategy}")

    def set_context_strategy(self, strategy: str) -> None:
        """
        Set the context classification strategy.

        Options: 'default', 'strict'
        """
        self._context_strategy = strategy
        self._classifier.set_strategy(strategy)
        self.logger.info(f"Context strategy set to: {strategy}")

    def prepare(self, discovery: DiscoveryResult) -> PreparationResult:
        """
        Prepare discovered data for verification.

        Args:
            discovery: DiscoveryResult from Stage 1

        Returns:
            PreparationResult ready for Stage 3
        """
        self.logger.info(f"Stage 2: Preparing {len(discovery.facts)} facts")

        result = PreparationResult(discovery=discovery)

        # Step 1: Prepare contexts first (needed for fact classification)
        self._prepare_contexts(discovery, result)

        # Step 2: Parse sign corrections from discovered facts
        self._extract_sign_corrections(discovery, result)

        # Step 3: Prepare and normalize facts
        self._prepare_facts(discovery, result)

        # Step 4: Group facts by context (C-Equal)
        self._group_facts(result)

        # Step 5: Build cross-context lookup
        self._build_concept_lookup(result)

        # Step 6: Detect duplicates
        self._detect_duplicates(result)

        # Step 7: Prepare calculations
        self._prepare_calculations(discovery, result)

        # Build statistics
        result.stats = {
            'facts_prepared': len(result.facts),
            'contexts_prepared': len(result.contexts),
            'fact_groups': len(result.fact_groups),
            'calculations_prepared': len(result.calculations),
            'sign_corrections': len(result.sign_corrections),
            'duplicates_found': len(result.duplicates),
            'errors_count': len(result.errors),
            'warnings_count': len(result.warnings),
        }

        self.logger.info(
            f"Stage 2 complete: {result.stats['facts_prepared']} facts in "
            f"{result.stats['fact_groups']} groups, "
            f"{result.stats['calculations_prepared']} calculations"
        )

        return result

    def _prepare_contexts(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Prepare contexts using context tools."""
        for ctx in discovery.contexts:
            # Extract period info
            period_info = self._period_extractor.extract(ctx.context_id)

            # Classify as dimensional or default
            is_dimensional = self._classifier.is_dimensional(ctx.context_id)

            # Determine period type
            period_type = ctx.period_type
            if not period_type:
                period_type = period_info.period_type.value

            prepared = PreparedContext(
                context_id=ctx.context_id,
                period_type=period_type,
                period_key=period_info.period_key or ctx.context_id,
                year=period_info.year,
                is_dimensional=is_dimensional or bool(ctx.dimensions),
                dimensions=ctx.dimensions,
            )

            result.contexts[ctx.context_id] = prepared

    def _extract_sign_corrections(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Extract sign corrections from facts with sign attributes."""
        for fact in discovery.facts:
            if fact.sign:
                # Parse sign attribute
                correction = self._sign_parser.parse_sign_attribute(fact.sign)
                if correction != 1:
                    # Normalize concept for lookup
                    normalized = self._normalizer.normalize(
                        fact.concept, strategy=self._naming_strategy
                    )
                    key = (normalized, fact.context_id)
                    result.sign_corrections[key] = correction

                    self.logger.debug(
                        f"Sign correction for {fact.concept} in {fact.context_id}: {correction}"
                    )

    def _prepare_facts(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Prepare facts using fact and naming tools."""
        for fact in discovery.facts:
            # Skip nil facts
            if fact.is_nil:
                continue

            # Parse value
            value = self._value_parser.parse_value(fact.value)
            if value is None:
                # Skip unparseable values
                continue

            # Normalize concept name
            normalized = self._normalizer.normalize(
                fact.concept, strategy=self._naming_strategy
            )

            # Register in normalizer for bidirectional lookup
            self._normalizer.register(fact.concept, 'discovery')

            # Get context classification
            ctx_info = result.contexts.get(fact.context_id)
            is_dimensional = ctx_info.is_dimensional if ctx_info else False

            # Get sign correction
            sign_key = (normalized, fact.context_id)
            sign_correction = result.sign_corrections.get(sign_key, 1)

            prepared = PreparedFact(
                concept=normalized,
                original_concept=fact.concept,
                value=value,
                context_id=fact.context_id,
                unit=fact.unit_ref,
                decimals=fact.decimals,
                sign_correction=sign_correction,
                is_dimensional=is_dimensional,
            )

            result.facts.append(prepared)

    def _group_facts(self, result: PreparationResult) -> None:
        """Group facts by context using C-Equal principle."""
        grouper = ContextGrouper()

        for fact in result.facts:
            grouper.add_fact(
                concept=fact.concept,
                value=fact.value,
                context_id=fact.context_id,
                unit=fact.unit,
                decimals=fact.decimals,
                original_name=fact.original_concept,
            )

        # Convert grouper output to FactGroup structures
        for context_id in grouper.get_context_ids():
            ctx_group = grouper.get_group(context_id)
            if ctx_group:
                ctx_info = result.contexts.get(context_id)

                fact_group = FactGroup(
                    context_id=context_id,
                    period_key=ctx_info.period_key if ctx_info else context_id,
                    is_dimensional=ctx_info.is_dimensional if ctx_info else False,
                    facts={},
                )

                # Copy facts from grouper
                for concept in ctx_group.concepts():
                    fact_data = ctx_group.get(concept)
                    if fact_data:
                        # Find matching prepared fact
                        for pf in result.facts:
                            if pf.concept == concept and pf.context_id == context_id:
                                fact_group.facts[concept] = pf
                                break

                result.fact_groups[context_id] = fact_group

    def _build_concept_lookup(self, result: PreparationResult) -> None:
        """Build cross-context concept lookup for dimensional fallback."""
        for fact in result.facts:
            if fact.concept not in result.all_facts_by_concept:
                result.all_facts_by_concept[fact.concept] = []

            result.all_facts_by_concept[fact.concept].append((
                fact.context_id,
                fact.value,
                fact.unit,
                fact.decimals,
            ))

    def _detect_duplicates(self, result: PreparationResult) -> None:
        """Detect duplicate facts using duplicate handler."""
        # Build fact entries for duplicate detection
        from ...tools.fact import FactEntry

        entries_by_concept = {}
        for fact in result.facts:
            if fact.concept not in entries_by_concept:
                entries_by_concept[fact.concept] = []

            entries_by_concept[fact.concept].append(FactEntry(
                concept=fact.concept,
                original_concept=fact.original_concept,
                value=fact.value,
                unit=fact.unit,
                decimals=fact.decimals,
                context_id=fact.context_id,
            ))

        # Check each concept for duplicates
        for concept, entries in entries_by_concept.items():
            if len(entries) > 1:
                # Group by context to find true duplicates
                by_context = {}
                for entry in entries:
                    if entry.context_id not in by_context:
                        by_context[entry.context_id] = []
                    by_context[entry.context_id].append(entry)

                for context_id, ctx_entries in by_context.items():
                    if len(ctx_entries) > 1:
                        info = self._duplicate_handler.analyze(ctx_entries)
                        if info.has_duplicates:
                            key = f"{concept}:{context_id}"
                            result.duplicates[key] = info

    def _prepare_calculations(self, discovery: DiscoveryResult, result: PreparationResult) -> None:
        """Prepare calculation trees."""
        # Group calculations by parent
        calc_trees = {}

        for calc in discovery.calculations:
            # Normalize parent
            parent_norm = self._normalizer.normalize(
                calc.parent_concept, strategy=self._naming_strategy
            )

            key = (parent_norm, calc.role, calc.source)
            if key not in calc_trees:
                calc_trees[key] = {
                    'parent': parent_norm,
                    'original_parent': calc.parent_concept,
                    'children': [],
                    'role': calc.role,
                    'source': calc.source,
                }

            # Normalize child
            child_norm = self._normalizer.normalize(
                calc.child_concept, strategy=self._naming_strategy
            )

            calc_trees[key]['children'].append((child_norm, calc.weight))

        # Convert to PreparedCalculation
        for key, tree in calc_trees.items():
            result.calculations.append(PreparedCalculation(
                parent_concept=tree['parent'],
                original_parent=tree['original_parent'],
                children=tree['children'],
                role=tree['role'],
                source=tree['source'],
            ))


__all__ = ['PreparationProcessor']
