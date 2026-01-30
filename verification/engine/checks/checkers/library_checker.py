# Path: verification/engine/checks/library_checker.py
"""
Library Checker for Verification Module

Validates against standard taxonomy definitions.
Optional check - runs after company-based checks.

LIBRARY CHECK (Quality):
Compare statements against standard taxonomy:
1. Are concepts used correctly?
2. Are period types appropriate?
3. Are value types consistent with taxonomy definitions?

This is informational - low scores don't invalidate data,
but may indicate unusual reporting choices.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ....loaders.mapped_reader import Statement, StatementFact, MappedStatements
from ....loaders.taxonomy_reader import TaxonomyReader, TaxonomyDefinition, ConceptDefinition
from ..core.constants import (
    CHECK_CONCEPT_VALIDITY,
    CHECK_PERIOD_TYPE_MATCH,
    CHECK_BALANCE_TYPE_MATCH,
    CHECK_DATA_TYPE_MATCH,
)
from ....constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from ..core.check_result import CheckResult


class LibraryChecker:
    """
    Validates against standard taxonomy definitions.

    Compares concepts used in statements against their definitions
    in the standard taxonomy (us-gaap, ifrs, etc.).

    Example:
        checker = LibraryChecker()
        results = checker.check_all(statements, 'us-gaap-2023')
        for result in results:
            if not result.passed:
                print(f"{result.check_name}: {result.message}")
    """

    def __init__(self):
        """Initialize library checker."""
        self.logger = logging.getLogger('process.library_checker')
        self.taxonomy_reader = TaxonomyReader()

    def check_all(
        self,
        statements: MappedStatements,
        taxonomy_id: Optional[str] = None
    ) -> list[CheckResult]:
        """
        Run all library checks on statements.

        Args:
            statements: MappedStatements from mapped_reader
            taxonomy_id: Optional taxonomy identifier (e.g., 'us-gaap-2023')

        Returns:
            List of CheckResult objects
        """
        self.logger.info(f"Running library checks against taxonomy: {taxonomy_id or 'auto-detect'}")
        results = []

        # Try to load taxonomy
        taxonomy = None
        if taxonomy_id:
            taxonomy = self.taxonomy_reader.read_taxonomy(taxonomy_id)

        if not taxonomy:
            self.logger.warning(f"Failed to load taxonomy: {taxonomy_id}")
            results.append(CheckResult(
                check_name=CHECK_CONCEPT_VALIDITY,
                check_type='library',
                passed=False,  # NO FAKE CONFIRMATION - if we can't check, it's a failure
                severity=SEVERITY_WARNING,
                message=f"Cannot validate: taxonomy '{taxonomy_id}' not available or failed to load"
            ))
            return results

        # Check concept validity
        validity_results = self.check_concept_validity(statements, taxonomy)
        results.extend(validity_results)

        # Check period type consistency
        period_results = self.check_period_type_consistency(statements, taxonomy)
        results.extend(period_results)

        # Check balance type consistency
        balance_results = self.check_balance_type_consistency(statements, taxonomy)
        results.extend(balance_results)

        passed = sum(1 for r in results if r.passed)
        self.logger.info(f"Library checks complete: {passed}/{len(results)} passed")

        return results

    def check_concept_validity(
        self,
        statements: MappedStatements,
        taxonomy: TaxonomyDefinition
    ) -> list[CheckResult]:
        """
        Check if concepts exist in the declared taxonomy.

        Args:
            statements: MappedStatements object
            taxonomy: TaxonomyDefinition from taxonomy_reader

        Returns:
            List of CheckResult for concept validity
        """
        results = []
        unknown_concepts = []
        valid_concepts = []
        extension_concepts = []

        for statement in statements.statements:
            for fact in statement.facts:
                if fact.is_abstract:
                    continue

                concept = fact.concept
                namespace = ''
                local_name = concept

                if ':' in concept:
                    parts = concept.split(':')
                    namespace = parts[0]
                    local_name = parts[1]

                # Check if it's a standard taxonomy concept
                concept_def = taxonomy.concepts.get(concept)
                if not concept_def:
                    # Try with just local name
                    concept_def = taxonomy.concepts.get(local_name)

                if concept_def:
                    valid_concepts.append(concept)
                elif self._is_extension_concept(namespace, taxonomy):
                    extension_concepts.append(concept)
                else:
                    unknown_concepts.append({
                        'concept': concept,
                        'statement': statement.name,
                    })

        # Report findings
        total_concepts = len(valid_concepts) + len(extension_concepts) + len(unknown_concepts)

        if unknown_concepts:
            results.append(CheckResult(
                check_name=CHECK_CONCEPT_VALIDITY,
                check_type='library',
                passed=False,
                severity=SEVERITY_INFO,  # Info only - extensions are valid
                message=f"{len(unknown_concepts)} concepts not found in standard taxonomy",
                details={
                    'unknown_concepts': unknown_concepts[:20],  # Limit to first 20
                    'total_unknown': len(unknown_concepts),
                    'total_valid': len(valid_concepts),
                    'total_extension': len(extension_concepts),
                }
            ))
        else:
            results.append(CheckResult(
                check_name=CHECK_CONCEPT_VALIDITY,
                check_type='library',
                passed=True,
                severity=SEVERITY_INFO,
                message=f"All {len(valid_concepts)} standard concepts are valid",
                details={
                    'total_valid': len(valid_concepts),
                    'total_extension': len(extension_concepts),
                }
            ))

        return results

    def check_period_type_consistency(
        self,
        statements: MappedStatements,
        taxonomy: TaxonomyDefinition
    ) -> list[CheckResult]:
        """
        Check if period types match taxonomy definitions.

        Instant concepts should have instant contexts.
        Duration concepts should have duration contexts.

        Args:
            statements: MappedStatements object
            taxonomy: TaxonomyDefinition

        Returns:
            List of CheckResult for period type checks
        """
        results = []
        mismatches = []
        checked = 0

        for statement in statements.statements:
            for fact in statement.facts:
                if fact.is_abstract:
                    continue

                concept = fact.concept
                concept_def = self._get_concept_definition(concept, taxonomy)

                if not concept_def or not concept_def.period_type:
                    continue

                checked += 1
                expected_type = concept_def.period_type.lower()

                # Determine actual period type from fact
                actual_type = self._determine_period_type(fact)

                if actual_type and expected_type != actual_type:
                    mismatches.append({
                        'concept': concept,
                        'expected': expected_type,
                        'actual': actual_type,
                        'statement': statement.name,
                    })

        if mismatches:
            results.append(CheckResult(
                check_name=CHECK_PERIOD_TYPE_MATCH,
                check_type='library',
                passed=False,
                severity=SEVERITY_WARNING,
                message=f"{len(mismatches)} period type mismatches found",
                details={
                    'mismatches': mismatches[:20],
                    'total_mismatches': len(mismatches),
                    'total_checked': checked,
                }
            ))
        else:
            results.append(CheckResult(
                check_name=CHECK_PERIOD_TYPE_MATCH,
                check_type='library',
                passed=True,
                severity=SEVERITY_INFO,
                message=f"All {checked} period types are consistent with taxonomy"
            ))

        return results

    def check_balance_type_consistency(
        self,
        statements: MappedStatements,
        taxonomy: TaxonomyDefinition
    ) -> list[CheckResult]:
        """
        Check if balance types (debit/credit) match taxonomy definitions.

        Args:
            statements: MappedStatements object
            taxonomy: TaxonomyDefinition

        Returns:
            List of CheckResult for balance type checks
        """
        results = []
        suspicious = []
        checked = 0

        for statement in statements.statements:
            for fact in statement.facts:
                if fact.is_abstract or fact.value is None:
                    continue

                concept = fact.concept
                concept_def = self._get_concept_definition(concept, taxonomy)

                if not concept_def or not concept_def.balance_type:
                    continue

                checked += 1

                try:
                    value = float(fact.value)
                except (ValueError, TypeError):
                    continue

                balance_type = concept_def.balance_type.lower()

                # Check for unusual signs based on balance type
                # Debit items are typically positive for assets/expenses
                # Credit items are typically positive for liabilities/equity/revenue
                if balance_type == 'debit' and value < 0:
                    # Negative debit might be unusual
                    suspicious.append({
                        'concept': concept,
                        'balance_type': balance_type,
                        'value': value,
                        'statement': statement.name,
                        'note': 'Negative value for debit-balance concept',
                    })
                elif balance_type == 'credit' and value < 0:
                    # Negative credit might be unusual
                    suspicious.append({
                        'concept': concept,
                        'balance_type': balance_type,
                        'value': value,
                        'statement': statement.name,
                        'note': 'Negative value for credit-balance concept',
                    })

        if suspicious:
            results.append(CheckResult(
                check_name=CHECK_BALANCE_TYPE_MATCH,
                check_type='library',
                passed=True,  # Info only - negative values can be valid
                severity=SEVERITY_INFO,
                message=f"{len(suspicious)} values with potentially unusual signs",
                details={
                    'suspicious': suspicious[:20],
                    'total_suspicious': len(suspicious),
                    'total_checked': checked,
                }
            ))
        else:
            results.append(CheckResult(
                check_name=CHECK_BALANCE_TYPE_MATCH,
                check_type='library',
                passed=True,
                severity=SEVERITY_INFO,
                message=f"All {checked} balance types appear consistent"
            ))

        return results

    def _get_concept_definition(
        self,
        concept: str,
        taxonomy: TaxonomyDefinition
    ) -> Optional[ConceptDefinition]:
        """Get concept definition from taxonomy."""
        concept_def = taxonomy.concepts.get(concept)
        if concept_def:
            return concept_def

        # Try without namespace
        if ':' in concept:
            local_name = concept.split(':')[-1]
            return taxonomy.concepts.get(local_name)

        return None

    def _is_extension_concept(self, namespace: str, taxonomy: TaxonomyDefinition) -> bool:
        """Check if namespace indicates an extension (company-specific) concept."""
        if not namespace:
            return False

        # Extension concepts typically have company-specific namespaces
        standard_prefixes = ['us-gaap', 'ifrs', 'dei', 'srt', 'country']
        return namespace.lower() not in standard_prefixes

    def _determine_period_type(self, fact: StatementFact) -> Optional[str]:
        """Determine period type from fact attributes."""
        # If both start and end are present, it's a duration
        if fact.period_start and fact.period_end:
            return 'duration'

        # If only end date (instant) is present
        if fact.period_end and not fact.period_start:
            return 'instant'

        return None


__all__ = ['LibraryChecker']
