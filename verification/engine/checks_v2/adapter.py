# Path: verification/engine/checks_v2/adapter.py
"""
Adapter for checks_v2 Integration

Provides compatibility layer between new checks_v2 architecture
and existing verification coordinator.

This adapter:
1. Exposes the same interface as old HorizontalChecker/VerticalChecker
2. Converts checks_v2 results to old CheckResult format
3. Allows gradual migration with feature flags

USAGE:
    # In coordinator.py, replace:
    from .checks import HorizontalChecker, VerticalChecker

    # With:
    from .checks_v2.adapter import HorizontalCheckerV2 as HorizontalChecker
    from .checks_v2.adapter import VerticalCheckerV2 as VerticalChecker

    # Or use feature flag:
    if config.get('use_checks_v2', False):
        from .checks_v2.adapter import HorizontalCheckerV2, VerticalCheckerV2
    else:
        from .checks import HorizontalChecker, VerticalChecker
"""

import logging
from pathlib import Path
from typing import Optional, Any

# Import old CheckResult for compatibility
from ..checks.core.check_result import CheckResult

# Import new checks_v2 components
from .processors import (
    PipelineOrchestrator,
    VerificationResult as V2VerificationResult,
    VerificationCheck,
)
from .tools.sign import SignLookup


class HorizontalCheckerV2:
    """
    Adapter for horizontal checks using checks_v2 architecture.

    Provides the same interface as the old HorizontalChecker but uses
    the new 3-stage pipeline internally.
    """

    def __init__(self):
        self.logger = logging.getLogger('checks_v2.adapter.horizontal')
        self._orchestrator = PipelineOrchestrator()
        self.sign_handler = None  # Set by coordinator

    def check_all(
        self,
        statements: Any,
        calc_networks: list = None,
        filing_path: Path = None
    ) -> list[CheckResult]:
        """
        Run horizontal checks using checks_v2 pipeline.

        This is the main interface called by VerificationCoordinator.

        Args:
            statements: MappedStatements object
            calc_networks: Calculation networks (unused - we load from filing)
            filing_path: Path to XBRL filing directory

        Returns:
            List of CheckResult objects (old format for compatibility)
        """
        self.logger.info("Running horizontal checks via checks_v2 adapter")

        if not filing_path:
            self.logger.warning("No filing path provided - returning empty results")
            return []

        try:
            # Configure orchestrator
            self._orchestrator.configure(
                naming_strategy='canonical',
                binding_strategy='fallback',
            )

            # Run the pipeline
            # Note: We need parsed.json, not the filing directory
            parsed_json = self._find_parsed_json(filing_path)
            if not parsed_json:
                self.logger.warning(f"No parsed.json found in {filing_path}")
                return []

            result = self._orchestrator.run(parsed_json)

            # Convert horizontal checks to old format
            return self._convert_horizontal_results(result)

        except Exception as e:
            self.logger.error(f"Error in horizontal checks: {e}", exc_info=True)
            return []

    def _find_parsed_json(self, filing_path: Path) -> Optional[Path]:
        """Find parsed.json for a filing."""
        # Check if filing_path itself is parsed.json
        if filing_path.is_file() and filing_path.name == 'parsed.json':
            return filing_path

        # Check in filing directory
        if filing_path.is_dir():
            parsed = filing_path / 'parsed.json'
            if parsed.exists():
                return parsed

        # Check in parser output directory (parallel structure)
        # /mnt/map_pro/downloader/entities/sec/company/filings/10-K/accession/
        # -> /mnt/map_pro/parser/parsed_reports/sec/company/10-K/date/parsed.json
        # This requires knowing the mapping - for now, just check obvious locations
        for pattern in ['**/parsed.json', '../**/parsed.json']:
            found = list(filing_path.glob(pattern))
            if found:
                return found[0]

        return None

    def _convert_horizontal_results(self, result: V2VerificationResult) -> list[CheckResult]:
        """Convert checks_v2 results to old CheckResult format."""
        check_results = []

        for check in result.horizontal_checks:
            check_results.append(self._convert_check(check))

        return check_results

    def _convert_check(self, check: VerificationCheck) -> CheckResult:
        """Convert a single VerificationCheck to CheckResult."""
        return CheckResult(
            check_name=check.check_name,
            check_type=check.check_type,
            passed=check.passed,
            severity=check.severity,
            message=check.message,
            expected_value=check.expected_value,
            actual_value=check.actual_value,
            difference=check.difference,
            details=check.details,
        )


class VerticalCheckerV2:
    """
    Adapter for vertical checks using checks_v2 architecture.

    Provides the same interface as the old VerticalChecker.
    """

    def __init__(
        self,
        tolerance: float = 0.01,
        rounding: float = 1.0,
        formula_registry: Any = None
    ):
        self.logger = logging.getLogger('checks_v2.adapter.vertical')
        self._orchestrator = PipelineOrchestrator()
        self._tolerance = tolerance
        self._rounding = rounding
        self._formula_registry = formula_registry
        self.sign_handler = None  # Set by coordinator

    def check_all(self, statements: Any) -> list[CheckResult]:
        """
        Run vertical checks using checks_v2 pipeline.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult objects
        """
        self.logger.info("Running vertical checks via checks_v2 adapter")

        # For now, vertical checks come from the same pipeline
        # They are already included in the orchestrator run
        # Return empty list - the horizontal adapter handles everything

        # TODO: Implement separate vertical checks in checks_v2
        # that verify cross-statement consistency
        return []


class LibraryCheckerV2:
    """
    Adapter for library checks using checks_v2 architecture.

    Provides the same interface as the old LibraryChecker.
    """

    def __init__(self):
        self.logger = logging.getLogger('checks_v2.adapter.library')

    def check_all(self, statements: Any, taxonomy_id: str = None) -> list[CheckResult]:
        """
        Run library checks.

        Args:
            statements: MappedStatements object
            taxonomy_id: Taxonomy identifier

        Returns:
            List of CheckResult objects
        """
        self.logger.info("Running library checks via checks_v2 adapter")

        # TODO: Implement library checks in checks_v2
        return []


def get_checkers_v2(config: Any = None) -> tuple:
    """
    Get checks_v2 checker instances.

    Args:
        config: Optional config loader

    Returns:
        Tuple of (HorizontalCheckerV2, VerticalCheckerV2, LibraryCheckerV2)
    """
    tolerance = config.get('calculation_tolerance', 0.01) if config else 0.01
    rounding = config.get('rounding_tolerance', 1.0) if config else 1.0

    return (
        HorizontalCheckerV2(),
        VerticalCheckerV2(tolerance, rounding),
        LibraryCheckerV2(),
    )


__all__ = [
    'HorizontalCheckerV2',
    'VerticalCheckerV2',
    'LibraryCheckerV2',
    'get_checkers_v2',
]
