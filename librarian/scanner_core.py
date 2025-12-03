"""
Core Scanner Implementation for Library Dependency Scanner.

Main scanner orchestration that coordinates namespace extraction,
matching, and library mapping operations.

Location: engines/librarian/scanner_core.py
"""

from typing import Dict, Any, List, Set, Optional

from core.system_logger import get_logger

from .scanner_models import ScanResult
from .namespace_extraction import NamespaceExtractor
from .namespace_matching import LibraryMapper
from .file_readers import FactsJsonReader, XbrlFileScanner
from .taxonomy_config import TAXONOMY_CONFIGS


logger = get_logger(__name__, 'engine')


class LibraryDependencyScanner:
    """
    Main scanner for filing library dependency requirements.
    
    Orchestrates the complete scanning process including:
    - Facts analysis
    - XBRL file scanning
    - Namespace extraction
    - Library mapping
    
    This is a market-agnostic implementation that works across all supported
    markets (SEC, FCA, ESMA, etc.).
    
    Example:
        >>> scanner = LibraryDependencyScanner()
        >>> result = await scanner.scan_filing_requirements(
        ...     filing_id='uuid-123',
        ...     market_type='SEC',
        ...     facts_json_path='/path/to/facts.json'
        ... )
        >>> 
        >>> if result.success:
        ...     print(f"Found {len(result.required_libraries)} libraries")
        ... else:
        ...     print(f"Scan failed: {result.error}")
    """
    
    def __init__(self):
        """Initialize library dependency scanner with all components."""
        self.logger = logger
        
        # Initialize components
        self.facts_reader = FactsJsonReader(self.logger)
        self.xbrl_scanner = XbrlFileScanner(self.logger)
        self.library_mapper = LibraryMapper(self.logger)
        self.namespace_extractor = NamespaceExtractor(self.logger)
        
        # Build namespace patterns for debugging
        self.namespace_patterns = self._build_namespace_patterns()
        
        self.logger.debug("Library dependency scanner initialized")
    
    async def scan_filing_requirements(
        self, 
        filing_id: str, 
        market_type: str, 
        facts_json_path: Optional[str] = None
    ) -> ScanResult:
        """
        Scan filing for all library requirements.
        
        Complete scanning process:
        1. Analyze parsed facts for namespaces
        2. Scan XBRL files for additional namespaces
        3. Combine and deduplicate all namespaces
        4. Map namespaces to required libraries
        
        Args:
            filing_id: Filing UUID to analyze
            market_type: Market type for library selection
            facts_json_path: Optional path to facts JSON file
            
        Returns:
            ScanResult object with complete scan information
            
        Example:
            >>> result = await scanner.scan_filing_requirements(
            ...     'uuid-123',
            ...     'SEC',
            ...     '/path/to/facts.json'
            ... )
        """
        try:
            # Step 1: Analyze parsed facts
            fact_namespaces = await self._analyze_parsed_facts(
                filing_id, 
                facts_json_path
            )
            
            # Step 2: Scan XBRL files
            xbrl_namespaces = await self._scan_xbrl_files(filing_id)
            
            # Step 3: Combine namespaces
            all_namespaces = fact_namespaces.union(xbrl_namespaces)
            
            # Step 4: Map to libraries
            required_libraries = self.library_mapper.map_to_libraries(
                all_namespaces, 
                market_type
            )
            
            self.logger.info(
                f"Scan complete: {len(all_namespaces)} namespaces, "
                f"{len(required_libraries)} libraries"
            )
            
            return ScanResult(
                success=True,
                namespaces=all_namespaces,
                required_libraries=required_libraries,
                fact_namespaces_count=len(fact_namespaces),
                xbrl_namespaces_count=len(xbrl_namespaces)
            )
        
        except Exception as e:
            self.logger.error(f"Filing scan failed: {e}", exc_info=True)
            return ScanResult(
                success=False,
                namespaces=set(),
                required_libraries=[],
                fact_namespaces_count=0,
                xbrl_namespaces_count=0,
                error=str(e)
            )
    
    async def _analyze_parsed_facts(
        self, 
        filing_id: str, 
        facts_json_path: Optional[str]
    ) -> Set[str]:
        """
        Analyze parsed facts JSON file for namespace requirements.
        
        ENHANCED: Now extracts namespaces from both metadata and individual facts.
        
        Args:
            filing_id: Filing UUID
            facts_json_path: Path to the facts JSON file
            
        Returns:
            Set of unique namespaces found in parsed facts
        """
        namespaces = set()
        
        if not facts_json_path:
            self.logger.warning(
                f"No facts JSON path provided for filing {filing_id}"
            )
            return namespaces
        
        try:
            # Read facts file
            facts_data = self.facts_reader.read_facts_file(facts_json_path)
            if not facts_data:
                return namespaces
            
            # NEW: Extract from document metadata/header first
            document_namespaces = self.namespace_extractor.extract_from_parsed_document(
                facts_data
            )
            if document_namespaces:
                self.logger.info(
                    f"Found {len(document_namespaces)} namespaces in document metadata"
                )
                namespaces.update(document_namespaces)
            
            # Extract facts list
            facts_list = self.facts_reader.extract_facts_list(facts_data)
            
            # Extract namespaces from each fact
            for fact in facts_list:
                fact_namespaces = self.namespace_extractor.extract_from_fact(fact)
                namespaces.update(fact_namespaces)
            
            self.logger.info(
                f"Found {len(namespaces)} unique namespaces in facts JSON: "
                f"{sorted(list(namespaces))}"
            )
        
        except Exception as e:
            self.logger.error(
                f"Failed to analyze facts JSON: {e}",
                exc_info=True
            )
        
        return namespaces
    
    async def _scan_xbrl_files(self, filing_id: str) -> Set[str]:
        """
        Scan extracted XBRL files for taxonomy namespace declarations.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Set of unique namespaces found in XBRL files
        """
        namespaces = set()
        
        try:
            # Get extraction directory
            extraction_dir = self.xbrl_scanner.get_extraction_directory(filing_id)
            if not extraction_dir:
                return namespaces
            
            # Find XBRL files
            xbrl_files = self.xbrl_scanner.find_xbrl_files(extraction_dir)
            
            # Extract namespaces from each file
            for xbrl_file in xbrl_files:
                file_namespaces = self.xbrl_scanner.extract_namespaces_from_file(
                    xbrl_file
                )
                namespaces.update(file_namespaces)
            
            self.logger.info(
                f"Found {len(namespaces)} namespaces in "
                f"{len(xbrl_files)} XBRL files"
            )
        
        except Exception as e:
            self.logger.error(
                f"Failed to scan XBRL files: {e}",
                exc_info=True
            )
        
        return namespaces
    
    def _build_namespace_patterns(self) -> Dict[str, List[str]]:
        """
        Build namespace to library mapping patterns from configurations.
        
        Returns:
            Dictionary mapping taxonomy names to namespace patterns
        """
        patterns = {}
        
        for config in TAXONOMY_CONFIGS:
            taxonomy_name = config['taxonomy_name']
            namespace = config.get('namespace', '').lower().rstrip('/')
            
            if namespace:
                if taxonomy_name not in patterns:
                    patterns[taxonomy_name] = []
                patterns[taxonomy_name].append(namespace)
        
        return patterns
    
    def get_namespace_patterns(self) -> Dict[str, List[str]]:
        """
        Get namespace patterns for debugging purposes.
        
        Returns:
            Copy of namespace patterns dictionary
        """
        return self.namespace_patterns.copy()


__all__ = ['LibraryDependencyScanner']