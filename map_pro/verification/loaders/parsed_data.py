# Path: verification/loaders/parsed_data.py
"""
Parsed Data Loader for Verification Module

Discovers and provides paths to files in parser output directory.
Does NOT load or parse files - other components decide how to use them.

ARCHITECTURE:
- Discovers all filing folders
- Provides paths to any file within folders
- Extracts metadata from folder names only
- Other components load files themselves
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader


@dataclass
class ParsedFilingEntry:
    """
    Entry for a parsed filing folder.

    Contains only paths and folder-derived metadata.
    Does NOT contain file contents.

    Attributes:
        market: Market name
        company: Company name (from folder name)
        form: Document type/form (from folder name)
        date: Filing date (from folder name)
        filing_folder: Path to filing folder
        available_files: Dict of file types to paths
    """
    market: str
    company: str
    form: str
    date: str
    filing_folder: Path
    available_files: dict[str, Path]


class ParsedDataLoader:
    """
    Universal doorkeeper for parser output directory.

    Discovers filing folders and provides paths to all files.
    Does NOT load file contents - that's for other components.

    Example:
        loader = ParsedDataLoader()

        # Discover all filing folders
        filings = loader.discover_all_parsed_filings()

        # Get path to specific file
        json_path = loader.get_file_path(filing, 'json')
    """

    MAX_DEPTH = 25

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize parsed data loader.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.parser_output_dir = self.config.get('parser_output_dir')
        self.logger = logging.getLogger('input.parsed_data')

        if not self.parser_output_dir:
            raise ValueError(
                "Parser output directory not configured. "
                "Check VERIFICATION_PARSER_OUTPUT_DIR in .env"
            )

        self.logger.info(f"ParsedDataLoader initialized: {self.parser_output_dir}")

    def discover_all_parsed_filings(self) -> list[ParsedFilingEntry]:
        """
        Discover all filing folders in parser output directory.

        Searches recursively for directories containing parsed data files.

        Returns:
            List of ParsedFilingEntry objects with paths to all files
        """
        if not self.parser_output_dir.exists():
            self.logger.warning(f"Parser output directory not found: {self.parser_output_dir}")
            return []

        self.logger.info(f"Discovering filing folders in: {self.parser_output_dir}")

        entries = []

        for json_file in self.parser_output_dir.rglob('parsed.json'):
            depth = len(json_file.relative_to(self.parser_output_dir).parts)
            if depth > self.MAX_DEPTH:
                continue

            filing_folder = json_file.parent
            entry = self._build_filing_entry_from_folder(filing_folder)
            if entry:
                entries.append(entry)

        self.logger.info(f"Discovered {len(entries)} valid filing entries")

        entries.sort(key=lambda e: (e.company, e.form, e.date))

        return entries

    def _build_filing_entry_from_folder(self, filing_folder: Path) -> Optional[ParsedFilingEntry]:
        """Build filing entry from folder structure."""
        try:
            parts = filing_folder.parts

            if len(parts) < 4:
                self.logger.warning(f"Path too shallow: {filing_folder}")
                return None

            date = parts[-1]
            form = parts[-2]
            company = parts[-3]
            market = parts[-4]

            available_files = self._discover_files(filing_folder)

            if not available_files:
                self.logger.warning(f"No files found in {filing_folder}")
                return None

            return ParsedFilingEntry(
                market=market,
                company=company,
                form=form,
                date=date,
                filing_folder=filing_folder,
                available_files=available_files
            )

        except Exception as e:
            self.logger.error(f"Error building entry for {filing_folder}: {e}")
            return None

    def _discover_files(self, filing_folder: Path) -> dict[str, Path]:
        """Discover all files in filing folder."""
        files = {}

        for file_path in filing_folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                key = ext[1:] if ext.startswith('.') else ext
                files[key] = file_path

        return files

    def get_file_path(self, filing: ParsedFilingEntry, file_type: str) -> Optional[Path]:
        """Get path to specific file type."""
        return filing.available_files.get(file_type)

    def find_parsed_filing(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> Optional[ParsedFilingEntry]:
        """
        Find specific parsed filing.

        Args:
            market: Market identifier
            company: Company name
            form: Form type
            date: Filing date

        Returns:
            ParsedFilingEntry or None if not found
        """
        expected_path = self.parser_output_dir / market / company / form / date

        if not expected_path.exists():
            return None

        return self._build_filing_entry_from_folder(expected_path)


__all__ = ['ParsedDataLoader', 'ParsedFilingEntry']
