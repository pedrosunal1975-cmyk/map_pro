# Path: verification/engine/taxonomy_manager.py
"""
Taxonomy Manager for Verification Module

Integrates with the library module to ensure standard taxonomies
are available before running library checks.

SIMPLE RESPONSIBILITY:
1. Takes company specs from verification (market, company, form, date)
2. Passes them to library module (just the filing_id string)
3. Library module does EVERYTHING (finds parsed.json, detects taxonomies, etc.)
4. Returns taxonomy availability status

The library module is sophisticated - it only needs:
- The filing_id (market/company/form/date)
- Someone to tell it to 'go'
"""

import logging
import sys
import asyncio
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from ..constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT


class TaxonomyManager:
    """
    Manages taxonomy availability for verification.

    Simple integration with the library module:
    1. Pass company specs (filing_id) to library module
    2. Library does everything (finds parsed.json, detects taxonomies, downloads)
    3. Return status to verification

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

    def ensure_taxonomies_available(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> dict:
        """
        Ensure taxonomies are available for a filing.

        SIMPLE: Just pass filing_id to library module and let it do everything.

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
        # Construct filing_id - this is all library module needs
        filing_id = f"{market}/{company}/{form}/{date}"
        self.logger.info(f"{LOG_INPUT} Activating library module for {filing_id}")

        # Get library coordinator
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
            self.logger.info(f"{LOG_PROCESS} Library module processing filing: {filing_id}")

            # SIMPLE: Just call library with filing_id
            # Library module does EVERYTHING:
            # - Finds the parsed.json file
            # - Reads it and extracts namespaces
            # - Resolves namespaces to taxonomy libraries
            # - Checks availability (database + physical files)
            # - Saves missing libraries for download
            result = coordinator.process_filing_by_id(filing_id)

            if result is None:
                return {
                    'ready': False,
                    'libraries_required': [],
                    'libraries_available': 0,
                    'libraries_missing': 0,
                    'message': f'Filing not found by library module: {filing_id}',
                    'namespaces_detected': [],
                }

            if not result.get('success', False):
                return {
                    'ready': False,
                    'libraries_required': [],
                    'libraries_available': 0,
                    'libraries_missing': 0,
                    'message': result.get('error', 'Unknown error from library module'),
                    'namespaces_detected': [],
                }

            # Build status from library result
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
                f"{LOG_OUTPUT} Library module result for {filing_id}: "
                f"{status['libraries_available']} available, "
                f"{status['libraries_missing']} missing"
            )

            return status

        except Exception as e:
            self.logger.error(f"Error from library module: {e}")
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
