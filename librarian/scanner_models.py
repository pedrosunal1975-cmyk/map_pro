"""
Scanner Models and Constants for Library Dependency Scanner.

Defines data structures, enums, and constants used throughout the
library dependency scanning system.

Location: engines/librarian/scanner_models.py
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Set, Optional


class ScannerConstants:
    """Constants used throughout the scanner."""
    
    # File extensions for XBRL files
    XSD_EXTENSION = '*.xsd'
    XML_EXTENSION = '*.xml'
    
    # Directory names
    EXTRACTED_DIR = 'extracted'
    
    # XML namespace constants
    XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'
    SCHEMA_LOCATION_ATTR = 'schemaLocation'
    XMLNS_PREFIX = 'xmlns'
    
    # URL protocol prefixes
    HTTP_PREFIX = 'http://'
    HTTPS_PREFIX = 'https://'
    
    # Taxonomy URL indicators for identifying taxonomy URLs across ALL markets
    # NOTE: This is multi-market reference data, not market-specific hardcoding
    # Includes patterns from SEC (US), FCA (UK), ESMA (EU), IFRS (international), and FASB
    TAXONOMY_INDICATORS = {
        'fasb.org',         # US GAAP (FASB)
        'ifrs.org',         # International (IFRS)
        'xbrl.org',         # XBRL International
        'sec.gov',          # US SEC market
        'frc.org.uk',       # UK FCA market
        'esma.europa.eu',   # EU ESMA market
        'taxonomy',         # Generic taxonomy marker
        'gaap',             # GAAP taxonomies
        'ifrs',             # IFRS taxonomies
        'esef',             # European Single Electronic Format
        'dei',              # Document Entity Information
        'srt'               # SEC Reporting Taxonomy
    }
    
    # Tolerance for extra characters (version, date suffix) past the taxonomy year 
    # in the namespace URL. Increased from 1 to 10 to safely cover common date 
    # suffixes (e.g., -01-31, which is 6 chars) and minor version extensions 
    # found in different market standards (SEC, ESMA, FCA).
    YEAR_MATCH_TOLERANCE = 10


class NamespaceSource(Enum):
    """Sources from which namespaces can be extracted."""
    PARSED_FACTS = 'parsed_facts'
    XBRL_FILES = 'xbrl_files'


@dataclass
class ScanResult:
    """
    Result of a filing dependency scan.
    
    Attributes:
        success: Whether scan completed successfully
        namespaces: Set of discovered namespaces
        required_libraries: List of required library configurations
        fact_namespaces_count: Number of namespaces from parsed facts
        xbrl_namespaces_count: Number of namespaces from XBRL files
        error: Error message if scan failed
    """
    success: bool
    namespaces: Set[str]
    required_libraries: List[Dict[str, Any]]
    fact_namespaces_count: int
    xbrl_namespaces_count: int
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert scan result to dictionary format.
        
        Returns:
            Dictionary representation of scan result
        """
        result = {
            'success': self.success,
            'namespaces': self.namespaces,
            'required_libraries': self.required_libraries,
            'fact_namespaces_count': self.fact_namespaces_count,
            'xbrl_namespaces_count': self.xbrl_namespaces_count
        }
        
        if self.error:
            result['error'] = self.error
        
        return result


__all__ = ['ScannerConstants', 'NamespaceSource', 'ScanResult']