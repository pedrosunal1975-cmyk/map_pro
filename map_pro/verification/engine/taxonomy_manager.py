# Path: verification/engine/taxonomy_manager.py
"""
Taxonomy Manager for Verification Module

Integrates with the library module to ensure standard taxonomies
are available before running library checks.

RESPONSIBILITY: Bridge between verification and library modules.
Triggers taxonomy downloads if needed before verification runs.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..loaders.parsed_data import ParsedDataLoader, ParsedFilingEntry
from ..constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT


class TaxonomyManager:
    """
    Manages taxonomy availability for verification.

    Integrates with the library module to:
    1. Check if required taxonomies are available
    2. Trigger taxonomy detection and download if needed
    3. Provide taxonomy status before library checks run

    Example:
        manager = TaxonomyManager()

        # Ensure taxonomies are available for a filing
        status = manager.ensure_taxonomies_available(filing)

        if status['ready']:
            # Run library checks
            ...
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize taxonomy manager.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.logger = logging.getLogger('process.taxonomy_manager')

        # Library module components (lazy loaded)
        self._library_coordinator = None
        self._library_available = None

        self.logger.info(f"{LOG_PROCESS} Taxonomy manager initialized")

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
            # Add library module to path if needed
            map_pro_dir = Path(__file__).parent.parent.parent
            if str(map_pro_dir) not in sys.path:
                sys.path.insert(0, str(map_pro_dir))

            # Initialize database engine first (required by library module)
            from database import initialize_engine
            initialize_engine()

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

    def ensure_taxonomies_available(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> dict:
        """
        Ensure taxonomies are available for a filing.

        Triggers library module to:
        1. Read parsed.json for the filing
        2. Detect required taxonomies from namespaces
        3. Download missing taxonomies

        Args:
            market: Market identifier
            company: Company name
            form: Form type
            date: Filing date

        Returns:
            Dictionary with status:
            {
                'ready': bool,
                'libraries_required': [...],
                'libraries_available': int,
                'libraries_missing': int,
                'message': str
            }
        """
        filing_id = f"{market}/{company}/{form}/{date}"
        self.logger.info(f"{LOG_INPUT} Checking taxonomy availability for {filing_id}")

        coordinator = self._get_library_coordinator()

        if not coordinator:
            return {
                'ready': False,
                'libraries_required': [],
                'libraries_available': 0,
                'libraries_missing': 0,
                'message': 'Library module not available',
            }

        try:
            # Process filing through library coordinator
            result = coordinator.process_filing_by_id(filing_id)

            if result is None:
                # Filing not found in parsed files - try constructing path
                self.logger.info(f"Filing not found by ID, trying alternate lookup")
                result = self._process_by_path(market, company, form, date)

            if result is None:
                return {
                    'ready': False,
                    'libraries_required': [],
                    'libraries_available': 0,
                    'libraries_missing': 0,
                    'message': f'Could not find parsed filing for {filing_id}',
                }

            if not result.get('success', False):
                return {
                    'ready': False,
                    'libraries_required': [],
                    'libraries_available': 0,
                    'libraries_missing': 0,
                    'message': result.get('error', 'Unknown error'),
                }

            # Build status from result
            status = {
                'ready': result.get('libraries_ready', False),
                'libraries_required': result.get('libraries_required', []),
                'libraries_available': result.get('libraries_available', 0),
                'libraries_missing': result.get('libraries_missing', 0),
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
            }

    def _process_by_path(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> Optional[dict]:
        """
        Process filing by constructing path directly.

        Used when filing ID lookup fails.
        """
        try:
            parsed_loader = ParsedDataLoader(self.config)
            parsed_filing = parsed_loader.find_parsed_filing(market, company, form, date)

            if not parsed_filing:
                return None

            # Create a FilingEntry-compatible object
            from library.models.filing_entry import FilingEntry

            filing = FilingEntry(
                filing_id=f"{market}/{company}/{form}/{date}",
                market=market,
                company=company,
                form_type=form,
                filing_date=date,
                accession_number=date,  # Use date as accession for ESEF
                parsed_json_path=parsed_filing.available_files.get('json'),
            )

            coordinator = self._get_library_coordinator()
            if coordinator:
                return coordinator.process_filing(filing)

        except Exception as e:
            self.logger.debug(f"Error in alternate lookup: {e}")

        return None

    def trigger_taxonomy_downloads(self) -> dict:
        """
        Trigger download of all pending taxonomies.

        Returns:
            Dictionary with download results
        """
        self.logger.info(f"{LOG_PROCESS} Triggering taxonomy downloads")

        try:
            import asyncio

            # Add downloader to path
            downloader_path = Path(__file__).parent.parent.parent / 'downloader'
            if str(downloader_path) not in sys.path:
                sys.path.insert(0, str(downloader_path.parent))

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
