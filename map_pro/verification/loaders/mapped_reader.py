# Path: verification/loaders/mapped_reader.py
"""
Mapped Statement Reader for Verification Module

Reads and interprets mapped statement files.
Works with paths provided by MappedDataLoader.

RESPONSIBILITY: Load and parse mapped statement JSON files
into structured data for verification checks.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .mapped_data import MappedFilingEntry


@dataclass
class StatementFact:
    """
    A single fact from a mapped statement.

    Attributes:
        concept: Concept name (e.g., 'us-gaap:Assets')
        value: Fact value (numeric or string)
        unit: Unit of measurement (e.g., 'USD')
        decimals: Decimal precision
        period_start: Period start date (for duration facts)
        period_end: Period end date
        context_id: Context identifier
        dimensions: Dimensional qualifiers
        label: Human-readable label
        order: Display order in statement
    """
    concept: str
    value: any
    unit: Optional[str] = None
    decimals: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    context_id: Optional[str] = None
    dimensions: dict = field(default_factory=dict)
    label: Optional[str] = None
    order: Optional[float] = None
    depth: int = 0
    is_total: bool = False
    is_abstract: bool = False


@dataclass
class Statement:
    """
    A financial statement with its facts.

    Attributes:
        name: Statement name (e.g., 'ConsolidatedBalanceSheet')
        role: Statement role URI
        facts: List of facts in this statement
        metadata: Additional statement metadata
    """
    name: str
    role: Optional[str] = None
    facts: list[StatementFact] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MappedStatements:
    """
    Complete set of mapped statements for a filing.

    Attributes:
        statements: List of statements
        filing_info: Filing metadata
        namespaces: Namespace declarations
        periods: Available reporting periods
    """
    statements: list[Statement] = field(default_factory=list)
    filing_info: dict = field(default_factory=dict)
    namespaces: dict = field(default_factory=dict)
    periods: list[dict] = field(default_factory=list)


class MappedReader:
    """
    Reads and interprets mapped statement JSON files.

    Uses paths from MappedDataLoader to load actual content.
    Converts JSON structure into typed dataclasses for verification.

    Example:
        loader = MappedDataLoader()
        reader = MappedReader()

        filings = loader.discover_all_mapped_filings()
        for filing in filings:
            statements = reader.read_statements(filing)
            for stmt in statements.statements:
                print(f"{stmt.name}: {len(stmt.facts)} facts")
    """

    def __init__(self):
        """Initialize mapped reader."""
        self.logger = logging.getLogger('input.mapped_reader')

    def read_statements(self, filing: MappedFilingEntry) -> Optional[MappedStatements]:
        """
        Read all statements from a mapped filing.

        Args:
            filing: MappedFilingEntry from MappedDataLoader

        Returns:
            MappedStatements object or None if reading fails
        """
        self.logger.info(f"Reading statements for {filing.company}/{filing.form}/{filing.date}")

        # Find the main statements file
        main_file = self._find_main_statements_file(filing)
        if not main_file:
            self.logger.warning(f"No main statements file found for {filing.filing_folder}")
            return None

        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self._parse_statements_data(data)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in {main_file}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading {main_file}: {e}")
            return None

    def read_statement_file(self, file_path: Path) -> Optional[Statement]:
        """
        Read a single statement JSON file.

        Args:
            file_path: Path to statement JSON file

        Returns:
            Statement object or None if reading fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self._parse_single_statement(data, file_path.stem)

        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return None

    def get_all_facts(self, statements: MappedStatements) -> list[StatementFact]:
        """
        Get all facts from all statements.

        Args:
            statements: MappedStatements object

        Returns:
            Flattened list of all facts
        """
        all_facts = []
        for stmt in statements.statements:
            all_facts.extend(stmt.facts)
        return all_facts

    def get_facts_by_concept(
        self,
        statements: MappedStatements,
        concept_pattern: str
    ) -> list[StatementFact]:
        """
        Find facts matching a concept pattern.

        Args:
            statements: MappedStatements object
            concept_pattern: Substring to match in concept name

        Returns:
            List of matching facts
        """
        matching = []
        pattern_lower = concept_pattern.lower()

        for stmt in statements.statements:
            for fact in stmt.facts:
                if pattern_lower in fact.concept.lower():
                    matching.append(fact)

        return matching

    def _find_main_statements_file(self, filing: MappedFilingEntry) -> Optional[Path]:
        """Find the main statements JSON file."""
        # Check json folder first
        if filing.json_folder and filing.json_folder.exists():
            for file_path in filing.json_folder.iterdir():
                if file_path.name in ['MAIN_FINANCIAL_STATEMENTS.json', 'statements.json']:
                    return file_path

        # Check root folder
        for file_path in filing.filing_folder.iterdir():
            if file_path.is_file() and file_path.name in [
                'MAIN_FINANCIAL_STATEMENTS.json',
                'statements.json'
            ]:
                return file_path

        # Return any JSON file
        json_files = filing.available_files.get('json', [])
        return json_files[0] if json_files else None

    def _parse_statements_data(self, data: dict) -> MappedStatements:
        """Parse the main statements JSON data."""
        result = MappedStatements()

        # Extract filing info
        result.filing_info = data.get('filing_info', data.get('metadata', {}))

        # Extract namespaces
        result.namespaces = data.get('namespaces', {})

        # Extract periods
        result.periods = data.get('periods', [])

        # Parse statements
        statements_data = data.get('statements', [])
        if isinstance(statements_data, dict):
            # Handle dict format {name: statement_data}
            for name, stmt_data in statements_data.items():
                stmt = self._parse_single_statement(stmt_data, name)
                if stmt:
                    result.statements.append(stmt)
        elif isinstance(statements_data, list):
            # Handle list format [{name, facts, ...}, ...]
            for stmt_data in statements_data:
                name = stmt_data.get('name', stmt_data.get('statement_name', 'Unknown'))
                stmt = self._parse_single_statement(stmt_data, name)
                if stmt:
                    result.statements.append(stmt)

        return result

    def _parse_single_statement(self, data: dict, name: str) -> Optional[Statement]:
        """Parse a single statement from JSON data."""
        try:
            stmt = Statement(
                name=name,
                role=data.get('role', data.get('roleUri')),
                metadata={
                    k: v for k, v in data.items()
                    if k not in ['facts', 'items', 'role', 'roleUri', 'name']
                }
            )

            # Parse facts
            facts_data = data.get('facts', data.get('items', []))
            for fact_data in facts_data:
                fact = self._parse_fact(fact_data)
                if fact:
                    stmt.facts.append(fact)

            return stmt

        except Exception as e:
            self.logger.error(f"Error parsing statement {name}: {e}")
            return None

    def _parse_fact(self, data: dict) -> Optional[StatementFact]:
        """Parse a single fact from JSON data."""
        try:
            # Handle different possible field names
            concept = (
                data.get('concept') or
                data.get('name') or
                data.get('qname') or
                ''
            )

            value = data.get('value', data.get('fact_value'))

            return StatementFact(
                concept=concept,
                value=value,
                unit=data.get('unit', data.get('unit_ref')),
                decimals=data.get('decimals'),
                period_start=data.get('period_start', data.get('startDate')),
                period_end=data.get('period_end', data.get('endDate', data.get('instant'))),
                context_id=data.get('context_id', data.get('contextRef')),
                dimensions=data.get('dimensions', {}),
                label=data.get('label', data.get('preferredLabel')),
                order=data.get('order'),
                depth=data.get('depth', data.get('level', 0)),
                is_total=data.get('is_total', data.get('isTotal', False)),
                is_abstract=data.get('is_abstract', data.get('isAbstract', False)),
            )

        except Exception as e:
            self.logger.error(f"Error parsing fact: {e}")
            return None


__all__ = ['MappedReader', 'MappedStatements', 'Statement', 'StatementFact']
