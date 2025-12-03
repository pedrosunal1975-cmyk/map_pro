"""
File Readers for Library Dependency Scanner.

Handles reading and parsing of facts JSON files and XBRL XML files
for namespace extraction.

Location: engines/librarian/file_readers.py
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.core_models import Filing

from .scanner_models import ScannerConstants
from .namespace_extraction import NamespaceExtractor


class FactsJsonReader:
    """
    Reads and parses facts JSON files.
    
    Handles file validation and JSON parsing with proper error handling.
    """
    
    def __init__(self, logger):
        """
        Initialize facts JSON reader.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def read_facts_file(self, facts_json_path: str) -> Optional[Dict[str, Any]]:
        """
        Read and parse facts JSON file.
        
        Args:
            facts_json_path: Path to facts JSON file
            
        Returns:
            Parsed JSON data or None if read fails
            
        Raises:
            No exceptions raised - errors are logged
        """
        try:
            json_path = Path(facts_json_path)
            
            if not json_path.exists():
                self.logger.warning(f"Facts JSON file not found: {facts_json_path}")
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in facts file {facts_json_path}: {e}")
            return None
        
        except OSError as e:
            self.logger.error(f"Failed to read facts file {facts_json_path}: {e}")
            return None
        
        except Exception as e:
            self.logger.error(f"Unexpected error reading facts file: {e}", exc_info=True)
            return None
    
    def extract_facts_list(self, facts_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract facts list from parsed JSON data.
        
        Args:
            facts_data: Parsed JSON data
            
        Returns:
            List of fact dictionaries (empty list if not found)
        """
        if not facts_data:
            return []
        
        facts_list = facts_data.get('facts', [])
        
        if not isinstance(facts_list, list):
            self.logger.warning(f"Facts field is not a list: {type(facts_list)}")
            return []
        
        return facts_list


class XbrlFileScanner:
    """
    Scans XBRL files in extraction directories.
    
    Handles file discovery and XML parsing for namespace extraction.
    """
    
    def __init__(self, logger):
        """
        Initialize XBRL file scanner.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def get_extraction_directory(self, filing_id: str) -> Optional[Path]:
        """
        Get extraction directory for a filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Path to extraction directory or None if not found
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter(
                    Filing.filing_universal_id == filing_id
                ).first()
                
                if not filing or not filing.filing_directory_path:
                    self.logger.warning(
                        f"No filing directory found for {filing_id}"
                    )
                    return None
                
                # Handle both absolute and relative paths
                filing_dir_str = filing.filing_directory_path
                if Path(filing_dir_str).is_absolute():
                    # Already absolute path
                    base_path = Path(filing_dir_str)
                else:
                    # Relative path, join with data_root
                    base_path = map_pro_paths.data_root / filing_dir_str

                extraction_dir = base_path / ScannerConstants.EXTRACTED_DIR
                
                if not extraction_dir.exists():
                    self.logger.warning(
                        f"Extraction directory not found: {extraction_dir}"
                    )
                    return None
                
                return extraction_dir
        
        except Exception as e:
            self.logger.error(f"Failed to get extraction directory: {e}", exc_info=True)
            return None
    
    def find_xbrl_files(self, extraction_dir: Path) -> List[Path]:
        """
        Find all XBRL files in extraction directory.
        
        Args:
            extraction_dir: Path to extraction directory
            
        Returns:
            List of XBRL file paths
        """
        xbrl_files = []
        
        try:
            xbrl_files.extend(extraction_dir.rglob(ScannerConstants.XSD_EXTENSION))
            xbrl_files.extend(extraction_dir.rglob(ScannerConstants.XML_EXTENSION))
        except Exception as e:
            self.logger.error(f"Failed to find XBRL files: {e}", exc_info=True)
        
        return xbrl_files
    
    def extract_namespaces_from_file(self, file_path: Path) -> Set[str]:
        """
        Extract namespace declarations from XBRL file.
        
        Parses XML and extracts namespaces from:
        - xmlns declarations
        - schemaLocation attributes
        
        Args:
            file_path: Path to XBRL file
            
        Returns:
            Set of normalized namespaces found in file
        """
        namespaces = set()
        extractor = NamespaceExtractor(self.logger)
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract from xmlns declarations
            namespaces.update(extractor.extract_from_xml_attributes(root.attrib))
            
            # Extract from schemaLocation
            schema_location = root.get(
                f'{{{ScannerConstants.XSI_NAMESPACE}}}{ScannerConstants.SCHEMA_LOCATION_ATTR}',
                ''
            )
            
            if schema_location:
                namespaces.update(
                    extractor.extract_from_schema_location(schema_location)
                )
        
        except ET.ParseError:
            # Skip files that can't be parsed as XML
            self.logger.debug(f"Could not parse XML file: {file_path}")
        
        except Exception as e:
            self.logger.debug(
                f"Failed to extract namespaces from {file_path}: {e}"
            )
        
        return namespaces


__all__ = ['FactsJsonReader', 'XbrlFileScanner']