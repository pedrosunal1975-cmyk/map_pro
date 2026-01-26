# Path: verification/engine/taxonomy_manager.py
"""
Taxonomy Manager for Verification Module

Integrates with the library module to ensure standard taxonomies
are available before running library checks.

RESPONSIBILITY: Bridge between verification and library modules.
1. Takes company details from verification
2. Passes them to library module (via FilingEntry)
3. Library module reads parsed.json, detects required taxonomies
4. If taxonomies are missing, triggers download
5. Returns taxonomy availability status

This follows the IPO principle:
- INPUT: Company details from verification
- PROCESS: Library module detects and downloads taxonomies
- OUTPUT: Taxonomy availability status for verification to use
"""

import logging
import sys
import asyncio
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..loaders.parsed_data import ParsedDataLoader, ParsedFilingEntry
from ..constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT


class TaxonomyManager:
    """
    Manages taxonomy availability for verification.

    Integrates with the library module to:
    1. Pass company details to library module
    2. Library reads parsed.json and detects required taxonomies
    3. Trigger taxonomy downloads if needed
    4. Provide taxonomy status before library checks run

    Example:
        manager = TaxonomyManager()

        # Ensure taxonomies are available for a filing
        status = manager.ensure_taxonomies_available(
            market='sec',
            company='Apple_Inc',
            form='10-K',
            date='0001234567'
        )

        if status['ready']:
            # Run library checks
            ...
        else:
            # Download required taxonomies first
            manager.trigger_taxonomy_downloads()
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize taxonomy manager.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.logger = logging.getLogger('process.taxonomy_manager')

        # Initialize parsed data loader to find parsed.json files
        self.parsed_loader = ParsedDataLoader(self.config)

        # Library module components (lazy loaded)
        self._library_coordinator = None
        self._library_available = None
        self._database_initialized = False

        self.logger.info(f"{LOG_PROCESS} Taxonomy manager initialized")

    def _initialize_database(self) -> bool:
        """
        Initialize database engine (required before library imports).

        Returns:
            True if successful
        """
        if self._database_initialized:
            return True

        try:
            # Add map_pro to path if needed
            map_pro_dir = Path(__file__).parent.parent.parent
            if str(map_pro_dir) not in sys.path:
                sys.path.insert(0, str(map_pro_dir))

            from database import initialize_engine
            initialize_engine()

            self._database_initialized = True
            self.logger.info(f"{LOG_OUTPUT} Database initialized")
            return True

        except ImportError as e:
            self.logger.warning(f"Database module not available: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"Could not initialize database: {e}")
            return False

    def _get_library_coordinator(self):
        """
        Lazy load library coordinator.

        Returns:
            LibraryCoordinator instance or None if not available
        """
        if self._library_coordinator is not None:
            return self._library_coordinator

        if self._library_available is False:
            return None

        try:
            # Initialize database first
            if not self._initialize_database():
                self._library_available = False
                return None

            # Import library coordinator
            from library.engine.coordinator import LibraryCoordinator

            self._library_coordinator = LibraryCoordinator()
            self._library_available = True

            self.logger.info(f"{LOG_OUTPUT} Library coordinator loaded successfully")
            return self._library_coordinator

        except ImportError as e:
            self.logger.warning(f"Library module not available: {e}")
            self._library_available = False
            return None
        except Exception as e:
            self.logger.warning(f"Could not initialize library coordinator: {e}")
            self._library_available = False
            return None

    def _create_library_filing_entry(
        self,
        parsed_filing: ParsedFilingEntry
    ):
        """
        Create a library.FilingEntry from verification.ParsedFilingEntry.

        Args:
            parsed_filing: ParsedFilingEntry from verification module

        Returns:
            library.FilingEntry object
        """
        from library.models.filing_entry import FilingEntry

        # Get parsed.json path
        parsed_json_path = parsed_filing.available_files.get('json')
        if not parsed_json_path:
            # Try to find parsed.json in the folder
            parsed_json_path = parsed_filing.filing_folder / 'parsed.json'

        return FilingEntry(
            market=parsed_filing.market,
            company=parsed_filing.company,
            form=parsed_filing.form,
            accession=parsed_filing.date,  # verification uses 'date', library uses 'accession'
            filing_folder=parsed_filing.filing_folder,
            parsed_json_path=parsed_json_path,
            available_files=parsed_filing.available_files,
        )

    def ensure_taxonomies_available(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> dict:
        """
        Ensure taxonomies are available for a filing.

        This method:
        1. Finds the parsed.json for the filing
        2. Creates a FilingEntry for library module
        3. Calls LibraryCoordinator.process_filing() which:
           - Reads parsed.json
           - Detects required taxonomies from namespaces
           - Checks availability (database + physical files)
           - Saves missing taxonomies to database for download
        4. Returns availability status

        Args:
            market: Market identifier (e.g., 'sec', 'esef')
            company: Company name
            form: Form type (e.g., '10-K')
            date: Filing date or accession number

        Returns:
            Dictionary with status:
            {
                'ready': bool,
                'libraries_required': [...],
                'libraries_available': int,
                'libraries_missing': int,
                'message': str,
                'namespaces_detected': [...],
            }
        """
        filing_id = f"{market}/{company}/{form}/{date}"
        self.logger.info(f"{LOG_INPUT} Checking taxonomy availability for {filing_id}")

        # Step 1: Find the parsed filing
        parsed_filing = self.parsed_loader.find_parsed_filing(market, company, form, date)

        if not parsed_filing:
            self.logger.warning(f"Parsed filing not found: {filing_id}")
            return {
                'ready': False,
                'libraries_required': [],
                'libraries_available': 0,
                'libraries_missing': 0,
                'message': f'Parsed filing not found: {filing_id}',
                'namespaces_detected': [],
            }

        # Step 2: Get library coordinator
        coordinator = self._get_library_coordinator()

        if not coordinator:
            return {
                'ready': False,
                'libraries_required': [],
                'libraries_available': 0,
                'libraries_missing': 0,
                'message': 'Library module not available',
                'namespaces_detected': [],
            }

        try:
            # Step 3: Create FilingEntry for library module
            library_filing = self._create_library_filing_entry(parsed_filing)

            self.logger.info(f"{LOG_PROCESS} Calling library module to process filing")

            # Step 4: Process filing through library coordinator
            # This reads parsed.json, detects namespaces, resolves to libraries,
            # checks availability, and saves missing libraries to database
            result = coordinator.process_filing(library_filing)

            if not result.get('success', False):
                return {
                    'ready': False,
                    'libraries_required': [],
                    'libraries_available': 0,
                    'libraries_missing': 0,
                    'message': result.get('error', 'Unknown error from library module'),
                    'namespaces_detected': [],
                }

            # Step 5: Build status from library result
            status = {
                'ready': result.get('libraries_ready', False),
                'libraries_required': result.get('libraries_required', []),
                'libraries_available': result.get('libraries_available', 0),
                'libraries_missing': result.get('libraries_missing', 0),
                'namespaces_detected': result.get('namespaces_detected', []),
                'message': 'All libraries available' if result.get('libraries_ready')
                          else f"{result.get('libraries_missing', 0)} libraries need to be downloaded",
            }

            self.logger.info(
                f"{LOG_OUTPUT} Taxonomy status for {filing_id}: "
                f"{status['libraries_available']} available, "
                f"{status['libraries_missing']} missing"
            )

            return status

        except Exception as e:
            self.logger.error(f"Error checking taxonomy availability: {e}")
            return {
                'ready': False,
                'libraries_required': [],
                'libraries_available': 0,
                'libraries_missing': 0,
                'message': str(e),
                'namespaces_detected': [],
            }

    def trigger_taxonomy_downloads(self) -> dict:
        """
        Trigger download of all pending taxonomies.

        This uses the downloader module to download taxonomies
        that were identified as missing by the library module.

        Returns:
            Dictionary with download results
        """
        self.logger.info(f"{LOG_PROCESS} Triggering taxonomy downloads")

        try:
            # Initialize database if needed
            if not self._initialize_database():
                return {
                    'success': False,
                    'error': 'Database not available',
                }

            # Add downloader to path
            map_pro_dir = Path(__file__).parent.parent.parent
            if str(map_pro_dir) not in sys.path:
                sys.path.insert(0, str(map_pro_dir))

            from downloader.engine.coordinator import DownloadCoordinator

            coordinator = DownloadCoordinator()

            async def run_downloads():
                return await coordinator.process_pending_downloads(limit=50)

            stats = asyncio.run(run_downloads())

            self.logger.info(
                f"{LOG_OUTPUT} Downloads complete: "
                f"{stats.get('succeeded', 0)}/{stats.get('total', 0)} successful"
            )

            return {
                'success': True,
                'total': stats.get('total', 0),
                'succeeded': stats.get('succeeded', 0),
                'failed': stats.get('failed', 0),
            }

        except ImportError as e:
            self.logger.warning(f"Downloader module not available: {e}")
            return {
                'success': False,
                'error': 'Downloader module not available',
            }
        except Exception as e:
            self.logger.error(f"Error triggering downloads: {e}")
            return {
                'success': False,
                'error': str(e),
            }

    def get_available_taxonomies(self) -> list[str]:
        """
        Get list of available taxonomy directories.

        Returns:
            List of taxonomy directory names (e.g., ['us-gaap-2023', 'ifrs-full'])
        """
        taxonomy_path = self.config.get('taxonomy_path')

        if not taxonomy_path or not taxonomy_path.exists():
            return []

        taxonomies = []
        for item in taxonomy_path.iterdir():
            if item.is_dir():
                # Check if it has schema files
                xsd_files = list(item.glob('*.xsd'))
                if xsd_files:
                    taxonomies.append(item.name)

        return sorted(taxonomies)

    def is_library_module_available(self) -> bool:
        """Check if library module is available."""
        coordinator = self._get_library_coordinator()
        return coordinator is not None


__all__ = ['TaxonomyManager']
