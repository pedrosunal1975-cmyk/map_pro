# Path: verification/engine/markets/esef/statement_identifier.py
"""
ESEF Statement Identifier

Identifies the main financial statements from ESEF/IFRS filings.

ESEF Advantage:
- Only 6 standardized IFRS statement types
- Clean, predictable naming
- All statements in core_statements/ are main statements

Main Statements (IFRS):
1. Statement of Financial Position (Balance Sheet)
2. Statement of Profit or Loss (Income Statement)
3. Statement of Cash Flows
4. Statement of Changes in Equity
5. Statement of Comprehensive Income (may be combined with P&L)
6. Notes and Mandatory Items

Identification is straightforward - match against the 6 known names.
"""

from pathlib import Path
from typing import List, Dict, Optional, Set

from verification.engine.markets.base import (
    BaseStatementIdentifier,
    StatementCategory,
    StatementInfo,
    MainStatements,
)


class ESEFStatementIdentifier(BaseStatementIdentifier):
    """
    ESEF/IFRS-specific statement identification.

    Identifies the 6 main IFRS statements from ESEF filings.
    Much simpler than SEC - IFRS has standardized statement names.
    """

    # ESEF-specific thresholds (lower than SEC - IFRS statements can be smaller)
    MIN_FILE_SIZE_THRESHOLD: int = 20000   # 20KB for JSON
    MIN_FACT_COUNT_THRESHOLD: int = 20     # IFRS statements can have fewer facts

    # The 6 IFRS standard statement names (normalized)
    MAIN_STATEMENT_NAMES: Set[str] = {
        "statementoffinancialposition",
        "profitorloss",
        "statementofcashflows",
        "statementofchangesinequity",
        "statementofcomprehensiveincome",
        "notesandmandatoryitems",
    }

    # Alternative names that map to main statements
    NAME_MAPPINGS: Dict[str, str] = {
        "balancesheet": "statementoffinancialposition",
        "consolidatedbalancesheet": "statementoffinancialposition",
        "incomestatement": "profitorloss",
        "profitandloss": "profitorloss",
        "cashflowstatement": "statementofcashflows",
        "equitystatement": "statementofchangesinequity",
        "comprehensiveincome": "statementofcomprehensiveincome",
        "othercomprehensiveincome": "statementofcomprehensiveincome",
        "notes": "notesandmandatoryitems",
    }

    def identify_main_statements(
        self,
        statements: List[Dict],
        json_dir: Optional[Path] = None
    ) -> MainStatements:
        """
        Identify main financial statements from ESEF filing.

        Strategy for ESEF:
        1. Match against the 6 known IFRS statement names
        2. File size is secondary (all core_statements are main)
        3. Much simpler than SEC

        Args:
            statements: List of statement dictionaries
            json_dir: Path to JSON directory for file size checks

        Returns:
            MainStatements with identified main statements
        """
        main = MainStatements()

        for stmt in statements:
            name = stmt.get('statement_name', stmt.get('name', ''))
            if not name:
                continue

            # Get file size
            file_size = 0
            if json_dir:
                file_size = self._get_file_size(json_dir, name)

            fact_count = len(stmt.get('facts', []))
            normalized = self.normalize_name(name)

            # Check if it's a main statement
            if normalized not in self.MAIN_STATEMENT_NAMES:
                # Check alternative names
                mapped = self.NAME_MAPPINGS.get(normalized)
                if mapped:
                    normalized = mapped
                else:
                    continue

            info = StatementInfo(
                name=name,
                category=StatementCategory.MAIN,
                file_size=file_size,
                fact_count=fact_count,
                normalized_name=normalized
            )

            # Map to appropriate slot
            if normalized == "statementoffinancialposition":
                main.balance_sheet = info
            elif normalized == "profitorloss":
                main.income_statement = info
            elif normalized == "statementofcashflows":
                main.cash_flow = info
            elif normalized == "statementofchangesinequity":
                main.equity_statement = info
            elif normalized == "statementofcomprehensiveincome":
                main.comprehensive_income = info
            elif normalized == "notesandmandatoryitems":
                main.notes = info

        return main

    def categorize_statement(
        self,
        statement_name: str,
        file_size: int = 0,
        fact_count: int = 0
    ) -> StatementCategory:
        """
        Categorize an ESEF statement.

        For ESEF, categorization is straightforward:
        - If name matches one of 6 IFRS statements -> MAIN
        - If in details/ folder -> DETAIL
        - Otherwise -> OTHER

        Args:
            statement_name: Name of the statement
            file_size: Size of the statement file in bytes
            fact_count: Number of facts in the statement

        Returns:
            StatementCategory classification
        """
        normalized = self.normalize_name(statement_name)

        # Check main statement names
        if normalized in self.MAIN_STATEMENT_NAMES:
            return StatementCategory.MAIN

        # Check alternative names
        if normalized in self.NAME_MAPPINGS:
            return StatementCategory.MAIN

        # Check for detail indicators
        if "detail" in statement_name.lower():
            return StatementCategory.DETAIL

        # Check for note indicators
        if "note" in statement_name.lower() and normalized != "notesandmandatoryitems":
            return StatementCategory.NOTE

        return StatementCategory.OTHER

    def get_main_statement_names(self) -> Set[str]:
        """
        Get the standard main statement names for ESEF.

        Returns:
            Set of normalized main statement names
        """
        return self.MAIN_STATEMENT_NAMES.copy()


__all__ = ['ESEFStatementIdentifier']
