# Path: verification/engine/checks/duplicate_fact_checker.py
"""
Duplicate Fact Checker for Horizontal Verification

Checks for duplicate facts and classifies them per XBRL Duplicates Guidance:
- Complete duplicates (same value): OK, ignore
- Consistent duplicates (same value, different precision): OK, use most precise
- Inconsistent duplicates (different values): ERROR
"""

import logging
from typing import TYPE_CHECKING

from ..core.check_result import CheckResult
from ..core.constants import CHECK_DUPLICATE_FACTS
from ....constants import SEVERITY_CRITICAL, SEVERITY_INFO

if TYPE_CHECKING:
    from ....loaders.mapped_reader import MappedStatements
    from ..c_equal.c_equal import CEqual


# Configuration constants
MAX_DUPLICATES_DISPLAY = 20  # Maximum duplicates to show in results


class DuplicateFactChecker:
    """
    Checks for duplicate facts within statements.

    Uses C-Equal grouping to identify duplicate facts
    and classifies them according to XBRL guidance.
    """

    def __init__(self, c_equal: 'CEqual'):
        """
        Initialize duplicate fact checker.

        Args:
            c_equal: CEqual instance for fact grouping
        """
        self.c_equal = c_equal
        self.logger = logging.getLogger('process.duplicate_fact_checker')

    def check_duplicate_facts(self, statements: 'MappedStatements') -> list[CheckResult]:
        """
        Check for duplicate facts and classify them.

        Per XBRL Duplicates Guidance:
        - Complete duplicates (same value): OK, ignore
        - Consistent duplicates (same value, different precision): OK, use most precise
        - Inconsistent duplicates (different values): ERROR

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for duplicate issues
        """
        results = []

        # Group facts to detect duplicates
        fact_groups = self.c_equal.group_facts(statements)

        # Find inconsistent duplicates
        inconsistent = fact_groups.find_inconsistent_duplicates()

        if inconsistent:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=False,
                severity=SEVERITY_CRITICAL,
                message=f"{len(inconsistent)} facts with inconsistent duplicate values",
                details={
                    'duplicates': inconsistent[:MAX_DUPLICATES_DISPLAY],
                    'total_issues': len(inconsistent),
                }
            ))
            self.logger.warning(
                f"Found {len(inconsistent)} concepts with inconsistent duplicate values"
            )
        else:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=True,
                severity=SEVERITY_INFO,
                message="No inconsistent duplicate facts found"
            ))
            self.logger.debug("No inconsistent duplicate facts found")

        return results


__all__ = [
    'DuplicateFactChecker',
    'MAX_DUPLICATES_DISPLAY',
]
