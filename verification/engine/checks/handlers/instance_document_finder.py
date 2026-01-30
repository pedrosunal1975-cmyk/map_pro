# Path: verification/engine/checks/handlers/instance_document_finder.py
"""
Instance Document Finder for XBRL Verification

Locates XBRL instance documents (iXBRL files) in filing directories.
These files contain sign attributes and other metadata needed for verification.
"""

import logging
from pathlib import Path
from typing import Optional


# Configuration constants
# File patterns for instance documents, in priority order
# iXBRL HTML files are preferred as they typically contain sign attributes
INSTANCE_DOCUMENT_PATTERNS = [
    ('*.htm', 'iXBRL HTML'),
    ('*.html', 'iXBRL HTML'),
    ('*.xhtml', 'iXBRL XHTML'),
    ('*_htm.xml', 'iXBRL XML'),
]

# File name patterns to exclude (these are linkbase files, not instance documents)
INSTANCE_DOCUMENT_EXCLUSIONS = ['_cal.', '_pre.', '_def.', '_lab.', 'schema']


class InstanceDocumentFinder:
    """
    Finds XBRL instance documents in filing directories.

    Instance documents contain the actual fact values and metadata
    (including iXBRL sign attributes) needed for verification.
    """

    def __init__(self):
        self.logger = logging.getLogger('process.instance_document_finder')

    def find_instance_document(self, filing_path: Path) -> Optional[Path]:
        """
        Find the XBRL instance document (iXBRL .htm file) in a filing directory.

        Prioritizes .htm files as they typically contain iXBRL with sign attributes.
        Returns the largest matching file (usually the full instance document).

        Args:
            filing_path: Path to filing directory

        Returns:
            Path to instance document or None if not found
        """
        if not filing_path or not filing_path.is_dir():
            self.logger.warning(f"Invalid filing path: {filing_path}")
            return None

        for pattern, doc_type in INSTANCE_DOCUMENT_PATTERNS:
            files = list(filing_path.glob(pattern))
            if files:
                # Filter out linkbase files (calculation, presentation, etc.)
                instance_files = [
                    f for f in files
                    if not any(excl in f.name.lower() for excl in INSTANCE_DOCUMENT_EXCLUSIONS)
                ]
                
                if instance_files:
                    # Prefer the largest file (usually the full instance document)
                    instance_file = max(instance_files, key=lambda f: f.stat().st_size)
                    self.logger.info(f"Found {doc_type} instance document: {instance_file.name}")
                    return instance_file

        self.logger.warning(f"No instance document found in {filing_path}")
        return None


__all__ = [
    'InstanceDocumentFinder',
    'INSTANCE_DOCUMENT_PATTERNS',
    'INSTANCE_DOCUMENT_EXCLUSIONS',
]
