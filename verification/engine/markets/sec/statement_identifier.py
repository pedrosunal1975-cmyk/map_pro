# Path: verification/engine/markets/sec/statement_identifier.py
"""
SEC Statement Identifier

Identifies the main financial statements from SEC filings.

SEC Challenge:
- Filings can declare 99+ "statements" but only 4-5 are main financials
- Main statements are typically:
  1. Consolidated Balance Sheets (15-30KB)
  2. Consolidated Statements of Cash Flows (20-40KB)
  3. Consolidated Statements of Operations/Income (15-25KB)
  4. Consolidated Statements of Stockholders' Equity (15-25KB)
  5. Sometimes Consolidated Statements of Comprehensive Income (separate or combined)

Identification Criteria:
1. File size > 40KB JSON (main statements have many facts)
2. Name contains "consolidated" + statement type keyword
3. Located in core_statements/ folder
4. NOT parenthetical, details, policies, or tables
"""

from pathlib import Path
from typing import List, Dict, Optional, Set

from verification.engine.markets.base import (
    BaseStatementIdentifier,
    StatementCategory,
    StatementInfo,
    MainStatements,
)


class SECStatementIdentifier(BaseStatementIdentifier):
    """
    SEC-specific statement identification.

    Identifies the 4-5 main consolidated statements from SEC filings.
    """

    # SEC-specific thresholds
    MIN_FILE_SIZE_THRESHOLD: int = 40000   # 40KB for JSON - main statements are large
    MIN_FACT_COUNT_THRESHOLD: int = 50     # Main statements have many facts

    # SEC uses "consolidated" prefix for main statements
    CONSOLIDATED_KEYWORDS: Set[str] = {"consolidated", "combined"}

    # Exclusion patterns - these are NOT main statements
    EXCLUSION_PATTERNS: Set[str] = {
        "parenthetical",
        "details",
        "policies",
        "tables",
        "disclosure",
        "schedule",
        "coverpage",
        "cover",
        "audit",
        "insider",
        "pvp",          # Pay vs Performance
        "err",          # Error disclosures
        "award",        # Award timing
        "trading",      # Trading arrangements
    }

    def identify_main_statements(
        self,
        statements: List[Dict],
        json_dir: Optional[Path] = None
    ) -> MainStatements:
        """
        Identify main financial statements from SEC filing.

        Strategy:
        1. Filter to consolidated statements only
        2. Check file sizes - main statements are large (>40KB JSON)
        3. Match to standard statement types by keywords
        4. Exclude parenthetical, details, etc.

        Args:
            statements: List of statement dictionaries
            json_dir: Path to JSON directory for file size checks

        Returns:
            MainStatements with identified main statements
        """
        main = MainStatements()
        candidates: List[StatementInfo] = []

        # Build candidate list with file sizes
        for stmt in statements:
            name = stmt.get('statement_name', stmt.get('name', ''))
            if not name:
                continue

            # Get file size
            file_size = 0
            if json_dir:
                file_size = self._get_file_size(json_dir, name)

            fact_count = len(stmt.get('facts', []))

            # Categorize
            category = self.categorize_statement(name, file_size, fact_count)

            info = StatementInfo(
                name=name,
                category=category,
                file_size=file_size,
                fact_count=fact_count,
                normalized_name=self.normalize_name(name)
            )

            if category == StatementCategory.MAIN:
                candidates.append(info)

        # Sort candidates by file size (largest first) - most reliable indicator
        candidates.sort(key=lambda x: x.file_size, reverse=True)

        # Match candidates to statement types
        for candidate in candidates:
            normalized = candidate.normalized_name

            # Balance Sheet
            if main.balance_sheet is None and self._matches_keywords(normalized, self.BALANCE_KEYWORDS):
                main.balance_sheet = candidate

            # Income Statement / Operations
            elif main.income_statement is None and self._matches_keywords(normalized, self.INCOME_KEYWORDS):
                # Check if it's NOT comprehensive income (separate statement)
                if not self._matches_keywords(normalized, {"comprehensive"}):
                    main.income_statement = candidate
                elif main.comprehensive_income is None:
                    main.comprehensive_income = candidate

            # Cash Flow
            elif main.cash_flow is None and self._matches_keywords(normalized, self.CASHFLOW_KEYWORDS):
                main.cash_flow = candidate

            # Stockholders' Equity
            elif main.equity_statement is None and self._matches_keywords(normalized, self.EQUITY_KEYWORDS):
                main.equity_statement = candidate

            # Comprehensive Income (if separate from Income Statement)
            elif main.comprehensive_income is None and self._matches_keywords(normalized, self.COMPREHENSIVE_KEYWORDS):
                main.comprehensive_income = candidate

        return main

    def categorize_statement(
        self,
        statement_name: str,
        file_size: int = 0,
        fact_count: int = 0
    ) -> StatementCategory:
        """
        Categorize a SEC statement.

        Args:
            statement_name: Name of the statement
            file_size: Size of the statement file in bytes
            fact_count: Number of facts in the statement

        Returns:
            StatementCategory classification
        """
        normalized = self.normalize_name(statement_name)
        lower_name = statement_name.lower()

        # Check exclusion patterns first
        for pattern in self.EXCLUSION_PATTERNS:
            if pattern in lower_name:
                if "details" in lower_name:
                    return StatementCategory.DETAIL
                elif "policies" in lower_name or "tables" in lower_name:
                    return StatementCategory.NOTE
                else:
                    return StatementCategory.OTHER

        # Must be "consolidated" or "combined" for main statements
        is_consolidated = any(kw in normalized for kw in self.CONSOLIDATED_KEYWORDS)
        if not is_consolidated:
            return StatementCategory.OTHER

        # Check if it matches main statement keywords
        is_main_type = (
            self._matches_keywords(normalized, self.BALANCE_KEYWORDS) or
            self._matches_keywords(normalized, self.INCOME_KEYWORDS) or
            self._matches_keywords(normalized, self.CASHFLOW_KEYWORDS) or
            self._matches_keywords(normalized, self.EQUITY_KEYWORDS) or
            self._matches_keywords(normalized, self.COMPREHENSIVE_KEYWORDS)
        )

        if not is_main_type:
            return StatementCategory.OTHER

        # File size check - main statements are large
        if file_size > 0 and file_size < self.MIN_FILE_SIZE_THRESHOLD:
            # Small file with consolidated name - likely a summary or parenthetical
            return StatementCategory.OTHER

        # Fact count check
        if fact_count > 0 and fact_count < self.MIN_FACT_COUNT_THRESHOLD:
            return StatementCategory.OTHER

        return StatementCategory.MAIN

    def get_main_statement_names(self) -> Set[str]:
        """
        Get the standard main statement name patterns for SEC.

        Returns:
            Set of normalized main statement name patterns
        """
        return {
            "consolidatedbalancesheets",
            "consolidatedbalancesheet",
            "consolidatedstatementsofoperations",
            "consolidatedstatementsofoperationsandcomprehensiveincome",
            "consolidatedstatementsofcashflows",
            "consolidatedstatementofcashflows",
            "consolidatedstatementsofstockholdersequity",
            "consolidatedstatementofshareholdersequity",
            "consolidatedstatementsofchangesinequity",
            "consolidatedstatementsofcomprehensiveincome",
        }


__all__ = ['SECStatementIdentifier']
