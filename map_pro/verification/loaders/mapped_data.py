# Path: verification/loaders/mapped_data.py
"""
Mapped Data Loader for Verification Module

Blind doorkeeper for mapped statements directory.
Discovers and provides paths to mapped statement files.
Does NOT load or interpret contents - that's for mapped_reader.py.

ARCHITECTURE:
- Discovers all mapped filing folders
- Provides paths to statement files
- Extracts metadata from folder structure
- Other components (mapped_reader) load and interpret files
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from .constants import MAPPED_STATEMENT_MARKERS, MAPPED_OUTPUT_SUBDIRS


@dataclass
class MappedFilingEntry:
    """
    Entry for a mapped filing folder.

    Contains only paths and folder-derived metadata.
    Does NOT contain file contents - that's for mapped_reader.

    Attributes:
        market: Market name (e.g., 'sec', 'esef')
        company: Company name (from folder name)
        form: Document type/form (from folder name)
        date: Filing date (from folder name)
        filing_folder: Path to mapped filing folder
        json_folder: Path to json/ subdirectory (if exists)
        csv_folder: Path to csv/ subdirectory (if exists)
        excel_folder: Path to excel/ subdirectory (if exists)
        available_files: Dict of file types to paths
    """
    market: str
    company: str
    form: str
    date: str
    filing_folder: Path
    json_folder: Optional[Path]
    csv_folder: Optional[Path]
    excel_folder: Optional[Path]
    available_files: dict[str, list[Path]]  # {format: [paths]}


class MappedDataLoader:
    """
    Blind doorkeeper for mapped statements directory.

    Discovers mapped filing folders and provides paths to all statement files.
    Does NOT load file contents - that's for MappedReader.

    SINGLE ENTRY POINT: All mapped statement path discovery goes through this class.

    Example:
        loader = MappedDataLoader()

        # Discover all mapped filings
        filings = loader.discover_all_mapped_filings()

        # Get paths for a specific filing
        for filing in filings:
            print(f"{filing.company} | {filing.form} | {filing.date}")
            print(f"  JSON files: {len(filing.available_files.get('json', []))}")
    """

    MAX_DEPTH = 25

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize mapped data loader.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.mapper_output_dir = self.config.get('mapper_output_dir')
        self.logger = logging.getLogger('input.mapped_data')

        if not self.mapper_output_dir:
            raise ValueError(
                "Mapper output directory not configured. "
                "Check VERIFICATION_MAPPER_OUTPUT_DIR in .env"
            )

        self.logger.info(f"MappedDataLoader initialized: {self.mapper_output_dir}")

    def discover_all_mapped_filings(self) -> list[MappedFilingEntry]:
        """
        Discover all mapped filing folders in mapper output directory.

        Searches recursively for directories containing statement files.
        A valid mapped filing folder contains json/, csv/, or excel/ subdirectories.

        Returns:
            List of MappedFilingEntry objects with paths to all files
        """
        if not self.mapper_output_dir.exists():
            self.logger.warning(f"Mapper output directory not found: {self.mapper_output_dir}")
            return []

        self.logger.info(f"Discovering mapped filings in: {self.mapper_output_dir}")

        entries = []

        # Strategy: Find directories that contain output subdirectories (json/, csv/, excel/)
        # These are the filing folders
        for subdir in MAPPED_OUTPUT_SUBDIRS:
            for output_dir in self.mapper_output_dir.rglob(subdir):
                if not output_dir.is_dir():
                    continue

                # Check depth
                depth = len(output_dir.relative_to(self.mapper_output_dir).parts)
                if depth > self.MAX_DEPTH:
                    continue

                # The filing folder is the parent of the output subdirectory
                filing_folder = output_dir.parent

                # Check if we already processed this filing folder
                if any(e.filing_folder == filing_folder for e in entries):
                    continue

                entry = self._build_filing_entry(filing_folder)
                if entry:
                    entries.append(entry)

        self.logger.info(f"Discovered {len(entries)} mapped filing entries")

        # Sort by company, form, date
        entries.sort(key=lambda e: (e.company, e.form, e.date))

        return entries

    def _build_filing_entry(self, filing_folder: Path) -> Optional[MappedFilingEntry]:
        """
        Build filing entry from folder structure.

        Expected structure: .../market/company/form/date/
        """
        try:
            parts = filing_folder.parts

            if len(parts) < 4:
                self.logger.warning(f"Path too shallow: {filing_folder}")
                return None

            # Extract from path structure
            date = parts[-1]
            form = parts[-2]
            company = parts[-3]
            market = parts[-4]

            # Find output subdirectories
            json_folder = filing_folder / 'json'
            csv_folder = filing_folder / 'csv'
            excel_folder = filing_folder / 'excel'

            # Discover all files
            available_files = self._discover_files(filing_folder)

            if not available_files:
                self.logger.warning(f"No statement files found in {filing_folder}")
                return None

            return MappedFilingEntry(
                market=market,
                company=company,
                form=form,
                date=date,
                filing_folder=filing_folder,
                json_folder=json_folder if json_folder.exists() else None,
                csv_folder=csv_folder if csv_folder.exists() else None,
                excel_folder=excel_folder if excel_folder.exists() else None,
                available_files=available_files
            )

        except Exception as e:
            self.logger.error(f"Error building entry for {filing_folder}: {e}")
            return None

    def _discover_files(self, filing_folder: Path) -> dict[str, list[Path]]:
        """
        Discover all statement files in filing folder.

        Returns:
            Dictionary mapping format to list of file paths
            {'json': [path1, path2], 'csv': [...], 'excel': [...]}
        """
        files = {
            'json': [],
            'csv': [],
            'excel': [],
        }

        # Check each output subdirectory
        for format_name in MAPPED_OUTPUT_SUBDIRS:
            format_dir = filing_folder / format_name
            if format_dir.exists() and format_dir.is_dir():
                for file_path in format_dir.iterdir():
                    if file_path.is_file():
                        files[format_name].append(file_path)

        # Also check root folder for any direct files
        for file_path in filing_folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext == '.json':
                    files['json'].append(file_path)
                elif ext == '.csv':
                    files['csv'].append(file_path)
                elif ext in ['.xlsx', '.xlsm']:
                    files['excel'].append(file_path)

        return files

    def get_json_files(self, filing: MappedFilingEntry) -> list[Path]:
        """Get all JSON files for a filing."""
        return filing.available_files.get('json', [])

    def get_csv_files(self, filing: MappedFilingEntry) -> list[Path]:
        """Get all CSV files for a filing."""
        return filing.available_files.get('csv', [])

    def get_main_statements_file(self, filing: MappedFilingEntry) -> Optional[Path]:
        """
        Get the main statements JSON file.

        Returns:
            Path to MAIN_FINANCIAL_STATEMENTS.json or statements.json
        """
        json_files = filing.available_files.get('json', [])

        for marker in MAPPED_STATEMENT_MARKERS:
            for json_file in json_files:
                if json_file.name == marker:
                    return json_file

        # Return first JSON file if no marker found
        return json_files[0] if json_files else None

    def find_mapped_filing(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> Optional[MappedFilingEntry]:
        """
        Find specific mapped filing.

        Args:
            market: Market identifier
            company: Company name
            form: Form type
            date: Filing date

        Returns:
            MappedFilingEntry or None if not found
        """
        expected_path = self.mapper_output_dir / market / company / form / date

        if not expected_path.exists():
            return None

        return self._build_filing_entry(expected_path)

    def get_filing_statistics(self) -> dict:
        """
        Get statistics about available mapped filings.

        Returns:
            Dictionary with counts by market, company, form
        """
        filings = self.discover_all_mapped_filings()

        stats = {
            'total_filings': len(filings),
            'by_market': {},
            'by_form': {},
            'companies': set(),
        }

        for filing in filings:
            # Count by market
            if filing.market not in stats['by_market']:
                stats['by_market'][filing.market] = 0
            stats['by_market'][filing.market] += 1

            # Count by form
            if filing.form not in stats['by_form']:
                stats['by_form'][filing.form] = 0
            stats['by_form'][filing.form] += 1

            # Track companies
            stats['companies'].add(f"{filing.market}/{filing.company}")

        stats['unique_companies'] = len(stats['companies'])
        stats['companies'] = list(stats['companies'])

        return stats


__all__ = ['MappedDataLoader', 'MappedFilingEntry']
