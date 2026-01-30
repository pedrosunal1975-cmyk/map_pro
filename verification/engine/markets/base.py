# Path: verification/engine/markets/base.py
"""
Base Statement Identifier

Abstract base class for market-specific main statement identification.

Purpose:
- Identify the 4-6 "main" financial statements from potentially 99+ declared statements
- Distinguish main statements from details, notes, policies, tables, etc.
- Enable proper duplicate detection (cross-statement appearances aren't duplicates)
- Focus vertical checks on main statements only

Architecture:
- Each market (SEC, ESEF) has different identification criteria
- Physical file characteristics (size, location) are key indicators
- Statement naming patterns vary by market
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set
from enum import Enum


class StatementCategory(Enum):
    """Classification of statement types."""
    MAIN = "main"           # Core financial statements (Balance Sheet, Income, Cash Flow, Equity)
    DETAIL = "detail"       # Detailed breakdowns of main statement items
    NOTE = "note"           # Notes and disclosures
    OTHER = "other"         # Cover pages, policies, tables, parenthetical


@dataclass
class StatementInfo:
    """Information about a single statement."""
    name: str                          # Statement name (e.g., "consolidatedbalancesheets")
    category: StatementCategory        # Classification
    file_path: Optional[Path] = None   # Path to the statement file
    file_size: int = 0                 # File size in bytes
    fact_count: int = 0                # Number of facts in statement
    normalized_name: str = ""          # Normalized name for comparison

    @property
    def is_main(self) -> bool:
        """Check if this is a main financial statement."""
        return self.category == StatementCategory.MAIN


@dataclass
class MainStatements:
    """Container for identified main statements."""
    balance_sheet: Optional[StatementInfo] = None
    income_statement: Optional[StatementInfo] = None
    cash_flow: Optional[StatementInfo] = None
    equity_statement: Optional[StatementInfo] = None
    comprehensive_income: Optional[StatementInfo] = None  # May be combined with income
    notes: Optional[StatementInfo] = None                 # ESEF has mandatory items

    def get_all(self) -> List[StatementInfo]:
        """Get all identified main statements."""
        return [s for s in [
            self.balance_sheet,
            self.income_statement,
            self.cash_flow,
            self.equity_statement,
            self.comprehensive_income,
            self.notes
        ] if s is not None]

    def get_names(self) -> Set[str]:
        """Get set of main statement names."""
        return {s.name for s in self.get_all()}


class BaseStatementIdentifier(ABC):
    """
    Abstract base class for market-specific statement identification.

    Subclasses implement market-specific logic for identifying
    the main financial statements from all declared statements.
    """

    # Minimum file size threshold (bytes) - files below this are likely not main statements
    MIN_FILE_SIZE_THRESHOLD: int = 10000  # 10KB for JSON

    # Main statement keywords - subclasses can override
    BALANCE_KEYWORDS: Set[str] = {"balance", "financialposition", "position"}
    INCOME_KEYWORDS: Set[str] = {"income", "operations", "profitorloss", "profit", "loss", "earnings"}
    CASHFLOW_KEYWORDS: Set[str] = {"cashflow", "cashflows", "cash"}
    EQUITY_KEYWORDS: Set[str] = {"equity", "stockholder", "shareholder", "changesinequity"}
    COMPREHENSIVE_KEYWORDS: Set[str] = {"comprehensive", "oci"}

    @abstractmethod
    def identify_main_statements(
        self,
        statements: List[Dict],
        json_dir: Optional[Path] = None
    ) -> MainStatements:
        """
        Identify the main financial statements from all statements.

        Args:
            statements: List of statement dictionaries with name, facts, etc.
            json_dir: Optional path to JSON directory for file size checks

        Returns:
            MainStatements container with identified main statements
        """
        pass

    @abstractmethod
    def categorize_statement(
        self,
        statement_name: str,
        file_size: int = 0,
        fact_count: int = 0
    ) -> StatementCategory:
        """
        Categorize a single statement.

        Args:
            statement_name: Name of the statement
            file_size: Size of the statement file in bytes
            fact_count: Number of facts in the statement

        Returns:
            StatementCategory classification
        """
        pass

    def normalize_name(self, name: str) -> str:
        """
        Normalize statement name for comparison.

        Removes common suffixes, prefixes, and standardizes format.

        Args:
            name: Original statement name

        Returns:
            Normalized name
        """
        normalized = name.lower()

        # Remove common suffixes
        suffixes_to_remove = [
            "parenthetical", "details", "policies", "tables",
            "_parenthetical", "_details", "_policies", "_tables"
        ]
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]

        # Remove underscores and hyphens for comparison
        normalized = normalized.replace("_", "").replace("-", "")

        return normalized

    def _get_file_size(self, json_dir: Path, statement_name: str) -> int:
        """
        Get file size for a statement.

        Args:
            json_dir: Path to JSON directory
            statement_name: Statement name

        Returns:
            File size in bytes, or 0 if not found
        """
        if not json_dir or not json_dir.exists():
            return 0

        # Try core_statements first, then other locations
        locations = [
            json_dir / "core_statements" / f"{statement_name}.json",
            json_dir / "details" / f"{statement_name}.json",
            json_dir / "other" / f"{statement_name}.json",
            json_dir / f"{statement_name}.json",
        ]

        for path in locations:
            if path.exists():
                return path.stat().st_size

        return 0

    def _matches_keywords(self, name: str, keywords: Set[str]) -> bool:
        """Check if name contains any of the keywords."""
        normalized = self.normalize_name(name)
        return any(kw in normalized for kw in keywords)


__all__ = [
    'StatementCategory',
    'StatementInfo',
    'MainStatements',
    'BaseStatementIdentifier',
]
